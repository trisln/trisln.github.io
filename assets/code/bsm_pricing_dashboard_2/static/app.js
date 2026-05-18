const state = {
  market: null,
};

function $(id) {
  return document.getElementById(id);
}

function formatNumber(value, digits = 4) {
  if (value === null || value === undefined || value === "") return "—";
  const num = Number(value);
  if (!Number.isFinite(num)) return String(value);
  return num.toLocaleString("fr-FR", { maximumFractionDigits: digits, minimumFractionDigits: digits });
}

function formatPercent(value, digits = 2) {
  if (value === null || value === undefined || value === "") return "—";
  return `${formatNumber(Number(value) * 100, digits)} %`;
}

function formToObject(form) {
  const data = new FormData(form);
  const obj = {};
  for (const [key, value] of data.entries()) {
    obj[key] = value;
  }
  form.querySelectorAll('input[type="checkbox"]').forEach((cb) => {
    obj[cb.name] = cb.checked;
  });
  return obj;
}

async function apiJson(url, options = {}) {
  const response = await fetch(url, options);
  const payload = await response.json();
  if (!response.ok || payload.ok === false) {
    throw new Error(payload.error || "Erreur API.");
  }
  return payload;
}

function setOutput(container, html) {
  container.innerHTML = html;
}

function errorBox(message) {
  return `<div class="error">${message}</div>`;
}

function noticeBox(message) {
  return `<div class="notice">${message}</div>`;
}

function resultMetrics(metrics) {
  return `
    <div class="result-metrics">
      ${metrics
        .map(
          ([label, value]) => `
            <div><span>${label}</span><strong>${value}</strong></div>
          `
        )
        .join("")}
    </div>
  `;
}

function jsonBlock(data) {
  return `<pre class="code-block">${escapeHtml(JSON.stringify(data, null, 2))}</pre>`;
}

function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

async function searchUnderlying() {
  const query = $("search-query").value.trim();
  const results = $("search-results");
  if (!query) {
    results.innerHTML = errorBox("Saisissez un ticker ou un nom.");
    return;
  }
  results.innerHTML = noticeBox("Recherche en cours...");
  try {
    const data = await apiJson(`/api/search?q=${encodeURIComponent(query)}`);
    if (!data.results.length) {
      results.innerHTML = noticeBox("Aucun résultat trouvé.");
      return;
    }
    results.innerHTML = data.results
      .map(
        (r) => `
          <div class="search-item">
            <div>
              <h4>${escapeHtml(r.symbol)} — ${escapeHtml(r.name || "")}</h4>
              <p>${escapeHtml(r.exchange || "")} ${r.quote_type ? " · " + escapeHtml(r.quote_type) : ""}</p>
            </div>
            <button data-symbol="${escapeHtml(r.symbol)}" class="select-symbol">Sélectionner</button>
          </div>
        `
      )
      .join("");
  } catch (error) {
    results.innerHTML = errorBox(error.message);
  }
}

async function loadMarket(symbol) {
  $("market-card").classList.remove("hidden");
  $("market-name").textContent = "Chargement...";
  $("market-symbol").textContent = symbol;
  try {
    const data = await apiJson(`/api/market/${encodeURIComponent(symbol)}`);
    state.market = data.market;
    renderMarket(data.market);
    injectMarketInputs(data.market);
  } catch (error) {
    $("market-card").innerHTML = errorBox(error.message);
  }
}

function renderMarket(market) {
  $("market-name").textContent = market.name;
  $("market-symbol").textContent = `${market.symbol}${market.exchange ? " · " + market.exchange : ""}`;
  $("market-spot").textContent = formatNumber(market.spot, 4);
  $("market-vol").textContent = formatPercent(market.realized_vol_1y, 2);
  $("market-div").textContent = formatPercent(market.dividend_yield, 2);
  $("market-currency").textContent = market.currency || "—";

  const expiry = $("expiry-select");
  const ivExpiry = $("iv-expiry");
  const ivSymbol = $("iv-symbol");
  expiry.innerHTML = "";
  ivExpiry.innerHTML = "";
  ivSymbol.value = market.symbol || "";

  const expirations = market.option_expirations || [];
  if (!expirations.length) {
    expiry.innerHTML = `<option value="">Aucune échéance disponible</option>`;
    ivExpiry.innerHTML = `<option value="">Aucune échéance disponible</option>`;
    $("load-chain-btn").disabled = true;
  } else {
    $("load-chain-btn").disabled = false;
    expirations.forEach((date) => {
      expiry.insertAdjacentHTML("beforeend", `<option value="${escapeHtml(date)}">${escapeHtml(date)}</option>`);
      ivExpiry.insertAdjacentHTML("beforeend", `<option value="${escapeHtml(date)}">${escapeHtml(date)}</option>`);
    });
  }
}

function injectMarketInputs(market) {
  document.querySelectorAll('input[name="spot"]').forEach((input) => {
    input.value = market.spot ?? "";
  });
  document.querySelectorAll('input[name="volatility"]').forEach((input) => {
    if (market.realized_vol_1y) input.value = Number(market.realized_vol_1y).toFixed(4);
  });
  document.querySelectorAll('input[name="dividend_yield"]').forEach((input) => {
    input.value = Number(market.dividend_yield || 0).toFixed(4);
  });
}

async function loadOptionChain() {
  if (!state.market) return;
  const expiry = $("expiry-select").value;
  const preview = $("chain-preview");
  if (!expiry) {
    preview.innerHTML = errorBox("Sélectionnez une échéance.");
    return;
  }
  preview.innerHTML = noticeBox("Chargement de la chaîne d’options...");
  try {
    const data = await apiJson(`/api/option-chain/${encodeURIComponent(state.market.symbol)}/${encodeURIComponent(expiry)}`);
    preview.innerHTML = renderChainPreview(data.calls, data.puts);
  } catch (error) {
    preview.innerHTML = errorBox(error.message);
  }
}

function renderChainPreview(calls, puts) {
  const renderTable = (title, rows) => {
    if (!rows.length) return `<p>${title} : aucune donnée.</p>`;
    const headers = ["strike", "lastPrice", "bid", "ask", "impliedVolatility", "volume", "openInterest"];
    return `
      <h4>${title}</h4>
      <table class="chain-table">
        <thead><tr>${headers.map((h) => `<th>${h}</th>`).join("")}</tr></thead>
        <tbody>
          ${rows.slice(0, 12).map((row) => `
            <tr>
              ${headers.map((h) => `<td>${h === "impliedVolatility" ? formatPercent(row[h], 2) : formatNumber(row[h], 4)}</td>`).join("")}
            </tr>
          `).join("")}
        </tbody>
      </table>
    `;
  };
  return renderTable("Calls", calls) + renderTable("Puts", puts);
}

function activateTab(target) {
  document.querySelectorAll(".tab").forEach((tab) => tab.classList.toggle("active", tab.dataset.tab === target));
  document.querySelectorAll(".tab-content").forEach((content) => content.classList.toggle("active", content.id === `tab-${target}`));
}

async function priceVanilla(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const output = $("vanilla-output");
  output.innerHTML = noticeBox("Calcul en cours...");
  try {
    const payload = formToObject(form);
    const data = await apiJson("/api/price/vanilla", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const r = data.result;
    const metrics = [["Prix", formatNumber(r.price, 6)]];
    if (r.implied_volatility_from_market_price !== undefined) {
      metrics.push(["IV extraite", formatPercent(r.implied_volatility_from_market_price, 3)]);
    }
    if (r.std_error !== undefined) {
      metrics.push(["Erreur std.", formatNumber(r.std_error, 6)]);
      metrics.push(["IC 95 %", `${formatNumber(r.ci95_low, 6)} – ${formatNumber(r.ci95_high, 6)}`]);
    }
    let greeks = "";
    if (r.greeks) {
      greeks = resultMetrics([
        ["Delta", formatNumber(r.greeks.delta, 6)],
        ["Gamma", formatNumber(r.greeks.gamma, 6)],
        ["Vega", formatNumber(r.greeks.vega, 6)],
        ["Theta / jour", formatNumber(r.greeks.theta_per_day, 6)],
        ["Rho", formatNumber(r.greeks.rho, 6)],
      ]);
    }
    output.innerHTML = `
      <div class="result-card">
        <h3>Résultat — ${escapeHtml(r.model)}</h3>
        <p>Pricing de l’option et diagnostics associés.</p>
        ${resultMetrics(metrics)}
        ${greeks}
        ${jsonBlock(r)}
      </div>
    `;
  } catch (error) {
    output.innerHTML = errorBox(error.message);
  }
}


function lineChartSvg(points, {
  width = 980,
  height = 380,
  xLabel = "Strike",
  yLabel = "Volatilité implicite",
} = {}) {
  const clean = points.filter((p) => Number.isFinite(p.x) && Number.isFinite(p.y));
  if (clean.length < 2) {
    return noticeBox("Pas assez de points exploitables pour tracer une smile.");
  }

  const pad = { top: 24, right: 24, bottom: 58, left: 72 };
  const xs = clean.map((p) => p.x);
  const ys = clean.map((p) => p.y);
  const xMin = Math.min(...xs);
  const xMax = Math.max(...xs);
  const yMinRaw = Math.min(...ys);
  const yMaxRaw = Math.max(...ys);
  const yMargin = Math.max((yMaxRaw - yMinRaw) * 0.12, 0.01);
  const yMin = Math.max(0, yMinRaw - yMargin);
  const yMax = yMaxRaw + yMargin;

  const innerW = width - pad.left - pad.right;
  const innerH = height - pad.top - pad.bottom;
  const sx = (x) => pad.left + ((x - xMin) / Math.max(xMax - xMin, 1e-9)) * innerW;
  const sy = (y) => pad.top + innerH - ((y - yMin) / Math.max(yMax - yMin, 1e-9)) * innerH;

  const ticksX = 6;
  const ticksY = 5;
  const xTicks = Array.from({ length: ticksX }, (_, i) => xMin + (i / (ticksX - 1)) * (xMax - xMin));
  const yTicks = Array.from({ length: ticksY }, (_, i) => yMin + (i / (ticksY - 1)) * (yMax - yMin));

  const path = clean
    .sort((a, b) => a.x - b.x)
    .map((p, i) => `${i === 0 ? "M" : "L"} ${sx(p.x).toFixed(2)} ${sy(p.y).toFixed(2)}`)
    .join(" ");

  const circles = clean
    .map((p) => `<circle cx="${sx(p.x).toFixed(2)}" cy="${sy(p.y).toFixed(2)}" r="4.5"></circle>`)
    .join("");

  return `
    <div class="chart-card">
      <svg class="iv-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="Courbe de volatilité implicite">
        <rect x="0" y="0" width="${width}" height="${height}" rx="18"></rect>
        ${yTicks.map((t) => `
          <line class="grid-line" x1="${pad.left}" y1="${sy(t)}" x2="${width - pad.right}" y2="${sy(t)}"></line>
          <text class="tick-label" x="${pad.left - 12}" y="${sy(t) + 4}" text-anchor="end">${formatPercent(t, 1)}</text>
        `).join("")}
        ${xTicks.map((t) => `
          <line class="grid-line vertical" x1="${sx(t)}" y1="${pad.top}" x2="${sx(t)}" y2="${height - pad.bottom}"></line>
          <text class="tick-label" x="${sx(t)}" y="${height - pad.bottom + 24}" text-anchor="middle">${formatNumber(t, 2)}</text>
        `).join("")}
        <line class="axis-line" x1="${pad.left}" y1="${height - pad.bottom}" x2="${width - pad.right}" y2="${height - pad.bottom}"></line>
        <line class="axis-line" x1="${pad.left}" y1="${pad.top}" x2="${pad.left}" y2="${height - pad.bottom}"></line>
        <path class="iv-line" d="${path}"></path>
        <g class="iv-points">${circles}</g>
        <text class="axis-label" x="${pad.left + innerW / 2}" y="${height - 14}" text-anchor="middle">${xLabel}</text>
        <text class="axis-label rotated" x="${-(pad.top + innerH / 2)}" y="22" text-anchor="middle">${yLabel}</text>
      </svg>
    </div>
  `;
}

function ivTable(rows) {
  if (!rows.length) return noticeBox("Aucune donnée de volatilité implicite exploitable.");
  return `
    <div class="table-wrap iv-table-wrap">
      <table class="iv-table">
        <thead>
          <tr>
            <th>Strike</th>
            <th>Moneyness K/S</th>
            <th>Bid</th>
            <th>Ask</th>
            <th>Midpoint</th>
            <th>IV Yahoo</th>
            <th>IV recalculée au midpoint</th>
            <th>IV sur last price</th>
            <th>Volume</th>
            <th>Open interest</th>
          </tr>
        </thead>
        <tbody>
          ${rows.map((r) => `
            <tr>
              <td>${formatNumber(r.strike, 4)}</td>
              <td>${formatNumber(r.moneyness, 4)}</td>
              <td>${formatNumber(r.bid, 4)}</td>
              <td>${formatNumber(r.ask, 4)}</td>
              <td>${formatNumber(r.midpoint, 4)}</td>
              <td>${r.yahoo_iv !== null && r.yahoo_iv !== undefined ? formatPercent(r.yahoo_iv, 2) : "—"}</td>
              <td>${r.model_iv_mid !== null && r.model_iv_mid !== undefined ? formatPercent(r.model_iv_mid, 2) : "—"}</td>
              <td>${r.model_iv_last !== null && r.model_iv_last !== undefined ? formatPercent(r.model_iv_last, 2) : "—"}</td>
              <td>${formatNumber(r.volume, 0)}</td>
              <td>${formatNumber(r.open_interest, 0)}</td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  `;
}

async function loadImpliedVolatility(event) {
  event.preventDefault();
  const output = $("iv-output");
  const payload = formToObject(event.currentTarget);
  const symbol = payload.symbol || state.market?.symbol;
  const expiry = payload.expiry;
  const side = payload.side || "call";
  const rate = payload.rate || 0.02;

  if (!symbol) {
    output.innerHTML = errorBox("Sélectionnez d’abord un sous-jacent dans la section supérieure.");
    return;
  }
  if (!expiry) {
    output.innerHTML = errorBox("Aucune échéance n’est sélectionnée.");
    return;
  }

  output.innerHTML = noticeBox("Extraction de la smile et recalcul des volatilités implicites...");
  try {
    const data = await apiJson(
      `/api/implied-volatility/${encodeURIComponent(symbol)}/${encodeURIComponent(expiry)}?side=${encodeURIComponent(side)}&rate=${encodeURIComponent(rate)}`
    );
    const summary = data.summary;
    const rows = data.rows || [];

    const chartPoints = rows
      .map((r) => ({
        x: Number(r.strike),
        y: r.model_iv_mid !== null && r.model_iv_mid !== undefined ? Number(r.model_iv_mid) : Number(r.yahoo_iv),
      }))
      .filter((p) => Number.isFinite(p.x) && Number.isFinite(p.y));

    const modelCount = rows.filter((r) => r.model_iv_mid !== null && r.model_iv_mid !== undefined).length;
    const yahooOnlyCount = rows.filter(
      (r) => (r.model_iv_mid === null || r.model_iv_mid === undefined) && r.yahoo_iv !== null && r.yahoo_iv !== undefined
    ).length;

    output.innerHTML = `
      <div class="result-card">
        <h3>Smile de volatilité implicite — ${escapeHtml(data.symbol)} — ${escapeHtml(summary.expiry)}</h3>
        <p>
          La courbe privilégie l’IV recalculée sur le midpoint bid/ask ; lorsqu’elle n’est pas admissible,
          l’IV Yahoo Finance est utilisée pour conserver une lecture de la structure.
        </p>
        ${resultMetrics([
          ["Spot", formatNumber(summary.spot, 4)],
          ["Maturité", `${formatNumber(summary.maturity_years, 4)} an(s)`],
          ["Strike ATM retenu", formatNumber(summary.atm_strike, 4)],
          ["IV ATM", summary.atm_iv !== null && summary.atm_iv !== undefined ? formatPercent(summary.atm_iv, 2) : "—"],
          ["IV minimale", summary.min_iv !== null && summary.min_iv !== undefined ? formatPercent(summary.min_iv, 2) : "—"],
          ["IV maximale", summary.max_iv !== null && summary.max_iv !== undefined ? formatPercent(summary.max_iv, 2) : "—"],
          ["Points recalculés", formatNumber(modelCount, 0)],
          ["Points Yahoo de repli", formatNumber(yahooOnlyCount, 0)],
        ])}
        ${lineChartSvg(chartPoints, { xLabel: "Strike", yLabel: "Volatilité implicite" })}
        ${ivTable(rows)}
      </div>
    `;
  } catch (error) {
    output.innerHTML = errorBox(error.message);
  }
}

function updateExoticFields() {
  const type = $("exotic-type").value;
  document.querySelectorAll(".asian-field").forEach((el) => el.classList.toggle("hidden", type !== "asian"));
  document.querySelectorAll(".barrier-field").forEach((el) => el.classList.toggle("hidden", type !== "barrier"));
  document.querySelectorAll(".gap-field").forEach((el) => el.classList.toggle("hidden", type !== "gap"));
  document.querySelectorAll(".mc-field").forEach((el) => el.classList.toggle("hidden", type === "gap"));
}

async function priceExotic(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const output = $("exotic-output");
  output.innerHTML = noticeBox("Calcul en cours...");
  try {
    const payload = formToObject(form);
    const data = await apiJson("/api/price/exotic", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const r = data.result;
    const metrics = [["Prix", formatNumber(r.price, 6)]];
    if (r.std_error !== undefined) {
      metrics.push(["Erreur std.", formatNumber(r.std_error, 6)]);
      metrics.push(["IC 95 %", `${formatNumber(r.ci95_low, 6)} – ${formatNumber(r.ci95_high, 6)}`]);
    }
    output.innerHTML = `
      <div class="result-card">
        <h3>Résultat — ${escapeHtml(r.exotic_type)}</h3>
        ${resultMetrics(metrics)}
        ${jsonBlock(r)}
      </div>
    `;
  } catch (error) {
    output.innerHTML = errorBox(error.message);
  }
}

function addBatchRow(prefill = {}) {
  const tbody = $("batch-table").querySelector("tbody");
  const row = document.createElement("tr");
  const spot = prefill.spot ?? state.market?.spot ?? 100;
  const vol = prefill.volatility ?? state.market?.realized_vol_1y ?? 0.25;
  const div = prefill.dividend_yield ?? state.market?.dividend_yield ?? 0.0;
  row.innerHTML = `
    <td><select name="model"><option value="bsm">BSM</option><option value="binomial">CRR</option><option value="monte_carlo">MC</option></select></td>
    <td><select name="option_type"><option value="call">Call</option><option value="put">Put</option></select></td>
    <td><input name="spot" type="number" step="any" value="${spot}"></td>
    <td><input name="strike" type="number" step="any" value="${prefill.strike ?? Math.round(Number(spot) || 100)}"></td>
    <td><input name="maturity" type="number" step="any" value="${prefill.maturity ?? 1}"></td>
    <td><input name="rate" type="number" step="any" value="${prefill.rate ?? 0.02}"></td>
    <td><input name="volatility" type="number" step="any" value="${Number(vol).toFixed ? Number(vol).toFixed(4) : vol}"></td>
    <td><input name="dividend_yield" type="number" step="any" value="${Number(div).toFixed ? Number(div).toFixed(4) : div}"></td>
    <td><input name="steps" type="number" step="1" value="400"></td>
    <td><input name="n_paths" type="number" step="1000" value="100000"></td>
    <td><input name="american" type="checkbox"></td>
    <td><button class="remove-row" type="button">Supprimer</button></td>
  `;
  tbody.appendChild(row);
}

function batchRowsPayload() {
  return [...$("batch-table").querySelectorAll("tbody tr")].map((row) => {
    const payload = {};
    row.querySelectorAll("input, select").forEach((field) => {
      payload[field.name] = field.type === "checkbox" ? field.checked : field.value;
    });
    return payload;
  });
}

async function priceBatch() {
  const output = $("batch-output");
  output.innerHTML = noticeBox("Pricing du lot en cours...");
  try {
    const data = await apiJson("/api/price/batch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rows: batchRowsPayload() }),
    });
    const rows = data.results || [];
    const errors = data.errors || [];
    const cards = rows
      .map((r) => `
        <div class="result-card">
          <h3>Ligne ${r.row} — ${escapeHtml(r.model)}</h3>
          ${resultMetrics([
            ["Prix", formatNumber(r.price, 6)],
            ["Erreur std.", r.std_error !== undefined ? formatNumber(r.std_error, 6) : "—"],
            ["Delta", r.greeks ? formatNumber(r.greeks.delta, 6) : "—"],
            ["Gamma", r.greeks ? formatNumber(r.greeks.gamma, 6) : "—"],
          ])}
        </div>
      `)
      .join("");
    const errorCards = errors.map((e) => errorBox(`Ligne ${e.row} : ${e.error}`)).join("");
    output.innerHTML = cards + errorCards || noticeBox("Aucun résultat.");
  } catch (error) {
    output.innerHTML = errorBox(error.message);
  }
}

function updateStructuredFields() {
  const type = $("structured-type").value;
  document.querySelectorAll(".capital-field").forEach((el) => el.classList.toggle("hidden", type !== "capital_protected"));
  document.querySelectorAll(".reverse-field").forEach((el) => el.classList.toggle("hidden", type !== "reverse_convertible"));
  document.querySelectorAll(".autocall-field").forEach((el) => el.classList.toggle("hidden", type !== "autocallable"));
}

async function priceStructured(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const output = $("structured-output");
  output.innerHTML = noticeBox("Calcul Monte Carlo en cours...");
  try {
    const payload = formToObject(form);
    const data = await apiJson("/api/price/structured", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const r = data.result;
    const metrics = [
      ["Prix", formatNumber(r.price, 6)],
      ["Erreur std.", formatNumber(r.std_error, 6)],
      ["IC 95 %", `${formatNumber(r.ci95_low, 6)} – ${formatNumber(r.ci95_high, 6)}`],
    ];
    if (r.autocall_probability !== undefined) {
      metrics.push(["P(autocall)", formatPercent(r.autocall_probability, 2)]);
      metrics.push(["P(perte en capital)", formatPercent(r.capital_loss_probability, 2)]);
    }
    output.innerHTML = `
      <div class="result-card">
        <h3>Résultat — ${escapeHtml(data.product_type)}</h3>
        ${resultMetrics(metrics)}
        ${jsonBlock(r)}
      </div>
    `;
  } catch (error) {
    output.innerHTML = errorBox(error.message);
  }
}

document.addEventListener("click", (event) => {
  if (event.target.matches(".select-symbol")) {
    loadMarket(event.target.dataset.symbol);
  }
  if (event.target.matches(".remove-row")) {
    event.target.closest("tr").remove();
  }
});

$("search-btn").addEventListener("click", searchUnderlying);
$("search-query").addEventListener("keydown", (event) => {
  if (event.key === "Enter") searchUnderlying();
});
$("refresh-market-btn").addEventListener("click", () => {
  if (state.market) loadMarket(state.market.symbol);
});
$("load-chain-btn").addEventListener("click", loadOptionChain);

document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => activateTab(tab.dataset.tab));
});

$("vanilla-form").addEventListener("submit", priceVanilla);
$("iv-form").addEventListener("submit", loadImpliedVolatility);
$("exotic-form").addEventListener("submit", priceExotic);
$("exotic-type").addEventListener("change", updateExoticFields);

$("add-batch-row").addEventListener("click", () => addBatchRow());
$("batch-price-btn").addEventListener("click", priceBatch);

$("structured-form").addEventListener("submit", priceStructured);
$("structured-type").addEventListener("change", updateStructuredFields);

updateExoticFields();
updateStructuredFields();
addBatchRow();
addBatchRow({ option_type: "put", strike: 95 });
