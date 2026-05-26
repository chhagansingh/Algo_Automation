/**
 * AlgoTrader — Master Dashboard JS
 * Loads all algo summaries, renders cards, calendar, date drawer.
 */

const ALGO_IDS    = ['algo1','algo2','algo3','algo4','algo5','algo6','algo7','algo8','algo9','algo10','algo11','algo12','algo13','algo14','algo15','algo16','algo17'];
const ALGO_ICONS  = {
  algo1: 'RS', algo2: 'NT', algo3: 'NB', algo4: 'FL', algo5: 'VX',
  algo6: 'ST', algo7: 'DT', algo8: 'CS', algo9: 'BS', algo10: 'AO', algo11: 'GS', algo12: 'DR',
  algo13: 'SR', algo14: 'ML', algo15: 'AS', algo16: 'S4', algo17: 'S3'
};
const ALGO_COLORS = {
  algo1: '#388bfd', algo2: '#e3b341', algo3: '#3fb950', algo4: '#a371f7',
  algo5: '#ff7b72', algo6: '#79c0ff', algo7: '#56d364', algo8: '#ffa657',
  algo9: '#d2a8ff', algo10: '#7ee787', algo11: '#f0883e', algo12: '#8b949e',
  algo13: '#2ea043', algo14: '#a47ae3', algo15: '#e85d75',
  algo16: '#00bcd4', algo17: '#ff9800'
};
const ALGO_TAGS   = {
  algo1:  { label: 'READY · 58%WR',         color: 'var(--green-light)', bg: 'rgba(46,160,67,0.12)' },
  algo2:  { label: 'AUDIT · 97%WR ★',      color: 'var(--green-light)', bg: 'rgba(46,160,67,0.12)' },
  algo3:  { label: 'READY · 41%WR',        color: 'var(--green-light)', bg: 'rgba(46,160,67,0.12)' },
  algo4:  { label: 'DEV · 73%WR · Low F',   color: 'var(--orange)',      bg: 'rgba(227,179,65,0.1)' },
  algo5:  { label: 'READY · 61%WR',        color: 'var(--green-light)', bg: 'rgba(46,160,67,0.12)' },
  algo6:  { label: 'DEV · 43%WR · High DD', color: 'var(--orange)',      bg: 'rgba(227,179,65,0.1)' },
  algo7:  { label: 'READY · 57%WR',        color: 'var(--green-light)', bg: 'rgba(46,160,67,0.12)' },
  algo8:  { label: 'DEV · 38%WR',          color: 'var(--orange)',      bg: 'rgba(227,179,65,0.1)' },
  algo9:  { label: 'DEV · 55%WR · Filter', color: 'var(--orange)',      bg: 'rgba(227,179,65,0.1)' },
  algo10: { label: 'DEV · 50%WR · Best FQ', color: 'var(--green-light)', bg: 'rgba(46,160,67,0.12)' },
  algo11: { label: 'STUDY · 46%WR',        color: 'var(--text-muted)',  bg: 'rgba(125,133,144,0.1)' },
  algo12: { label: 'STUDY · 30%WR · Dip',  color: 'var(--text-muted)',  bg: 'rgba(125,133,144,0.1)' },
  algo13: { label: 'READY · 49%WR · Roll', color: 'var(--green-light)', bg: 'rgba(46,160,67,0.12)' },
  algo14: { label: 'READY · 49%WR · ML',   color: 'var(--green-light)', bg: 'rgba(46,160,67,0.12)' },
  algo15: { label: 'READY · 45%WR · Agg', color: 'var(--green-light)', bg: 'rgba(46,160,67,0.12)' },
  algo16: { label: 'READY · 94%WR · Scalp', color: 'var(--green-light)', bg: 'rgba(46,160,67,0.12)' },
  algo17: { label: 'READY · 95%WR · Scalp-Agg', color: 'var(--green-light)', bg: 'rgba(46,160,67,0.12)' },
};

// ── Algo Info Tooltips ── Why each algo was chosen ────────────────────────────
const ALGO_INFO = {
  algo1:  "Native suite: Short Straddle with daily range filter. Proven 58% WR on NIFTY. Basis of the original algo stack.",
  algo2:  "Native suite: Enhanced short straddle (Scenario B) with close-move filter. Highest WR (97%) in the suite.",
  algo3:  "Native suite: EMA 5/20 crossover + RSI filter. Classic trend-following adapted for NIFTY weekly options.",
  algo4:  "Native suite: Options-flow proxy using EMA-13 trend. Filters for strong directional days.",
  algo5:  "Native suite: VIX mean-reversion. Buys NIFTY when fear spikes (high India VIX). Counter-trend defensive.",
  algo6:  "Native suite: SuperTrend + ADX credit spread. Trend-following with defined risk.",
  algo7:  "Native suite: Opening range breakout (Dual Thrust). 57% WR breakout system.",
  algo8:  "Native suite: CPMA vs EMA scalper. Intraday micro-trend capture with tight stops.",
  algo9:  "Native suite: Composite bullish score (SMA+RSI+MACD+ADX). Multi-factor confluence.",
  algo10: "Native suite: Awesome Oscillator + ADX>25. Momentum + trend strength confirmation.",
  algo11: "Native suite: Long ATM straddle proxy. Gamma scalping concept (study only — requires live Greeks).",
  algo12: "From lumibot-dev (AAPL Deep Dip): Buy ATM CE on 2% dip from 20-day high. Counter-trend recovery play.",
  algo13: "From Stock-Prediction-Models (Signal Rolling): 3-day consecutive close momentum. Simple but powerful trend persistence.",
  algo14: "From Stock-Prediction-Models: First ML algo in suite. RandomForest on 10 features predicts next-day direction.",
  algo15: "From freqAI-LSTM (Crypto): 9 normalized indicators → dynamic weighted aggregate score + vol adjustment. Best Sharpe (8.66).",
  algo16: "From nifty_scalper-main: 5-checklist confluence (VWAP+EMA+Supertrend+RSI+VIX). 4/5 align → ATM CE/PE intraday scalper. +2%Tgt/-5%SL.",
  algo17: "From nifty_scalper-main: Same as algo16 but 3/5 confluence (more aggressive). More trades, slightly higher risk. Intraday only.",
};

let masterCalendar = null;
let liveInterval   = null;
let summaryData    = {};

// ── Init ──────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  loadDashboard();
  loadLivePrice();
  initBacktestPanel('master_backtest', ALGO_IDS);
  liveInterval = setInterval(loadLivePrice, 15000); // refresh price every 15s

  // Master calendar (all algos)
  masterCalendar = new AlgoCalendar('master_calendar', 'all', onCalendarDateClick);
});

// ── Load dashboard data ────────────────────────────────────────────────────────
async function loadDashboard() {
  try {
    const res  = await fetch('/api/dashboard');
    const data = await res.json();
    summaryData = data.algos || {};
    renderAlgoCards(summaryData);
  } catch(e) {
    console.error('Dashboard load error:', e);
  }
}

// ── Live Nifty price ──────────────────────────────────────────────────────────
async function loadLivePrice() {
  try {
    const res  = await fetch('/api/nifty/live');
    const data = await res.json();
    const el = document.getElementById('live_nifty');
    const vx = document.getElementById('live_vix');
    const tm = document.getElementById('live_time');
    if (el) el.textContent = data.nifty ? data.nifty.toLocaleString('en-IN') : '--';
    if (vx) vx.textContent = data.vix ? 'VIX ' + data.vix : '';
    if (tm) tm.textContent = data.time || '';
  } catch(e) {}
}

// ── Render algo summary cards ─────────────────────────────────────────────────
function renderAlgoCards(algos) {
  const grid = document.getElementById('algo_cards_grid');
  if (!grid) return;

  grid.innerHTML = ALGO_IDS.map(id => {
    const a       = algos[id] || {};
    const pnl     = a.pnl_summary || {};
    const running = a.paper_running;
    const status  = running ? 'paper' : 'off';
    const statusLabel = running ? 'PAPER' : 'OFF';
    const todayPnl = pnl.today || 0;
    const mtdPnl   = pnl.one_month || 0;
    const positions = a.positions_count || 0;

    return `
      <div class="algo-summary-card" onclick="window.location.href='/algo/${id}'">
        <div style="display:flex;align-items:flex-start;gap:10px">
          <div style="width:38px;height:38px;border-radius:8px;background:${ALGO_COLORS[id]};
            display:flex;align-items:center;justify-content:center;font-weight:700;font-size:13px;
            color:#fff;flex-shrink:0">
            ${ALGO_ICONS[id]}
          </div>
          <div style="flex:1;min-width:0">
            <div style="display:flex;align-items:center;gap:6px">
              <div class="name" style="font-size:13px">${a.short_name || a.algo_name || id}</div>
              <span class="algo-info-btn" data-info="${ALGO_INFO[id] || ''}" style="width:16px;height:16px;border-radius:50%;background:var(--text-muted);color:#fff;display:inline-flex;align-items:center;justify-content:center;font-size:10px;font-weight:700;cursor:help;flex-shrink:0" title="${ALGO_INFO[id] || ''}">i</span>
            </div>
            <div style="display:inline-block;margin-top:3px;padding:1px 7px;border-radius:4px;font-size:10px;font-weight:600;
              color:${ALGO_TAGS[id].color};background:${ALGO_TAGS[id].bg}">
              ${ALGO_TAGS[id].label}
            </div>
            <div class="subtitle" style="margin-top:4px">${a.subtitle || ''}</div>
          </div>
        </div>

        <div class="status-badge ${status}" style="margin-top:10px">
          <span style="width:6px;height:6px;border-radius:50%;background:currentColor;display:inline-block"></span>
          ${statusLabel}
          ${positions > 0 ? `&nbsp;· ${positions} open` : ''}
        </div>

        <div class="metrics-row" style="margin-top:12px">
          <div class="metric">
            <span class="label">Today</span>
            <span class="value ${pnlClass(todayPnl)}">${fmtPnl(todayPnl)}</span>
          </div>
          <div class="metric">
            <span class="label">MTD</span>
            <span class="value ${pnlClass(mtdPnl)}">${fmtPnl(mtdPnl)}</span>
          </div>
          <div class="metric">
            <span class="label">Open</span>
            <span class="value text-muted">${positions}</span>
          </div>
        </div>

        <div style="margin-top:10px;font-size:11px;color:var(--blue)">
          View Detail →
        </div>
      </div>
    `;
  }).join('');
}

// ── Calendar date click → drawer ───────────────────────────────────────────────
function onCalendarDateClick(dateStr) {
  openDateDrawer(dateStr, 'all');
}

async function openDateDrawer(dateStr, algoId) {
  const drawer  = document.getElementById('date_drawer');
  const overlay = document.getElementById('date_drawer_overlay');
  const title   = document.getElementById('drawer_title');
  const body    = document.getElementById('drawer_body');
  if (!drawer) return;

  // Format date nicely
  const d = new Date(dateStr + 'T00:00:00');
  const dayName = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'][d.getDay()];
  const monthNames = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  const label = `${dayName}, ${d.getDate()} ${monthNames[d.getMonth()]} ${d.getFullYear()}`;
  if (title) title.textContent = label;

  if (body) body.innerHTML = `<div style="padding:20px;text-align:center"><div class="spinner"></div></div>`;
  drawer.classList.add('open');
  overlay.classList.add('open');

  try {
    const res  = await fetch(`/api/trades/date/${algoId}/${dateStr}`);
    const data = await res.json();
    if (body) body.innerHTML = renderDrawerTrades(data);
  } catch(e) {
    if (body) body.innerHTML = `<div style="color:var(--red-light);padding:12px">Failed to load trades</div>`;
  }
}

function closeDateDrawer() {
  document.getElementById('date_drawer')?.classList.remove('open');
  document.getElementById('date_drawer_overlay')?.classList.remove('open');
}

function renderDrawerTrades(data) {
  const trades = data.trades || [];
  const dayPnl = data.day_pnl || 0;

  if (trades.length === 0) {
    return `
      <div class="empty-state">
        <div class="empty-icon">📭</div>
        <div>No trades on this day</div>
        <div class="text-dim" style="font-size:10px">No signals triggered</div>
      </div>`;
  }

  const header = `
    <div class="day-pnl-header">
      <span>Day P&L</span>
      <span class="day-pnl-value ${pnlClass(dayPnl)}">${fmtPnl(dayPnl)}</span>
    </div>`;

  const cards = trades.map(t => renderTradeCard(t)).join('');
  return header + cards;
}

function renderTradeCard(t) {
  const pnl    = t.pnl || 0;
  const pnlPct = t.pnl_pct || 0;
  const exitReason = (t.exit_reason || '').toLowerCase();
  let exitCls = 'eod';
  if (exitReason.includes('target')) exitCls = 'target';
  else if (exitReason.includes('tsl') || exitReason.includes('trailing')) exitCls = 'tsl';
  else if (exitReason.includes('sl') || exitReason.includes('stop')) exitCls = 'sl';

  const optBadge = t.option_type === 'CE' ? 'badge-ce'
    : t.option_type === 'PE' ? 'badge-pe' : 'badge-both';
  const subName = t.sub_strategy || t.signal_name || 'TRADE';

  return `
    <div class="trade-card">
      <div class="trade-card-header">
        <div class="trade-card-left">
          <div class="trade-name">${subName.replace(/_/g,' ')}</div>
          <div class="trade-meta">
            <span class="signal-tag">${t.algo_name || t.algo_id}</span>
            <span class="expiry">${t.entry_time ? t.entry_time.replace('T',' ').slice(0,16) : t.date}</span>
          </div>
        </div>
        <div class="trade-card-right">
          <div class="pnl-per-lot ${pnlClass(pnl)}">${fmtPnl(pnl)}</div>
          <div class="pnl-pct ${pnlClass(pnl)}">${pnlPct > 0 ? '▲' : pnl < 0 ? '▼' : ''} ${Math.abs(pnlPct).toFixed(2)}%</div>
        </div>
      </div>

      <div class="trade-legs">
        <table>
          <thead><tr>
            <th>SYMBOL</th><th>ENTRY</th><th>EXIT</th>
          </tr></thead>
          <tbody><tr>
            <td class="leg-symbol">
              <span class="${optBadge}">${t.option_type || 'N/A'}</span>
              NIFTY ${t.strike || ''}
            </td>
            <td>${t.entry_price ? '₹' + Number(t.entry_price).toFixed(1) : '—'}</td>
            <td>${t.exit_price ? '₹' + Number(t.exit_price).toFixed(1) : '—'}</td>
          </tr></tbody>
        </table>
      </div>

      <div class="trade-card-footer">
        <span>Closed: ${t.exit_time ? t.exit_time.slice(0,16).replace('T',' ') : '—'}</span>
        <span class="exit-reason ${exitCls}">${(t.exit_reason||'—').replace(/_/g,' ')}</span>
      </div>
    </div>
  `;
}
