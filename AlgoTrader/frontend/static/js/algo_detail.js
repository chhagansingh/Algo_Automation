/**
 * AlgoTrader — Per-Algo Detail Page JS
 * Handles signal cards, open positions, closed trades, calendar, paper trading controls.
 */

let algoCalendar   = null;
let liveInterval   = null;
let currentAlgoId  = null;
let currentPage    = 1;
const PAGE_SIZE    = 20;

document.addEventListener('DOMContentLoaded', () => {
  // Extract algo_id from URL: /algo/algo1 → algo1
  const pathParts = window.location.pathname.split('/');
  currentAlgoId = pathParts[pathParts.length - 1] || 'algo3';

  loadAlgoSummary(currentAlgoId);
  loadTrades(currentAlgoId, 1);
  loadLivePrice();
  liveInterval = setInterval(() => {
    loadLivePrice();
    loadAlgoSummary(currentAlgoId);
  }, 30000);

  // Per-algo calendar (sidebar)
  algoCalendar = new AlgoCalendar('algo_calendar', currentAlgoId, onAlgoCalendarClick);

  // Backtest panel (single algo pre-selected)
  initBacktestPanel('algo_backtest', [currentAlgoId]);
});

// ── Live price ────────────────────────────────────────────────────────────────
async function loadLivePrice() {
  try {
    const res  = await fetch('/api/nifty/live');
    const data = await res.json();
    setElText('hdr_nifty', data.nifty ? data.nifty.toLocaleString('en-IN') : '--');
    setElText('hdr_vix', data.vix ? 'VIX ' + data.vix : '');
    setElText('hdr_time', 'Updated ' + (data.time || ''));
  } catch(e) {}
}

// ── Load algo summary (signals, open positions, P&L) ─────────────────────────
async function loadAlgoSummary(algoId) {
  try {
    const res  = await fetch(`/api/algo/${algoId}/summary`);
    const data = await res.json();
    renderPnlSummary(data.pnl_summary || {});
    renderPortfolioExposure(data);
    renderOpenPositions(data.open_positions || []);
    renderSignalCards(data.live_signal || {}, data.algo_meta || {});
    renderPaperControls(algoId, data.paper_running);
  } catch(e) {
    console.error('Summary load error:', e);
  }
}

// ── P&L Summary (sidebar) ─────────────────────────────────────────────────────
function renderPnlSummary(pnl) {
  const el = document.getElementById('pnl_summary');
  if (!el) return;

  const periods = [
    { key: 'one_year',    label: '1 YEAR' },
    { key: 'six_month',   label: '6 MONTHS' },
    { key: 'three_month', label: '3 MONTHS' },
    { key: 'one_month',   label: '1 MONTH' },
  ];

  const cards = periods.map(p => {
    const v    = pnl[p.key] || 0;
    const cls  = v >= 0 ? 'text-green' : 'text-red';
    const sign = v >= 0 ? '+' : '';
    // Compute rough % (use algo initial capital from meta if available)
    return `
      <div class="pnl-card">
        <div class="period">${p.label}</div>
        <div class="pnl-pct ${cls}">${sign}${fmtPct(0)}</div>
        <div class="pnl-abs ${cls}">${fmtPnl(v)}</div>
      </div>`;
  }).join('');

  const today = pnl.today || 0;
  const todayCls = today >= 0 ? 'text-green' : 'text-red';
  const todaySign = today >= 0 ? '+' : '';

  el.innerHTML = `
    <div class="pnl-summary-grid">
      ${cards}
      <div class="pnl-card today">
        <div class="period">TODAY</div>
        <div class="pnl-pct ${todayCls}">${todaySign}${fmtPnl(today)}</div>
        <div class="pnl-abs text-muted">${today === 0 ? 'No trades yet' : ''}</div>
      </div>
    </div>`;
}

// ── Portfolio Exposure (sidebar) ───────────────────────────────────────────────
function renderPortfolioExposure(data) {
  const el = document.getElementById('portfolio_exposure');
  if (!el) return;
  const positions = (data.open_positions || []).length;
  const todayPnl  = data.pnl_summary?.today || 0;
  const running   = data.paper_running;
  el.innerHTML = `
    <div class="exposure-grid">
      <div class="exposure-item">
        <div class="e-label">Daily P&L</div>
        <div class="e-value ${pnlClass(todayPnl)}">${fmtPnl(todayPnl)}</div>
      </div>
      <div class="exposure-item">
        <div class="e-label">Positions</div>
        <div class="e-value">${positions}</div>
      </div>
      <div class="exposure-item">
        <div class="e-label">At Risk</div>
        <div class="e-value text-orange">${positions > 0 ? '~2%' : '0%'}</div>
      </div>
    </div>
    <div class="e-label" style="margin-top:8px">STATUS</div>
    <div class="status-bar ${running ? '' : 'halted'}" style="width:100%"></div>
    <div style="margin-top:4px;font-size:11px;color:${running ? 'var(--green-light)' : 'var(--text-dim)'}">
      ${running ? 'ACTIVE — Paper Trading' : 'INACTIVE'}
    </div>`;
}

// ── Signal Cards ──────────────────────────────────────────────────────────────
function renderSignalCards(liveSignal, meta) {
  const el = document.getElementById('signal_cards');
  if (!el) return;
  const cards  = liveSignal.signal_cards || {};
  const signal = liveSignal.signal || 'NO_TRADE';

  if (Object.keys(cards).length === 0) {
    el.innerHTML = `<div class="text-muted" style="font-size:12px;padding:8px">No live signal data</div>`;
    return;
  }

  const cardNames = Object.keys(cards);
  const cardHtml  = cardNames.map((name, i) => {
    const val    = cards[name];
    const colors = ['', 'green', 'blue', 'red', 'purple', '', 'green', 'red'];
    const cls    = colors[i % colors.length];
    return `
      <div class="signal-card ${cls}">
        <div class="sc-label">${name.replace(/_/g,' ')}</div>
        <div class="sc-value">${val}</div>
      </div>`;
  }).join('');

  const signalColor = signal === 'NO_TRADE' ? 'text-muted'
    : signal.includes('BUY') || signal.includes('CONDOR') ? 'text-green' : 'text-orange';

  el.innerHTML = `
    <div class="signal-grid">${cardHtml}</div>
    <div class="lot-row">
      <span class="lot-badge">Signal: ${signal.replace(/_/g,' ')}</span>
      ${liveSignal.option_type ? `<span class="lot-badge">${liveSignal.option_type}</span>` : ''}
      ${liveSignal.strike ? `<span class="lot-badge">Strike: ${liveSignal.strike}</span>` : ''}
    </div>`;
}

// ── Open Positions ─────────────────────────────────────────────────────────────
function renderOpenPositions(positions) {
  const el = document.getElementById('open_positions');
  if (!el) return;

  if (positions.length === 0) {
    el.innerHTML = `
      <div class="empty-state" style="padding:16px">
        <div class="empty-icon">&#9726;</div>
        <div>No open position — waiting for entry signal</div>
      </div>`;
    return;
  }

  const rows = positions.map(p => {
    const unr  = p.unrealized_pnl || 0;
    const optBadge = p.option_type === 'CE' ? 'badge-ce'
      : p.option_type === 'PE' ? 'badge-pe' : 'badge-both';
    return `
      <tr>
        <td>${p.symbol || 'NIFTY'}</td>
        <td>${p.strike || '—'}</td>
        <td><span class="${optBadge}">${p.option_type || '—'}</span></td>
        <td>${p.open_time ? p.open_time.slice(11,16) : '—'}</td>
        <td>${p.entry_price ? '₹' + Number(p.entry_price).toFixed(1) : '—'}</td>
        <td>${p.current_ltp ? '₹' + Number(p.current_ltp).toFixed(1) : '—'}</td>
        <td><span class="text-blue" style="font-size:11px">${p.signal_name || '—'}</span></td>
        <td class="${pnlClass(unr)}">${fmtPnl(unr)}</td>
      </tr>`;
  }).join('');

  el.innerHTML = `
    <table class="positions-table">
      <thead><tr>
        <th>Symbol</th><th>Strike</th><th>Type</th><th>Entry Time</th>
        <th>Entry</th><th>LTP</th><th>Signal</th><th>Unr. P&L</th>
      </tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
}

// ── Closed Trades ─────────────────────────────────────────────────────────────
async function loadTrades(algoId, page) {
  currentPage = page;
  const el = document.getElementById('closed_trades');
  if (!el) return;
  el.innerHTML = `<div style="padding:16px;text-align:center"><div class="spinner"></div></div>`;

  try {
    const res  = await fetch(`/api/algo/${algoId}/trades?page=${page}&page_size=${PAGE_SIZE}`);
    const data = await res.json();
    renderClosedTrades(data);
  } catch(e) {
    el.innerHTML = `<div style="color:var(--red-light);padding:12px">Failed to load trades</div>`;
  }
}

function renderClosedTrades(data) {
  const el     = document.getElementById('closed_trades');
  const pagEl  = document.getElementById('trades_pagination');
  if (!el) return;

  const trades = data.trades || [];
  const total  = data.total  || 0;
  const pages  = data.pages  || 1;

  if (trades.length === 0) {
    el.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">📭</div>
        <div>No trades yet</div>
        <div class="text-dim" style="font-size:10px">Run a backtest to populate trade history</div>
      </div>`;
    if (pagEl) pagEl.innerHTML = '';
    return;
  }

  // Day header + trade cards
  let html = '';
  let lastDate = '';
  for (const t of trades) {
    const tDate = (t.date || '').slice(0, 10);
    if (tDate !== lastDate) {
      if (lastDate !== '') html += '</div>';
      html += `<div class="day-pnl-header" style="margin-top:${lastDate?'14px':'0'}">
        <span style="font-size:12px;font-weight:600">${_fmtDateLabel(tDate)}</span>
      </div><div>`;
      lastDate = tDate;
    }
    html += renderSingleTradeCard(t);
  }
  if (lastDate) html += '</div>';
  el.innerHTML = html;

  // Pagination
  if (pagEl) {
    if (pages <= 1) { pagEl.innerHTML = ''; return; }
    const prev = currentPage > 1 ? `<button class="btn btn-ghost" onclick="loadTrades('${data.algo_id||currentAlgoId}', ${currentPage-1})">← Prev</button>` : '';
    const next = currentPage < pages ? `<button class="btn btn-ghost" onclick="loadTrades('${data.algo_id||currentAlgoId}', ${currentPage+1})">Next →</button>` : '';
    pagEl.innerHTML = `<div style="display:flex;gap:8px;align-items:center;padding:8px 0;font-size:12px;color:var(--text-muted)">
      ${prev} Page ${currentPage} / ${pages} ${next}
    </div>`;
  }
}

function renderSingleTradeCard(t) {
  const pnl    = parseFloat(t.pnl) || 0;
  const pnlPct = parseFloat(t.pnl_pct) || 0;
  const exitReason = (t.exit_reason || '').toLowerCase();
  let exitCls = 'eod';
  if (exitReason.includes('target')) exitCls = 'target';
  else if (exitReason.includes('tsl') || exitReason.includes('trailing')) exitCls = 'tsl';
  else if (exitReason.includes('sl') || exitReason.includes('stop')) exitCls = 'sl';

  const optBadge = t.option_type === 'CE' ? 'badge-ce'
    : t.option_type === 'PE' ? 'badge-pe' : 'badge-both';
  const subName = (t.sub_strategy || t.signal_name || 'TRADE').replace(/_/g,' ');
  const signalTag = (t.signal_name || '').replace(/_/g,' ');

  return `
    <div class="trade-card">
      <div class="trade-card-header">
        <div class="trade-card-left">
          <div class="trade-name">${subName}</div>
          <div class="trade-meta">
            <span class="signal-tag">${signalTag}</span>
            <span class="expiry">${t.entry_time ? t.entry_time.slice(0,16).replace('T',' ') : t.date || ''}</span>
          </div>
        </div>
        <div class="trade-card-right">
          <div class="pnl-per-lot ${pnlClass(pnl)}">${fmtPnl(pnl)} / Lot</div>
          <div class="pnl-pct ${pnlClass(pnl)}">${pnl >= 0 ? '▲' : '▼'} ${Math.abs(pnlPct).toFixed(2)}%</div>
        </div>
      </div>

      <div class="trade-legs">
        <table>
          <thead><tr>
            <th>TRADE NAME</th><th>ENTRY</th><th>EXIT</th>
          </tr></thead>
          <tbody>
            <tr>
              <td class="leg-symbol">
                <span class="${optBadge}">${t.option_type || 'N/A'}</span>
                NIFTY ${t.strike || ''}
              </td>
              <td>${t.entry_price ? '₹' + Number(t.entry_price).toFixed(2) : '—'}</td>
              <td>${t.exit_price  ? '₹' + Number(t.exit_price).toFixed(2)  : '—'}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="trade-card-footer">
        <span>Closed: ${t.exit_time ? t.exit_time.slice(0,16).replace('T',' ') : '—'}</span>
        <span class="exit-reason ${exitCls}">${(t.exit_reason||'—').replace(/_/g,' ')}</span>
      </div>
    </div>`;
}

// ── Paper trading controls ─────────────────────────────────────────────────────
function renderPaperControls(algoId, running) {
  const el = document.getElementById('paper_controls');
  if (!el) return;
  if (running) {
    el.innerHTML = `<button class="btn btn-halt" onclick="stopPaper('${algoId}')">&#x23F9; HALT</button>`;
  } else {
    el.innerHTML = `<button class="btn btn-start" onclick="startPaper('${algoId}')">&#9654; START PAPER</button>`;
  }
}

async function startPaper(algoId) {
  await fetch(`/api/paper/${algoId}/start`, { method: 'POST' });
  setTimeout(() => loadAlgoSummary(algoId), 1000);
}
async function stopPaper(algoId) {
  await fetch(`/api/paper/${algoId}/stop`, { method: 'POST' });
  setTimeout(() => loadAlgoSummary(algoId), 500);
}

// ── Calendar date click ───────────────────────────────────────────────────────
async function onAlgoCalendarClick(dateStr) {
  openAlgoDateDrawer(dateStr, currentAlgoId);
}

async function openAlgoDateDrawer(dateStr, algoId) {
  const drawer  = document.getElementById('date_drawer');
  const overlay = document.getElementById('date_drawer_overlay');
  const title   = document.getElementById('drawer_title');
  const body    = document.getElementById('drawer_body');
  if (!drawer) return;

  const d = new Date(dateStr + 'T00:00:00');
  const dayName = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'][d.getDay()];
  const monthNames = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  if (title) title.textContent = `${dayName}, ${d.getDate()} ${monthNames[d.getMonth()]} ${d.getFullYear()}`;

  if (body) body.innerHTML = `<div style="padding:20px;text-align:center"><div class="spinner"></div></div>`;
  drawer.classList.add('open');
  if (overlay) overlay.classList.add('open');

  try {
    const res  = await fetch(`/api/trades/date/${algoId}/${dateStr}`);
    const data = await res.json();
    if (body) body.innerHTML = renderDrawerTradesAlgo(data);
  } catch(e) {
    if (body) body.innerHTML = `<div style="color:var(--red-light);padding:12px">Failed</div>`;
  }
}

function renderDrawerTradesAlgo(data) {
  const trades = data.trades || [];
  const dayPnl = data.day_pnl || 0;
  if (trades.length === 0) {
    return `<div class="empty-state"><div class="empty-icon">📭</div><div>No trades on this day</div></div>`;
  }
  const header = `<div class="day-pnl-header">
    <span>Day P&L</span>
    <span class="day-pnl-value ${pnlClass(dayPnl)}">${fmtPnl(dayPnl)}</span>
  </div>`;
  return header + trades.map(t => renderSingleTradeCard(t)).join('');
}

function closeDateDrawer() {
  document.getElementById('date_drawer')?.classList.remove('open');
  document.getElementById('date_drawer_overlay')?.classList.remove('open');
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function setElText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

function _fmtDateLabel(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr + 'T00:00:00');
  const days   = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
  const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  return `${days[d.getDay()]}, ${d.getDate()} ${months[d.getMonth()]} ${d.getFullYear()}`;
}
