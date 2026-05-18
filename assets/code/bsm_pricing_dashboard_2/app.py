from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import yfinance as yf
from flask import Flask, jsonify, render_template, request

from pricing_engine import (
    autocallable_note_mc,
    black_scholes_greeks,
    black_scholes_price,
    capital_protected_note_mc,
    clean_float,
    clean_int,
    crr_binomial_price,
    gap_option_price,
    implied_volatility,
    longstaff_schwartz_american,
    monte_carlo_asian,
    monte_carlo_barrier,
    monte_carlo_european,
    reverse_convertible_mc,
)

app = Flask(__name__)


def error_response(message: str, status: int = 400):
    return jsonify({"ok": False, "error": message}), status


def json_ok(payload: Dict[str, Any]):
    return jsonify({"ok": True, **payload})


def _safe_label(record: Dict[str, Any], *keys: str, default: str = "") -> str:
    for key in keys:
        value = record.get(key)
        if value:
            return str(value)
    return default


def _search_quotes(query: str) -> List[Dict[str, Any]]:
    search = yf.Search(
        query,
        max_results=10,
        news_count=0,
        lists_count=0,
        include_cb=False,
        include_nav_links=False,
        include_research=False,
        enable_fuzzy_query=True,
        recommended=0,
        raise_errors=False,
    )
    quotes = getattr(search, "quotes", []) or []
    results = []
    for quote in quotes:
        symbol = quote.get("symbol")
        if not symbol:
            continue
        results.append(
            {
                "symbol": symbol,
                "name": _safe_label(quote, "shortname", "longname", default=symbol),
                "exchange": _safe_label(quote, "exchDisp", "exchange", default=""),
                "quote_type": _safe_label(quote, "quoteType", default=""),
                "score": quote.get("score"),
            }
        )
    return results


def _ticker_info(symbol: str) -> Dict[str, Any]:
    ticker = yf.Ticker(symbol)
    fast = getattr(ticker, "fast_info", {}) or {}

    def fast_get(name: str):
        try:
            return fast.get(name)
        except Exception:
            try:
                return getattr(fast, name)
            except Exception:
                return None

    info = {}
    try:
        info = ticker.info or {}
    except Exception:
        info = {}

    history = ticker.history(period="1y", auto_adjust=True)
    if history.empty or "Close" not in history:
        raise ValueError("Unable to retrieve a usable one-year price history from Yahoo Finance.")

    close = history["Close"].dropna()
    if close.empty:
        raise ValueError("Closing-price history is empty.")

    spot = float(
        fast_get("lastPrice")
        or info.get("currentPrice")
        or info.get("regularMarketPrice")
        or close.iloc[-1]
    )
    returns = close.pct_change().dropna()
    realized_vol_1y = float(returns.std() * np.sqrt(252)) if not returns.empty else None

    dividend_yield = info.get("dividendYield")
    if dividend_yield is None:
        dividend_yield = 0.0

    expiries = []
    try:
        expiries = list(ticker.options or [])
    except Exception:
        expiries = []

    return {
        "symbol": symbol.upper(),
        "name": info.get("longName") or info.get("shortName") or symbol.upper(),
        "currency": info.get("currency") or fast_get("currency") or "",
        "exchange": info.get("exchange") or "",
        "spot": spot,
        "previous_close": fast_get("previousClose") or info.get("previousClose"),
        "market_cap": info.get("marketCap"),
        "dividend_yield": float(dividend_yield or 0.0),
        "realized_vol_1y": realized_vol_1y,
        "option_expirations": expiries[:30],
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }


def _common_option_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "spot": clean_float(payload.get("spot"), "spot"),
        "strike": clean_float(payload.get("strike"), "strike"),
        "maturity": clean_float(payload.get("maturity"), "maturity"),
        "rate": clean_float(payload.get("rate", 0.02), "rate"),
        "volatility": clean_float(payload.get("volatility"), "volatility"),
        "dividend_yield": clean_float(payload.get("dividend_yield", 0.0), "dividend_yield"),
        "option_type": str(payload.get("option_type", "call")).lower(),
    }


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/search")
def search_underlying():
    query = (request.args.get("q") or "").strip()
    if len(query) < 1:
        return error_response("Enter at least one character.")
    try:
        return json_ok({"results": _search_quotes(query)})
    except Exception as exc:
        return error_response(f"Yahoo Finance search failed: {exc}", 502)


@app.get("/api/market/<symbol>")
def market_data(symbol: str):
    symbol = symbol.strip().upper()
    if not symbol:
        return error_response("Ticker symbol is required.")
    try:
        return json_ok({"market": _ticker_info(symbol)})
    except Exception as exc:
        return error_response(f"Yahoo Finance market-data retrieval failed: {exc}", 502)


@app.get("/api/option-chain/<symbol>/<expiry>")
def option_chain(symbol: str, expiry: str):
    symbol = symbol.strip().upper()
    try:
        ticker = yf.Ticker(symbol)
        chain = ticker.option_chain(expiry)
        calls = chain.calls.copy()
        puts = chain.puts.copy()

        keep = ["contractSymbol", "strike", "lastPrice", "bid", "ask", "impliedVolatility", "volume", "openInterest", "inTheMoney"]
        calls = calls[[col for col in keep if col in calls.columns]].head(80)
        puts = puts[[col for col in keep if col in puts.columns]].head(80)

        return json_ok({
            "symbol": symbol,
            "expiry": expiry,
            "calls": calls.replace({np.nan: None}).to_dict(orient="records"),
            "puts": puts.replace({np.nan: None}).to_dict(orient="records"),
        })
    except Exception as exc:
        return error_response(f"Yahoo Finance option-chain retrieval failed: {exc}", 502)


@app.get("/api/implied-volatility/<symbol>/<expiry>")
def implied_volatility_smile(symbol: str, expiry: str):
    symbol = symbol.strip().upper()
    option_side = str(request.args.get("side", "call")).lower()
    if option_side not in {"call", "put"}:
        return error_response("side must be 'call' or 'put'.")

    try:
        rate = clean_float(request.args.get("rate", 0.02), "rate")
        market = _ticker_info(symbol)
        spot = clean_float(market["spot"], "spot")
        dividend_yield = clean_float(market.get("dividend_yield", 0.0), "dividend_yield")

        expiry_dt = datetime.strptime(expiry, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        now_dt = datetime.now(timezone.utc)
        maturity = max((expiry_dt - now_dt).total_seconds() / (365.0 * 24 * 3600), 1.0 / 365.0)

        ticker = yf.Ticker(symbol)
        chain = ticker.option_chain(expiry)
        frame = chain.calls.copy() if option_side == "call" else chain.puts.copy()

        keep = [
            "contractSymbol",
            "strike",
            "lastPrice",
            "bid",
            "ask",
            "impliedVolatility",
            "volume",
            "openInterest",
            "inTheMoney",
        ]
        frame = frame[[col for col in keep if col in frame.columns]].copy()
        frame = frame.dropna(subset=["strike"]).sort_values("strike")

        rows = []
        for _, row in frame.iterrows():
            strike = float(row["strike"])
            bid = row.get("bid")
            ask = row.get("ask")
            last_price = row.get("lastPrice")
            yahoo_iv = row.get("impliedVolatility")

            midpoint = None
            model_iv_mid = None
            model_iv_last = None

            if pd.notna(bid) and pd.notna(ask) and float(ask) >= float(bid) and float(ask) > 0:
                midpoint = (float(bid) + float(ask)) / 2.0
                try:
                    model_iv_mid = implied_volatility(
                        market_price=midpoint,
                        spot=spot,
                        strike=strike,
                        maturity=maturity,
                        rate=rate,
                        dividend_yield=dividend_yield,
                        option_type=option_side,
                    )
                except Exception:
                    model_iv_mid = None

            if pd.notna(last_price) and float(last_price) > 0:
                try:
                    model_iv_last = implied_volatility(
                        market_price=float(last_price),
                        spot=spot,
                        strike=strike,
                        maturity=maturity,
                        rate=rate,
                        dividend_yield=dividend_yield,
                        option_type=option_side,
                    )
                except Exception:
                    model_iv_last = None

            rows.append(
                {
                    "contract_symbol": None if pd.isna(row.get("contractSymbol")) else str(row.get("contractSymbol")),
                    "strike": strike,
                    "moneyness": strike / spot if spot else None,
                    "bid": None if pd.isna(bid) else float(bid),
                    "ask": None if pd.isna(ask) else float(ask),
                    "midpoint": midpoint,
                    "last_price": None if pd.isna(last_price) else float(last_price),
                    "yahoo_iv": None if pd.isna(yahoo_iv) else float(yahoo_iv),
                    "model_iv_mid": model_iv_mid,
                    "model_iv_last": model_iv_last,
                    "volume": None if pd.isna(row.get("volume")) else float(row.get("volume")),
                    "open_interest": None if pd.isna(row.get("openInterest")) else float(row.get("openInterest")),
                    "in_the_money": None if pd.isna(row.get("inTheMoney")) else bool(row.get("inTheMoney")),
                }
            )

        valid_rows = [
            r for r in rows
            if r["yahoo_iv"] is not None or r["model_iv_mid"] is not None or r["model_iv_last"] is not None
        ]

        iv_candidates = [r["model_iv_mid"] for r in valid_rows if r["model_iv_mid"] is not None]
        if not iv_candidates:
            iv_candidates = [r["yahoo_iv"] for r in valid_rows if r["yahoo_iv"] is not None]

        atm_row = None
        if valid_rows:
            atm_row = min(valid_rows, key=lambda r: abs(r["strike"] - spot))
        atm_iv = None
        if atm_row:
            atm_iv = atm_row["model_iv_mid"]
            if atm_iv is None:
                atm_iv = atm_row["yahoo_iv"]

        summary = {
            "spot": spot,
            "expiry": expiry,
            "maturity_years": maturity,
            "side": option_side,
            "rate": rate,
            "dividend_yield": dividend_yield,
            "points": len(valid_rows),
            "atm_strike": atm_row["strike"] if atm_row else None,
            "atm_iv": atm_iv,
            "min_iv": min(iv_candidates) if iv_candidates else None,
            "max_iv": max(iv_candidates) if iv_candidates else None,
        }

        return json_ok({
            "symbol": symbol,
            "market": market,
            "summary": summary,
            "rows": valid_rows,
        })
    except Exception as exc:
        return error_response(f"Implied-volatility extraction failed: {exc}", 502)


@app.post("/api/price/vanilla")
def price_vanilla():
    payload = request.get_json(force=True, silent=True) or {}
    try:
        inputs = _common_option_payload(payload)
        model = str(payload.get("model", "bsm")).lower()
        american = bool(payload.get("american", False))
        result: Dict[str, Any] = {"model": model, "inputs": inputs}

        if model == "bsm":
            result["price"] = black_scholes_price(**inputs)
            result["greeks"] = black_scholes_greeks(**inputs)
        elif model == "binomial":
            steps = clean_int(payload.get("steps", 400), "steps", default=400)
            result["price"] = crr_binomial_price(**inputs, steps=steps, american=american)
            result["steps"] = steps
            result["american"] = american
        elif model == "monte_carlo":
            n_paths = clean_int(payload.get("n_paths", 100_000), "n_paths", default=100_000)
            result.update(monte_carlo_european(**inputs, n_paths=n_paths))
            result["n_paths"] = n_paths
        elif model == "longstaff_schwartz":
            n_paths = clean_int(payload.get("n_paths", 50_000), "n_paths", default=50_000)
            n_steps = clean_int(payload.get("steps", 60), "steps", default=60)
            degree = clean_int(payload.get("degree", 2), "degree", default=2)
            result.update(
                longstaff_schwartz_american(
                    **inputs, n_paths=n_paths, n_steps=n_steps, polynomial_degree=degree
                )
            )
            result["n_paths"] = n_paths
            result["steps"] = n_steps
            result["degree"] = degree
            result["american"] = True
        else:
            raise ValueError("Unsupported vanilla model.")

        market_price = payload.get("market_price")
        if market_price not in (None, ""):
            iv = implied_volatility(
                market_price=clean_float(market_price, "market_price"),
                spot=inputs["spot"],
                strike=inputs["strike"],
                maturity=inputs["maturity"],
                rate=inputs["rate"],
                dividend_yield=inputs["dividend_yield"],
                option_type=inputs["option_type"],
            )
            result["implied_volatility_from_market_price"] = iv

        return json_ok({"result": result})
    except Exception as exc:
        return error_response(str(exc))


@app.post("/api/price/exotic")
def price_exotic():
    payload = request.get_json(force=True, silent=True) or {}
    try:
        exotic_type = str(payload.get("exotic_type", "asian")).lower()
        inputs = _common_option_payload(payload)
        result: Dict[str, Any] = {"exotic_type": exotic_type, "inputs": inputs}

        if exotic_type == "asian":
            averaging = str(payload.get("averaging", "arithmetic")).lower()
            n_paths = clean_int(payload.get("n_paths", 60_000), "n_paths", default=60_000)
            steps = clean_int(payload.get("steps", 252), "steps", default=252)
            result.update(monte_carlo_asian(**inputs, averaging=averaging, n_paths=n_paths, n_steps=steps))
            result["averaging"] = averaging
            result["n_paths"] = n_paths
            result["steps"] = steps
        elif exotic_type == "barrier":
            barrier = clean_float(payload.get("barrier"), "barrier")
            barrier_type = str(payload.get("barrier_type", "up-and-out")).lower()
            n_paths = clean_int(payload.get("n_paths", 80_000), "n_paths", default=80_000)
            steps = clean_int(payload.get("steps", 252), "steps", default=252)
            result.update(
                monte_carlo_barrier(
                    **inputs,
                    barrier=barrier,
                    barrier_type=barrier_type,
                    n_paths=n_paths,
                    n_steps=steps,
                )
            )
            result["barrier"] = barrier
            result["barrier_type"] = barrier_type
            result["n_paths"] = n_paths
            result["steps"] = steps
        elif exotic_type == "gap":
            trigger_strike = clean_float(payload.get("trigger_strike"), "trigger_strike")
            payoff_strike = clean_float(payload.get("payoff_strike"), "payoff_strike")
            result["price"] = gap_option_price(
                spot=inputs["spot"],
                trigger_strike=trigger_strike,
                payoff_strike=payoff_strike,
                maturity=inputs["maturity"],
                rate=inputs["rate"],
                volatility=inputs["volatility"],
                dividend_yield=inputs["dividend_yield"],
                option_type=inputs["option_type"],
            )
            result["trigger_strike"] = trigger_strike
            result["payoff_strike"] = payoff_strike
        else:
            raise ValueError("Unsupported exotic option type.")

        return json_ok({"result": result})
    except Exception as exc:
        return error_response(str(exc))


@app.post("/api/price/batch")
def price_batch():
    payload = request.get_json(force=True, silent=True) or {}
    rows = payload.get("rows") or []
    if not isinstance(rows, list) or not rows:
        return error_response("Batch payload must contain a non-empty 'rows' array.")
    results = []
    errors = []

    for idx, row in enumerate(rows, start=1):
        try:
            inputs = _common_option_payload(row)
            model = str(row.get("model", "bsm")).lower()
            if model == "bsm":
                result = {"price": black_scholes_price(**inputs), "greeks": black_scholes_greeks(**inputs)}
            elif model == "binomial":
                result = {
                    "price": crr_binomial_price(
                        **inputs,
                        steps=clean_int(row.get("steps", 400), "steps", default=400),
                        american=bool(row.get("american", False)),
                    )
                }
            elif model == "monte_carlo":
                result = {
                    **monte_carlo_european(
                        **inputs,
                        n_paths=clean_int(row.get("n_paths", 100_000), "n_paths", default=100_000),
                    )
                }
            else:
                raise ValueError("Unsupported model in batch row.")
            results.append({"row": idx, "ok": True, "inputs": inputs, "model": model, **result})
        except Exception as exc:
            errors.append({"row": idx, "ok": False, "error": str(exc)})

    return json_ok({"results": results, "errors": errors})


@app.post("/api/price/structured")
def price_structured():
    payload = request.get_json(force=True, silent=True) or {}
    try:
        product_type = str(payload.get("product_type", "capital_protected")).lower()
        common = {
            "spot": clean_float(payload.get("spot"), "spot"),
            "maturity": clean_float(payload.get("maturity"), "maturity"),
            "rate": clean_float(payload.get("rate", 0.02), "rate"),
            "volatility": clean_float(payload.get("volatility"), "volatility"),
            "dividend_yield": clean_float(payload.get("dividend_yield", 0.0), "dividend_yield"),
            "notional": clean_float(payload.get("notional", 1000), "notional"),
            "n_paths": clean_int(payload.get("n_paths", 80_000), "n_paths", default=80_000),
        }

        if product_type == "capital_protected":
            result = capital_protected_note_mc(
                **common,
                capital_floor=clean_float(payload.get("capital_floor", 0.90), "capital_floor"),
                participation=clean_float(payload.get("participation", 1.00), "participation"),
            )
        elif product_type == "reverse_convertible":
            result = reverse_convertible_mc(
                **common,
                coupon_rate=clean_float(payload.get("coupon_rate", 0.10), "coupon_rate"),
                protection_barrier=clean_float(payload.get("protection_barrier", 0.70), "protection_barrier"),
            )
        elif product_type == "autocallable":
            result = autocallable_note_mc(
                **common,
                annual_coupon_rate=clean_float(payload.get("annual_coupon_rate", 0.10), "annual_coupon_rate"),
                autocall_barrier=clean_float(payload.get("autocall_barrier", 1.00), "autocall_barrier"),
                coupon_barrier=clean_float(payload.get("coupon_barrier", 0.70), "coupon_barrier"),
                protection_barrier=clean_float(payload.get("protection_barrier", 0.60), "protection_barrier"),
                observations_per_year=clean_int(payload.get("observations_per_year", 4), "observations_per_year", default=4),
                memory_coupon=bool(payload.get("memory_coupon", True)),
            )
        else:
            raise ValueError("Unsupported structured product type.")

        return json_ok({"product_type": product_type, "inputs": common, "result": result})
    except Exception as exc:
        return error_response(str(exc))


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
