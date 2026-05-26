# AlgoTrader — Build Checklist
> Follow this file to track progress. Update status as each item completes.
> Legend: [ ] = pending | [x] = done | [~] = in progress

---

## Phase 1 — Scaffold + Config + Storage
- [x] Create full folder structure (algos/ backtest/ storage/ paper/ data/ api/ frontend/)
- [x] requirements.txt (fastapi, uvicorn, pandas, numpy, yfinance, scipy, python-multipart)
- [x] config.py — algo metadata, CSV paths, constants
- [x] storage/csv_store.py — read/write trades, open positions, daily summary
- [x] Initialize empty CSVs with correct headers (data/trades/, data/paper/, data/daily_summary.csv)

## Phase 2 — Algo Wrappers
- [x] algos/__init__.py
- [x] algos/base.py — AlgoBase class with run_backtest() + _metrics() + _monthly_breakdown() interface
- [x] algos/algo1_rd_straddle.py — R&D binary straddle logic (exact copy as function)
- [x] algos/algo2_ntb_scenb.py — NiftyTradeBot ScenB logic (exact copy as function)
- [x] algos/algo3_niftybot_ema.py — NiftyBot 3 strategies (EMA/RSI + Iron Condor + Short Straddle)
- [x] Test: import all 3 wrappers, run_backtest() returns trades list ✓

## Phase 3 — Backtest Engine
- [x] backtest/__init__.py
- [x] backtest/engine.py — run_backtest(algo_id, start, end) → {metrics, trades}
- [x] backtest/engine.py — run_compare(algo_ids, start, end) → side-by-side compare table
- [x] backtest/engine.py — monthly_breakdown via base class
- [x] Test: run backtest all 3 algos, results verified ✓

## Phase 4 — FastAPI Backend
- [x] main.py — FastAPI app, static files, route includes, CORS
- [x] api/__init__.py
- [x] api/routes_dashboard.py — GET /api/dashboard + GET /api/nifty/live
- [x] api/routes_algo.py — GET /api/algo/{id}/summary, /trades (paginated), /open
- [x] api/routes_backtest.py — POST /api/backtest (single + compare, auto-saves trades to CSV)
- [x] api/routes_paper.py — POST /api/paper/{id}/start|stop + GET /api/paper/status
- [x] api/routes_calendar.py — GET /api/calendar/all/{y}/{m}, /algo/{id}/{y}/{m}, /api/trades/date/{id}/{date}
- [x] Test: all endpoints return 200, backtest saves trades, calendar reflects data ✓

## Phase 5 — Paper Trading Runner
- [x] paper/__init__.py
- [x] paper/runner.py — fetch_live_nifty() via yfinance 1-min + daily bars
- [x] paper/runner.py — _compute_indicators() — EMA5/20, RSI, ATR%, regime
- [x] paper/runner.py — _paper_loop() — signal generation, open/close position to CSV
- [x] paper/runner.py — start_paper()/stop_paper() via threading.Event + BackgroundTasks

## Phase 6 — Frontend: Master Dashboard
- [x] frontend/index.html — dark theme shell, topbar, algo tabs, sidebar layout
- [x] frontend/static/css/style.css — full dark theme (600 lines: cards, badges, calendar, trade cards, drawer, responsive)
- [x] Header: algo tabs with live status dots, Nifty+VIX live price
- [x] Algo summary cards (3-col grid): name, status badge, Today P&L, MTD, open positions, click → detail
- [x] Backtest panel: date picker + multi-algo checkboxes + RUN button
- [x] Compare results table (side-by-side metrics + monthly breakdown + equity curve chart)
- [x] Master calendar (all algos combined): month nav ← →, monthly return, colored daily cells
- [x] Date click → right drawer with all trades of that day
- [x] frontend/static/js/dashboard.js — fetch /api/dashboard, render cards, calendar init
- [x] frontend/static/js/calendar.js — reusable AlgoCalendar class (profit/loss/today/selected styling)
- [x] frontend/static/js/charts.js — renderEquityCurve(), renderMonthlyBar(), fmtPnl(), fmtPct()
- [x] Mobile responsive: CSS grid collapses at 768px/640px, sidebar hidden on mobile

## Phase 7 — Frontend: Per-Algo Dashboard
- [x] frontend/algo_detail.html — dark theme with 2-col layout (main + sidebar)
- [x] Header: algo name, subtitle, Nifty+VIX, status badge, updated time, HALT/START button
- [x] Right sidebar: P&L Summary cards (1Y/6M/3M/1M/Today), Portfolio Exposure + status bar, Calendar
- [x] Signal metric cards (dark cards, colored values per algo: EMA5/20/RSI/ADX for algo3 etc.)
- [x] Signal + lot-size badge row showing current signal + option type + strike
- [x] Open Positions table: Symbol | Strike | CE/PE | Entry Time | Entry | LTP | Signal | Unr.P&L
- [x] Closed Trades — trade cards (Image 3 style):
  - [x] Trade name + signal tag + entry datetime
  - [x] Legs table: SYMBOL | ENTRY | EXIT price
  - [x] Footer: closed time + exit reason badge (TARGET/TSL/SL/EOD color coded)
  - [x] P&L / Lot + % (green/red with arrow)
- [x] Per-algo calendar in right sidebar (date click → right drawer with that day's trades)
- [x] START PAPER / HALT buttons (live toggle)
- [x] Backtest panel (single algo pre-selected, date range, run → results inline)
- [x] frontend/static/js/algo_detail.js — full render pipeline (signals, positions, trades, calendar, paper controls)
- [x] Pagination for closed trades (20 per page, prev/next)

## Phase 8 — Frontend: Backtest Compare Panel
- [x] Shared backtest panel component (initBacktestPanel() in backtest.js, used on both pages)
- [x] Date range picker (from/to with max=today)
- [x] Algo checkboxes (multi-select, pre-selected per page context)
- [x] RUN BACKTEST → POST /api/backtest → spinner loading state
- [x] Single result: 8 metric cards + equity curve chart + monthly breakdown table
- [x] Compare result: side-by-side table (best highlighted green), equity multi-line chart, monthly compare table
- [x] frontend/static/js/backtest.js — full API integration + result rendering

---

## Final Verification
- [x] `uvicorn main:app --reload --port 8080` starts cleanly
- [x] GET /api/dashboard → all 3 algos data ✓
- [x] GET /api/nifty/live → live Nifty 23988.90, VIX 16.83 ✓
- [x] POST /api/backtest (single) → metrics, trades, monthly, equity_curve ✓
- [x] POST /api/backtest (compare 3 algos) → compare_table, monthly_compare, equity_curves ✓
- [x] GET /api/calendar/algo3/2025/5 → monthly ₹18,403, 13 trading days ✓
- [x] GET /api/trades/date/algo3/2025-05-23 → count:1, pnl:₹3,268 ✓
- [x] GET /api/algo/algo3/trades → total:43 trades ✓
- [x] GET / → index.html served ✓
- [x] GET /algo/algo3 → algo_detail.html served ✓
- [x] CSV files created and populated: algo3_trades.csv (43 rows) ✓
- [ ] Browser UI test — open http://localhost:8080 and verify dashboard renders
- [ ] Browser UI test — backtest panel run and compare view
- [ ] Mobile responsive test (375px Chrome DevTools)

---

## Progress Summary
- Phase 1: 5/5 ✅
- Phase 2: 6/6 ✅
- Phase 3: 5/5 ✅
- Phase 4: 8/8 ✅
- Phase 5: 5/5 ✅
- Phase 6: 12/12 ✅
- Phase 7: 14/14 ✅
- Phase 8: 8/8 ✅
- Final API: 11/14 done (3 browser tests pending)

**Total: 74/77 items complete — Server running, APIs verified ✓**

---

## How to Run

```bash
cd /Users/com/Desktop/R&D/AlgoTrader
uvicorn main:app --reload --port 8080
# Open: http://localhost:8080
```

## API Quick Reference
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Master Dashboard UI |
| `/algo/{id}` | GET | Per-Algo Dashboard UI |
| `/api/dashboard` | GET | All algos summary JSON |
| `/api/nifty/live` | GET | Live Nifty + VIX |
| `/api/algo/{id}/summary` | GET | Algo signals + P&L |
| `/api/algo/{id}/trades` | GET | Paginated closed trades |
| `/api/algo/{id}/open` | GET | Open paper positions |
| `/api/backtest` | POST | Run backtest (saves to CSV) |
| `/api/calendar/all/{y}/{m}` | GET | Master calendar data |
| `/api/calendar/{id}/{y}/{m}` | GET | Per-algo calendar |
| `/api/trades/date/{id}/{date}` | GET | Trades for specific date |
| `/api/paper/{id}/start` | POST | Start paper trading |
| `/api/paper/{id}/stop` | POST | Stop paper trading |
| `/api/paper/status` | GET | All runners status |
