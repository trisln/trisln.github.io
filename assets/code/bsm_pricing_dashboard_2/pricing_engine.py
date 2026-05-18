from __future__ import annotations

from dataclasses import dataclass
from math import exp, log, sqrt
from typing import Dict, Iterable, Literal, Optional

import numpy as np
from scipy.stats import norm
from scipy.optimize import brentq


OptionType = Literal["call", "put"]


def _validate_positive(**kwargs: float) -> None:
    for name, value in kwargs.items():
        if value is None or not np.isfinite(value) or value <= 0:
            raise ValueError(f"{name} must be strictly positive.")


def _validate_non_negative(**kwargs: float) -> None:
    for name, value in kwargs.items():
        if value is None or not np.isfinite(value) or value < 0:
            raise ValueError(f"{name} must be non-negative.")


def _is_call(option_type: str) -> bool:
    option_type = str(option_type).lower()
    if option_type not in {"call", "put"}:
        raise ValueError("option_type must be 'call' or 'put'.")
    return option_type == "call"


def intrinsic_value(spot: float, strike: float, option_type: OptionType) -> float:
    return max(spot - strike, 0.0) if _is_call(option_type) else max(strike - spot, 0.0)


def bsm_d1_d2(
    spot: float,
    strike: float,
    maturity: float,
    rate: float,
    volatility: float,
    dividend_yield: float = 0.0,
) -> tuple[float, float]:
    _validate_positive(spot=spot, strike=strike, maturity=maturity, volatility=volatility)
    d1 = (log(spot / strike) + (rate - dividend_yield + 0.5 * volatility**2) * maturity) / (
        volatility * sqrt(maturity)
    )
    d2 = d1 - volatility * sqrt(maturity)
    return d1, d2


def black_scholes_price(
    spot: float,
    strike: float,
    maturity: float,
    rate: float,
    volatility: float,
    dividend_yield: float = 0.0,
    option_type: OptionType = "call",
) -> float:
    _validate_positive(spot=spot, strike=strike)
    _validate_non_negative(maturity=maturity, volatility=volatility)

    if maturity == 0:
        return intrinsic_value(spot, strike, option_type)
    if volatility == 0:
        forward_intrinsic = max(
            spot * exp(-dividend_yield * maturity) - strike * exp(-rate * maturity), 0.0
        )
        if _is_call(option_type):
            return forward_intrinsic
        return max(
            strike * exp(-rate * maturity) - spot * exp(-dividend_yield * maturity), 0.0
        )

    d1, d2 = bsm_d1_d2(spot, strike, maturity, rate, volatility, dividend_yield)
    discount_q = exp(-dividend_yield * maturity)
    discount_r = exp(-rate * maturity)

    if _is_call(option_type):
        return spot * discount_q * norm.cdf(d1) - strike * discount_r * norm.cdf(d2)
    return strike * discount_r * norm.cdf(-d2) - spot * discount_q * norm.cdf(-d1)


def black_scholes_greeks(
    spot: float,
    strike: float,
    maturity: float,
    rate: float,
    volatility: float,
    dividend_yield: float = 0.0,
    option_type: OptionType = "call",
) -> Dict[str, float]:
    _validate_positive(spot=spot, strike=strike, maturity=maturity, volatility=volatility)
    d1, d2 = bsm_d1_d2(spot, strike, maturity, rate, volatility, dividend_yield)
    discount_q = exp(-dividend_yield * maturity)
    discount_r = exp(-rate * maturity)
    pdf_d1 = norm.pdf(d1)

    if _is_call(option_type):
        delta = discount_q * norm.cdf(d1)
        theta = (
            -(spot * discount_q * pdf_d1 * volatility) / (2 * sqrt(maturity))
            - rate * strike * discount_r * norm.cdf(d2)
            + dividend_yield * spot * discount_q * norm.cdf(d1)
        )
        rho = strike * maturity * discount_r * norm.cdf(d2)
    else:
        delta = -discount_q * norm.cdf(-d1)
        theta = (
            -(spot * discount_q * pdf_d1 * volatility) / (2 * sqrt(maturity))
            + rate * strike * discount_r * norm.cdf(-d2)
            - dividend_yield * spot * discount_q * norm.cdf(-d1)
        )
        rho = -strike * maturity * discount_r * norm.cdf(-d2)

    gamma = discount_q * pdf_d1 / (spot * volatility * sqrt(maturity))
    vega = spot * discount_q * pdf_d1 * sqrt(maturity)

    return {
        "delta": float(delta),
        "gamma": float(gamma),
        "vega": float(vega),
        "theta_per_year": float(theta),
        "theta_per_day": float(theta / 365.0),
        "rho": float(rho),
        "d1": float(d1),
        "d2": float(d2),
    }


def implied_volatility(
    market_price: float,
    spot: float,
    strike: float,
    maturity: float,
    rate: float,
    dividend_yield: float = 0.0,
    option_type: OptionType = "call",
) -> float:
    _validate_positive(spot=spot, strike=strike, maturity=maturity)
    _validate_non_negative(market_price=market_price)

    intrinsic = intrinsic_value(spot, strike, option_type)
    if market_price < intrinsic - 1e-10:
        raise ValueError("Market price is below intrinsic value; no admissible implied volatility.")

    def objective(vol: float) -> float:
        return black_scholes_price(
            spot=spot,
            strike=strike,
            maturity=maturity,
            rate=rate,
            volatility=vol,
            dividend_yield=dividend_yield,
            option_type=option_type,
        ) - market_price

    try:
        return float(brentq(objective, 1e-8, 5.0, xtol=1e-10, rtol=1e-10, maxiter=200))
    except ValueError as exc:
        raise ValueError("Unable to bracket an implied volatility in [0, 500%].") from exc


def crr_binomial_price(
    spot: float,
    strike: float,
    maturity: float,
    rate: float,
    volatility: float,
    dividend_yield: float = 0.0,
    option_type: OptionType = "call",
    steps: int = 300,
    american: bool = False,
) -> float:
    _validate_positive(spot=spot, strike=strike, maturity=maturity, volatility=volatility)
    if steps < 1:
        raise ValueError("steps must be >= 1.")

    dt = maturity / steps
    u = exp(volatility * sqrt(dt))
    d = 1.0 / u
    growth = exp((rate - dividend_yield) * dt)
    p = (growth - d) / (u - d)
    if not 0 <= p <= 1:
        raise ValueError("Risk-neutral probability outside [0, 1]. Increase steps or inspect inputs.")

    j = np.arange(steps + 1)
    terminal_spots = spot * (u ** j) * (d ** (steps - j))
    values = (
        np.maximum(terminal_spots - strike, 0.0)
        if _is_call(option_type)
        else np.maximum(strike - terminal_spots, 0.0)
    )

    discount = exp(-rate * dt)

    for t in range(steps - 1, -1, -1):
        values = discount * (p * values[1 : t + 2] + (1 - p) * values[0 : t + 1])
        if american:
            j_t = np.arange(t + 1)
            spots_t = spot * (u ** j_t) * (d ** (t - j_t))
            exercise = (
                np.maximum(spots_t - strike, 0.0)
                if _is_call(option_type)
                else np.maximum(strike - spots_t, 0.0)
            )
            values = np.maximum(values, exercise)

    return float(values[0])


def _simulate_gbm_paths(
    spot: float,
    maturity: float,
    rate: float,
    volatility: float,
    dividend_yield: float,
    n_paths: int,
    n_steps: int,
    seed: Optional[int] = None,
    antithetic: bool = True,
) -> np.ndarray:
    _validate_positive(spot=spot, maturity=maturity, volatility=volatility)
    if n_paths < 100:
        raise ValueError("n_paths must be >= 100.")
    if n_steps < 1:
        raise ValueError("n_steps must be >= 1.")

    rng = np.random.default_rng(seed)
    dt = maturity / n_steps
    drift = (rate - dividend_yield - 0.5 * volatility**2) * dt
    diffusion = volatility * sqrt(dt)

    if antithetic:
        half = (n_paths + 1) // 2
        z_half = rng.standard_normal((half, n_steps))
        z = np.vstack([z_half, -z_half])[:n_paths]
    else:
        z = rng.standard_normal((n_paths, n_steps))

    log_returns = drift + diffusion * z
    log_paths = np.cumsum(log_returns, axis=1)
    paths = np.empty((n_paths, n_steps + 1))
    paths[:, 0] = spot
    paths[:, 1:] = spot * np.exp(log_paths)
    return paths


def monte_carlo_european(
    spot: float,
    strike: float,
    maturity: float,
    rate: float,
    volatility: float,
    dividend_yield: float = 0.0,
    option_type: OptionType = "call",
    n_paths: int = 100_000,
    seed: Optional[int] = 42,
) -> Dict[str, float]:
    _validate_positive(spot=spot, strike=strike, maturity=maturity, volatility=volatility)
    rng = np.random.default_rng(seed)
    z = rng.standard_normal(n_paths)
    s_t = spot * np.exp(
        (rate - dividend_yield - 0.5 * volatility**2) * maturity
        + volatility * sqrt(maturity) * z
    )
    payoff = np.maximum(s_t - strike, 0.0) if _is_call(option_type) else np.maximum(strike - s_t, 0.0)
    discounted = exp(-rate * maturity) * payoff
    price = float(discounted.mean())
    stderr = float(discounted.std(ddof=1) / sqrt(n_paths))
    ci_low = price - 1.96 * stderr
    ci_high = price + 1.96 * stderr
    return {"price": price, "std_error": stderr, "ci95_low": ci_low, "ci95_high": ci_high}


def monte_carlo_asian(
    spot: float,
    strike: float,
    maturity: float,
    rate: float,
    volatility: float,
    dividend_yield: float = 0.0,
    option_type: OptionType = "call",
    averaging: Literal["arithmetic", "geometric"] = "arithmetic",
    n_paths: int = 60_000,
    n_steps: int = 252,
    seed: Optional[int] = 42,
) -> Dict[str, float]:
    paths = _simulate_gbm_paths(
        spot, maturity, rate, volatility, dividend_yield, n_paths, n_steps, seed=seed
    )
    observed = paths[:, 1:]
    if averaging == "arithmetic":
        avg = observed.mean(axis=1)
    elif averaging == "geometric":
        avg = np.exp(np.log(observed).mean(axis=1))
    else:
        raise ValueError("averaging must be 'arithmetic' or 'geometric'.")

    payoff = np.maximum(avg - strike, 0.0) if _is_call(option_type) else np.maximum(strike - avg, 0.0)
    discounted = exp(-rate * maturity) * payoff
    price = float(discounted.mean())
    stderr = float(discounted.std(ddof=1) / sqrt(n_paths))
    return {
        "price": price,
        "std_error": stderr,
        "ci95_low": price - 1.96 * stderr,
        "ci95_high": price + 1.96 * stderr,
    }


def monte_carlo_barrier(
    spot: float,
    strike: float,
    barrier: float,
    maturity: float,
    rate: float,
    volatility: float,
    dividend_yield: float = 0.0,
    option_type: OptionType = "call",
    barrier_type: Literal["up-and-out", "down-and-out", "up-and-in", "down-and-in"] = "up-and-out",
    n_paths: int = 80_000,
    n_steps: int = 252,
    seed: Optional[int] = 42,
) -> Dict[str, float]:
    _validate_positive(barrier=barrier)
    paths = _simulate_gbm_paths(
        spot, maturity, rate, volatility, dividend_yield, n_paths, n_steps, seed=seed
    )
    max_path = paths.max(axis=1)
    min_path = paths.min(axis=1)

    if barrier_type == "up-and-out":
        active = max_path < barrier
    elif barrier_type == "down-and-out":
        active = min_path > barrier
    elif barrier_type == "up-and-in":
        active = max_path >= barrier
    elif barrier_type == "down-and-in":
        active = min_path <= barrier
    else:
        raise ValueError("Unsupported barrier_type.")

    terminal = paths[:, -1]
    vanilla = np.maximum(terminal - strike, 0.0) if _is_call(option_type) else np.maximum(strike - terminal, 0.0)
    payoff = vanilla * active.astype(float)
    discounted = exp(-rate * maturity) * payoff
    price = float(discounted.mean())
    stderr = float(discounted.std(ddof=1) / sqrt(n_paths))
    return {
        "price": price,
        "std_error": stderr,
        "ci95_low": price - 1.96 * stderr,
        "ci95_high": price + 1.96 * stderr,
    }


def gap_option_price(
    spot: float,
    trigger_strike: float,
    payoff_strike: float,
    maturity: float,
    rate: float,
    volatility: float,
    dividend_yield: float = 0.0,
    option_type: OptionType = "call",
) -> float:
    _validate_positive(
        spot=spot,
        trigger_strike=trigger_strike,
        payoff_strike=payoff_strike,
        maturity=maturity,
        volatility=volatility,
    )
    d1, d2 = bsm_d1_d2(spot, trigger_strike, maturity, rate, volatility, dividend_yield)
    discount_q = exp(-dividend_yield * maturity)
    discount_r = exp(-rate * maturity)

    if _is_call(option_type):
        return float(spot * discount_q * norm.cdf(d1) - payoff_strike * discount_r * norm.cdf(d2))
    return float(payoff_strike * discount_r * norm.cdf(-d2) - spot * discount_q * norm.cdf(-d1))


def longstaff_schwartz_american(
    spot: float,
    strike: float,
    maturity: float,
    rate: float,
    volatility: float,
    dividend_yield: float = 0.0,
    option_type: OptionType = "put",
    n_paths: int = 50_000,
    n_steps: int = 60,
    seed: Optional[int] = 42,
    polynomial_degree: int = 2,
) -> Dict[str, float]:
    if polynomial_degree < 1:
        raise ValueError("polynomial_degree must be >= 1.")

    paths = _simulate_gbm_paths(
        spot, maturity, rate, volatility, dividend_yield, n_paths, n_steps, seed=seed
    )
    dt = maturity / n_steps
    discount = exp(-rate * dt)

    exercise = (
        np.maximum(paths - strike, 0.0)
        if _is_call(option_type)
        else np.maximum(strike - paths, 0.0)
    )
    cashflows = exercise[:, -1].copy()
    stopping_time = np.full(n_paths, n_steps, dtype=int)

    for t in range(n_steps - 1, 0, -1):
        alive = stopping_time > t
        itm = exercise[:, t] > 0
        mask = alive & itm
        if mask.sum() < polynomial_degree + 2:
            continue

        x = paths[mask, t]
        y = cashflows[mask] * np.exp(-rate * dt * (stopping_time[mask] - t))
        basis = np.column_stack([x**k for k in range(polynomial_degree + 1)])
        beta, *_ = np.linalg.lstsq(basis, y, rcond=None)
        continuation = basis @ beta
        immediate = exercise[mask, t]

        exercise_now_local = immediate > continuation
        global_indices = np.flatnonzero(mask)[exercise_now_local]
        cashflows[global_indices] = exercise[global_indices, t]
        stopping_time[global_indices] = t

    discounted_cashflows = cashflows * np.exp(-rate * dt * stopping_time)
    price = float(discounted_cashflows.mean())
    stderr = float(discounted_cashflows.std(ddof=1) / sqrt(n_paths))
    return {
        "price": price,
        "std_error": stderr,
        "ci95_low": price - 1.96 * stderr,
        "ci95_high": price + 1.96 * stderr,
    }


def capital_protected_note_mc(
    spot: float,
    maturity: float,
    rate: float,
    volatility: float,
    dividend_yield: float = 0.0,
    notional: float = 1000.0,
    capital_floor: float = 0.90,
    participation: float = 1.00,
    n_paths: int = 120_000,
    seed: Optional[int] = 42,
) -> Dict[str, float]:
    _validate_positive(spot=spot, maturity=maturity, volatility=volatility, notional=notional)
    _validate_non_negative(capital_floor=capital_floor, participation=participation)
    rng = np.random.default_rng(seed)
    z = rng.standard_normal(n_paths)
    s_t = spot * np.exp(
        (rate - dividend_yield - 0.5 * volatility**2) * maturity
        + volatility * sqrt(maturity) * z
    )
    total_return = s_t / spot - 1.0
    payoff = notional * (capital_floor + participation * np.maximum(total_return, 0.0))
    discounted = np.exp(-rate * maturity) * payoff
    price = float(discounted.mean())
    stderr = float(discounted.std(ddof=1) / sqrt(n_paths))
    return {"price": price, "std_error": stderr, "ci95_low": price - 1.96 * stderr, "ci95_high": price + 1.96 * stderr}


def reverse_convertible_mc(
    spot: float,
    maturity: float,
    rate: float,
    volatility: float,
    dividend_yield: float = 0.0,
    notional: float = 1000.0,
    coupon_rate: float = 0.10,
    protection_barrier: float = 0.70,
    n_paths: int = 120_000,
    seed: Optional[int] = 42,
) -> Dict[str, float]:
    _validate_positive(spot=spot, maturity=maturity, volatility=volatility, notional=notional)
    _validate_positive(protection_barrier=protection_barrier)
    _validate_non_negative(coupon_rate=coupon_rate)
    rng = np.random.default_rng(seed)
    z = rng.standard_normal(n_paths)
    s_t = spot * np.exp(
        (rate - dividend_yield - 0.5 * volatility**2) * maturity
        + volatility * sqrt(maturity) * z
    )
    ratio = s_t / spot
    redemption = np.where(ratio >= protection_barrier, notional, notional * ratio)
    coupon = notional * coupon_rate
    payoff = redemption + coupon
    discounted = np.exp(-rate * maturity) * payoff
    price = float(discounted.mean())
    stderr = float(discounted.std(ddof=1) / sqrt(n_paths))
    return {"price": price, "std_error": stderr, "ci95_low": price - 1.96 * stderr, "ci95_high": price + 1.96 * stderr}


def autocallable_note_mc(
    spot: float,
    maturity: float,
    rate: float,
    volatility: float,
    dividend_yield: float = 0.0,
    notional: float = 1000.0,
    annual_coupon_rate: float = 0.10,
    autocall_barrier: float = 1.00,
    coupon_barrier: float = 0.70,
    protection_barrier: float = 0.60,
    observations_per_year: int = 4,
    memory_coupon: bool = True,
    n_paths: int = 80_000,
    seed: Optional[int] = 42,
) -> Dict[str, float]:
    _validate_positive(
        spot=spot,
        maturity=maturity,
        volatility=volatility,
        notional=notional,
        autocall_barrier=autocall_barrier,
        coupon_barrier=coupon_barrier,
        protection_barrier=protection_barrier,
    )
    if observations_per_year < 1:
        raise ValueError("observations_per_year must be >= 1.")
    _validate_non_negative(annual_coupon_rate=annual_coupon_rate)

    n_obs = max(1, int(round(maturity * observations_per_year)))
    n_steps = n_obs
    paths = _simulate_gbm_paths(
        spot, maturity, rate, volatility, dividend_yield, n_paths, n_steps, seed=seed
    )
    obs = paths[:, 1:]
    ratios = obs / spot

    dt_obs = maturity / n_obs
    coupon_per_obs = annual_coupon_rate / observations_per_year * notional

    cashflows = np.zeros(n_paths)
    redemption_time = np.full(n_paths, maturity)
    alive = np.ones(n_paths, dtype=bool)
    unpaid_coupons = np.zeros(n_paths)

    for obs_idx in range(n_obs):
        ratio = ratios[:, obs_idx]
        current_time = (obs_idx + 1) * dt_obs

        coupon_due = alive & (ratio >= coupon_barrier)
        if memory_coupon:
            coupon_amount = coupon_per_obs + unpaid_coupons[coupon_due]
            unpaid_coupons[coupon_due] = 0.0
        else:
            coupon_amount = np.full(coupon_due.sum(), coupon_per_obs)

        if coupon_due.any():
            cashflows[coupon_due] += coupon_amount * np.exp(-rate * current_time)

        if memory_coupon:
            missed = alive & ~coupon_due
            unpaid_coupons[missed] += coupon_per_obs

        autocall = alive & (ratio >= autocall_barrier)
        if autocall.any():
            cashflows[autocall] += notional * np.exp(-rate * current_time)
            redemption_time[autocall] = current_time
            alive[autocall] = False

    final_ratio = ratios[:, -1]
    final_alive = alive
    if final_alive.any():
        redemption = np.where(
            final_ratio[final_alive] >= protection_barrier,
            notional,
            notional * final_ratio[final_alive],
        )
        cashflows[final_alive] += redemption * np.exp(-rate * maturity)

    price = float(cashflows.mean())
    stderr = float(cashflows.std(ddof=1) / sqrt(n_paths))
    autocall_probability = float((~alive).mean())
    capital_loss_probability = float((alive & (final_ratio < protection_barrier)).mean())
    return {
        "price": price,
        "std_error": stderr,
        "ci95_low": price - 1.96 * stderr,
        "ci95_high": price + 1.96 * stderr,
        "autocall_probability": autocall_probability,
        "capital_loss_probability": capital_loss_probability,
    }


def clean_float(value, field: str, allow_none: bool = False) -> Optional[float]:
    if allow_none and (value is None or value == ""):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric.") from exc
    if not np.isfinite(result):
        raise ValueError(f"{field} must be finite.")
    return result


def clean_int(value, field: str, default: Optional[int] = None) -> int:
    if value is None or value == "":
        if default is None:
            raise ValueError(f"{field} must be an integer.")
        return int(default)
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be an integer.") from exc
