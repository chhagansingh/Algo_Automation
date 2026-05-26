/**
 * AlgoTrader — Backtest Panel Logic
 * Handles date picker, algo selection, API call, results rendering.
 */

let _backtestChart = null;

async function runBacktest(algoIds, startDate, endDate, resultContainerId, interval = "1d") {
  const container = document.getElementById(resultContainerId);
  if (!container) return;

  container.innerHTML = `<div style="display:flex;align-items:center;gap:10px;padding:16px;color:var(--text-muted)">
    <div class="spinner"></div> Running backtest (${interval})...
  </div>`;

  try {
    const res = await fetch('/api/backtest', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ algo_ids: algoIds, start_date: startDate, end_date: endDate, interval }),
    });
    if (!res.ok) {
      const err = await res.json();
      container.innerHTML = `<div style="color:var(--red-light);padding:12px">Error: ${err.detail || 'Unknown error'}</div>`;
      return;
    }
    const data = await res.json();
    renderBacktestResults(container, data, algoIds);
  } catch (e) {
    container.innerHTML = `<div style="color:var(--red-light);padding:12px">Request failed: ${e.message}</div>`;
  }
}

function renderBacktestResults(container, data, algoIds) {
  const mode   = data.mode;
  const result = data.result;

  if (mode === 'single') {
    renderSingleResult(container, result);
  } else {
    renderCompareResult(container, result, algoIds);
  }
}

// ── Single algo result ─────────────────────────────────────────────────────────
function renderSingleResult(container, result) {
  const m    = result.metrics || {};
  const name = result.algo_name || result.algo_id;
  const monthly = result.monthly || {};
  const curve   = result.equity_curve || [];

  const pnlCls = (m.final_pnl || 0) >= 0 ? 'text-green' : 'text-red';

  container.innerHTML = `
    <div style="padding:4px 0 12px">
      <div style="display:flex;gap:8px;align-items:center;margin-bottom:12px">
        <span style="font-weight:600;font-size:14px">${name}</span>
        <span style="font-size:11px;color:var(--text-muted)">${result.start_date} → ${result.end_date}</span>
      </div>

      <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:14px">
        ${_metricBox('Final P&L', fmtPnl(m.final_pnl), pnlCls)}
        ${_metricBox('Win Rate', m.win_rate + '%', m.win_rate >= 50 ? 'text-green' : 'text-red')}
        ${_metricBox('Sharpe', m.sharpe, m.sharpe >= 1 ? 'text-green' : 'text-red')}
        ${_metricBox('Max DD', fmtPnl(-(m.max_drawdown||0)), 'text-red')}
        ${_metricBox('Trades', m.total_trades, 'text-muted')}
        ${_metricBox('Wins', m.wins, 'text-green')}
        ${_metricBox('Losses', m.losses, 'text-red')}
        ${_metricBox('ROC', fmtPct(m.roc_pct), pnlCls)}
      </div>

      <div class="card-title">EQUITY CURVE</div>
      <div class="chart-container" style="height:160px">
        <canvas id="bt_equity_canvas"></canvas>
      </div>

      <div class="card-title" style="margin-top:14px">MONTHLY BREAKDOWN</div>
      ${_monthlyTable(monthly, [result.algo_id], { [result.algo_id]: monthly }, { [result.algo_id]: name })}
    </div>
  `;

  // Render chart
  if (curve.length > 0) {
    setTimeout(() => {
      renderEquityCurve('bt_equity_canvas',
        { [result.algo_id]: curve },
        { [result.algo_id]: name }
      );
    }, 50);
  }
}

// ── Compare result (multiple algos) ────────────────────────────────────────────
function renderCompareResult(container, result, algoIds) {
  const algoNames = {};
  algoIds.forEach(id => {
    algoNames[id] = result.results?.[id]?.algo_name || id;
  });

  const compareTable  = result.compare_table  || [];
  const monthlyCompare = result.monthly_compare || [];
  const equityCurves  = result.equity_curves   || {};

  // Format cells
  const pnlMetrics = new Set(['Final P&L (₹)', 'Avg Win (₹)', 'Max Drawdown (₹)', 'Avg Loss (₹)']);
  const pctMetrics = new Set(['Win Rate (%)', 'ROC (%)']);

  container.innerHTML = `
    <div style="padding:4px 0 12px">
      <div style="font-size:11px;color:var(--text-muted);margin-bottom:12px">
        Compare: ${result.start_date} → ${result.end_date}
      </div>

      <div class="card-title">METRICS COMPARISON</div>
      <div style="overflow-x:auto">
        <table class="compare-table">
          <thead>
            <tr>
              <th>Metric</th>
              ${algoIds.map(id => `<th>${algoNames[id]}</th>`).join('')}
            </tr>
          </thead>
          <tbody>
            ${compareTable.map(row => _compareRow(row, algoIds, pnlMetrics, pctMetrics)).join('')}
          </tbody>
        </table>
      </div>

      <div class="card-title" style="margin-top:16px">EQUITY CURVES</div>
      <div class="chart-container" style="height:180px">
        <canvas id="bt_compare_canvas"></canvas>
      </div>

      <div class="card-title" style="margin-top:16px">MONTHLY BREAKDOWN</div>
      <div style="overflow-x:auto">
        ${_monthlyTable(null, algoIds, _buildPerAlgoMonthly(result.results, algoIds), algoNames)}
      </div>
    </div>
  `;

  // Render chart
  if (Object.keys(equityCurves).length > 0) {
    setTimeout(() => {
      renderEquityCurve('bt_compare_canvas', equityCurves, algoNames);
    }, 50);
  }
}

function _compareRow(row, algoIds, pnlMetrics, pctMetrics) {
  const metric = row.metric;
  const values = algoIds.map(id => row[id] ?? 0);

  // Highlight best (highest) for most metrics, lowest for drawdown/losses/consec loss
  const isLowerBetter = metric.includes('Drawdown') || metric === 'Losses' || metric === 'Max Consec. Losses';
  const best = isLowerBetter
    ? Math.min(...values.filter(v => v !== 0))
    : Math.max(...values);

  const cells = algoIds.map((id, i) => {
    const v    = row[id] ?? 0;
    let display = v;
    if (pnlMetrics.has(metric)) display = fmtPnl(v);
    else if (pctMetrics.has(metric)) display = fmtPct(v);
    else if (metric === 'Sharpe Ratio') display = Number(v).toFixed(2);

    const isBest = v === best && v !== 0;
    const cls    = isBest ? 'best' : (metric.includes('P&L') || metric === 'ROC (%)' ? (v >= 0 ? 'text-green' : 'text-red') : '');
    return `<td class="${cls}">${display}</td>`;
  });

  return `<tr><td>${metric}</td>${cells.join('')}</tr>`;
}

function _buildPerAlgoMonthly(results, algoIds) {
  const out = {};
  algoIds.forEach(id => {
    out[id] = results?.[id]?.monthly || {};
  });
  return out;
}

function _monthlyTable(singleMonthly, algoIds, perAlgoMonthly, algoNames) {
  // Collect all months
  const allMonths = new Set();
  algoIds.forEach(id => {
    Object.keys(perAlgoMonthly[id] || {}).forEach(m => allMonths.add(m));
  });
  if (allMonths.size === 0) return '<div class="text-muted" style="padding:8px;font-size:12px">No monthly data</div>';
  const months = Array.from(allMonths).sort();

  const headerCells = algoIds.length > 1
    ? algoIds.map(id => `<th>${algoNames[id] || id}</th>`).join('')
    : '';

  const rows = months.map(m => {
    const [y, mo] = m.split('-');
    const monthLabel = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][parseInt(mo)-1] + ' ' + y;
    const cells = algoIds.map(id => {
      const v = perAlgoMonthly[id]?.[m] ?? 0;
      const cls = v > 0 ? 'text-green' : v < 0 ? 'text-red' : 'text-dim';
      return `<td class="${cls}">${fmtPnl(v)}</td>`;
    }).join('');
    return `<tr><td>${monthLabel}</td>${cells}</tr>`;
  }).join('');

  return `
    <table class="monthly-table">
      <thead><tr><th>Month</th>${headerCells}</tr></thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

function _metricBox(label, value, cls) {
  return `
    <div class="signal-card">
      <div class="sc-label">${label}</div>
      <div class="sc-value ${cls}">${value}</div>
    </div>
  `;
}

// ── Backtest Panel init (called from pages) ────────────────────────────────────
function initBacktestPanel(panelId, defaultAlgoIds) {
  const panel = document.getElementById(panelId);
  if (!panel) return;

  const today   = new Date().toISOString().split('T')[0];
  const oneYrAgo = new Date(Date.now() - 365*24*60*60*1000).toISOString().split('T')[0];

  panel.innerHTML = `
    <div class="backtest-panel">
      <div class="bp-title">Backtest Configuration</div>
      <div class="backtest-form">
        <div class="form-group">
          <label>From</label>
          <input type="date" id="${panelId}_start" value="${oneYrAgo}" max="${today}">
        </div>
        <div class="form-group">
          <label>To</label>
          <input type="date" id="${panelId}_end" value="${today}" max="${today}">
        </div>
        <div class="form-group">
          <label>Interval</label>
          <select id="${panelId}_interval" style="padding:6px 10px;border-radius:6px;background:#1e293b;border:1px solid #334155;color:var(--text);font-size:13px">
            <option value="1d">Daily (1d)</option>
            <option value="1h">1 Hour</option>
            <option value="30m">30 Minute</option>
            <option value="15m">15 Minute</option>
            <option value="5m">5 Minute</option>
            <option value="1m">1 Minute</option>
          </select>
          <div style="font-size:10px;color:var(--text-dim);margin-top:4px">
            Intraday: max 60 days (5m/15m/30m) / 730 days (1h)
          </div>
        </div>
        <div class="form-group">
          <label>Algos</label>
          <div class="algo-checkboxes">
            <label class="algo-checkbox-label">
              <input type="checkbox" id="${panelId}_algo1" value="algo1" ${defaultAlgoIds.includes('algo1') ? 'checked' : ''}> Algo1
            </label>
            <label class="algo-checkbox-label">
              <input type="checkbox" id="${panelId}_algo2" value="algo2" ${defaultAlgoIds.includes('algo2') ? 'checked' : ''}> Algo2
            </label>
            <label class="algo-checkbox-label">
              <input type="checkbox" id="${panelId}_algo3" value="algo3" ${defaultAlgoIds.includes('algo3') ? 'checked' : ''}> Algo3
            </label>
          </div>
        </div>
        <button class="btn btn-blue" onclick="triggerBacktest('${panelId}')">
          &#9654; Run Backtest
        </button>
      </div>
      <div id="${panelId}_results" style="margin-top:12px"></div>
    </div>
  `;
}

function triggerBacktest(panelId) {
  const start  = document.getElementById(`${panelId}_start`)?.value;
  const end    = document.getElementById(`${panelId}_end`)?.value;
  const interval = document.getElementById(`${panelId}_interval`)?.value || "1d";
  const checks = ['algo1','algo2','algo3'].filter(id =>
    document.getElementById(`${panelId}_${id}`)?.checked
  );
  if (!start || !end) return alert('Please select date range');
  if (checks.length === 0) return alert('Please select at least one algo');
  runBacktest(checks, start, end, `${panelId}_results`, interval);
}
