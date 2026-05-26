# AlgoTrader — Complete Roadmap & Build Plan

## Project Goal
Single unified dashboard to monitor, backtest and paper-trade all 3 NIFTY50 algo strategies.
- No existing code changes — original algos are wrapped as-is
- All storage: CSV only (no database)
- Professional dark-themed UI (mobile-responsive)
- FastAPI backend + HTML/TailwindCSS/Alpine.js/Chart.js frontend

---

## 3 Algos Being Wrapped

| ID | Name | Source File | Strategy Logic |
|----|------|------------|----------------|
| algo1 | R&D Binary Straddle | `R&D/backtest_strategy.py` | Daily range < 1% → sell ATM straddle |
| algo2 | NiftyTradeBot ScenB | `nifty_tradebot-main/backtest_may2025.py` | Short straddle + close-move filter (ScenB) |
| algo3 | NiftyBot EMA/RSI | `Nifty-Bot-main/backtest_may2025.py` | EMA5/20 crossover + RSI>55/<45 → buy CE/PE |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI (Python) |
| Frontend | HTML + TailwindCSS (CDN) + Alpine.js + Chart.js |
| Charts | Chart.js |
| Storage | CSV files |
| Paper Trading | FastAPI BackgroundTasks |
| Python deps | fastapi, uvicorn, pandas, numpy, yfinance, scipy |

---

## Folder Structure (Final)

```
AlgoTrader/
├── ROADMAP.md                        ← This file
├── CHECKLIST.md                      ← Build progress tracker
├── main.py                           ← FastAPI app entry point (uvicorn target)
├── config.py                         ← Paths, constants, algo metadata
├── requirements.txt
│
├── algos/                            ← Algo wrappers (original logic imported unchanged)
│   ├── __init__.py
│   ├── base.py                       ← AlgoBase class (run_backtest interface)
│   ├── algo1_rd_straddle.py          ← Wraps R&D backtest_strategy.py logic
│   ├── algo2_ntb_scenb.py            ← Wraps nifty_tradebot ScenB logic
│   └── algo3_niftybot_ema.py         ← Wraps Nifty-Bot EMA/RSI + Iron Condor + Short Straddle
│
├── backtest/
│   └── engine.py                     ← run_backtest(algo_id, start, end) → TradeList + Metrics
│
├── storage/
│   └── csv_store.py                  ← read/write trades, paper positions, daily summary
│
├── paper/
│   └── runner.py                     ← BackgroundTask: fetch live data, generate signals, log trades
│
├── data/
│   ├── trades/
│   │   ├── algo1_trades.csv          ← Closed trades per algo
│   │   ├── algo2_trades.csv
│   │   └── algo3_trades.csv
│   ├── paper/
│   │   ├── algo1_paper_open.csv      ← Open paper positions
│   │   ├── algo2_paper_open.csv
│   │   └── algo3_paper_open.csv
│   └── daily_summary.csv             ← Date | algo_id | pnl | trades_count
│
├── api/
│   ├── __init__.py
│   ├── routes_dashboard.py           ← GET /api/dashboard (master view data)
│   ├── routes_backtest.py            ← POST /api/backtest (run backtest for date range)
│   ├── routes_algo.py                ← GET /api/algo/{id} (per-algo detail)
│   ├── routes_paper.py               ← POST /api/paper/{id}/start|stop
│   └── routes_calendar.py            ← GET /api/calendar/{algo_id}/{year}/{month}
│
└── frontend/
    ├── index.html                    ← Master Dashboard
    ├── algo_detail.html              ← Per-Algo Dashboard
    └── static/
        ├── css/
        │   └── style.css             ← Custom dark theme overrides
        └── js/
            ├── dashboard.js          ← Master dashboard: algos summary, tabs
            ├── algo_detail.js        ← Per-algo: open/closed trades, signals
            ├── calendar.js           ← Reusable calendar component
            ├── charts.js             ← Chart.js P&L curve + monthly bar
            └── backtest.js           ← Backtest panel: date picker, compare, results
```

---

## API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/` | Serve master dashboard |
| GET | `/algo/{id}` | Serve per-algo detail page |
| GET | `/api/dashboard` | Master summary: all algos status, today P&L, positions |
| GET | `/api/algo/{id}/summary` | Algo detail: signals, open positions, today trades |
| GET | `/api/algo/{id}/trades` | All closed trades (paginated) |
| GET | `/api/algo/{id}/open` | Open paper positions |
| GET | `/api/calendar/{id}/{year}/{month}` | Calendar: daily P&L for month |
| POST | `/api/backtest` | Body: {algo_ids, start_date, end_date} → metrics + trades |
| POST | `/api/paper/{id}/start` | Start paper trading for algo |
| POST | `/api/paper/{id}/stop` | Stop paper trading for algo |
| GET | `/api/nifty/live` | Live Nifty price + VIX (yfinance fast quote) |

---

## Dashboard Pages

### Page 1: Master Dashboard (`/`)
- Top tabs: Algo1 | Algo2 | Algo3 (with live status dot)
- Per-algo card: Name, status badge (LIVE/PAPER/OFF), Today P&L, MTD P&L, Positions
- Backtest panel: date range picker + multi-algo checkboxes + RUN → Compare table
- Calendar: month nav (← →), monthly return below month name, colored daily P&L cells
- Right panel on date click: all trades of that day across all algos

### Page 2: Per-Algo Dashboard (`/algo/{id}`)
- Header: Algo name + subtitle, Live Nifty + VIX, status badge, last updated
- Right sidebar (fixed): P&L summary cards (1Y/6M/3M/1M/Today), Portfolio exposure, Calendar
- Main area:
  - Live Signals section: metric cards (EMA5, EMA20, RSI, ADX etc. as per algo)
  - Progress bars for signal scores
  - Open Positions table: Symbol | Strike | CE/PE | Entry | LTP | Signal | Unr.P&L
  - Closed Trades: trade cards with legs, entry/exit time, exit reason, P&L ₹ + %
- Backtest drawer: date range → single algo backtest → metrics table + monthly breakdown

---

## CSV Schema

### trades CSV (algo1_trades.csv etc.)
```
trade_id, algo_id, date, symbol, strike, option_type, signal_name,
entry_time, entry_price, exit_time, exit_price, exit_reason,
pnl, pnl_pct, lot_size, status(open/closed)
```

### paper_open CSV
```
trade_id, algo_id, open_time, symbol, strike, option_type, signal_name,
entry_price, current_ltp, unrealized_pnl, lot_size
```

### daily_summary CSV
```
date, algo_id, total_pnl, trades_count, wins, losses
```

---

## Build Phases

### Phase 1 — Scaffold + Config + Storage
- [ ] Create folder structure
- [ ] requirements.txt
- [ ] config.py (paths, algo metadata, constants)
- [ ] storage/csv_store.py (read/write all CSVs)
- [ ] Initialize empty CSVs with headers

### Phase 2 — Algo Wrappers
- [ ] algos/base.py (AlgoBase interface)
- [ ] algos/algo1_rd_straddle.py (exact logic from backtest_strategy.py)
- [ ] algos/algo2_ntb_scenb.py (exact ScenB logic from ntb backtest_may2025.py)
- [ ] algos/algo3_niftybot_ema.py (EMA/RSI + Iron Condor + Short Straddle from niftybot backtest)

### Phase 3 — Backtest Engine
- [ ] backtest/engine.py
  - [ ] run_backtest(algo_id, start_date, end_date) function
  - [ ] Returns: metrics dict + trades list
  - [ ] run_compare(algo_ids, start_date, end_date) for multi-algo compare
  - [ ] Monthly breakdown generator

### Phase 4 — FastAPI Routes
- [ ] main.py with FastAPI app + static file serving
- [ ] api/routes_dashboard.py
- [ ] api/routes_backtest.py
- [ ] api/routes_algo.py
- [ ] api/routes_paper.py
- [ ] api/routes_calendar.py

### Phase 5 — Paper Trading Runner
- [ ] paper/runner.py
  - [ ] fetch_live_nifty() via yfinance
  - [ ] generate_signal(algo_id) → uses algo wrapper
  - [ ] log_trade_to_csv()
  - [ ] BackgroundTask per algo (start/stop control)

### Phase 6 — Frontend Master Dashboard
- [ ] frontend/index.html (dark theme shell)
- [ ] frontend/static/css/style.css
- [ ] frontend/static/js/dashboard.js
  - [ ] Algo summary cards with live status
  - [ ] Master calendar (all algos combined)
  - [ ] Date click → right panel with trades
- [ ] frontend/static/js/calendar.js (reusable component)
- [ ] frontend/static/js/charts.js (P&L curve + monthly bar)

### Phase 7 — Frontend Per-Algo Dashboard
- [ ] frontend/algo_detail.html
- [ ] frontend/static/js/algo_detail.js
  - [ ] Signal metric cards (live signals section)
  - [ ] Open positions table
  - [ ] Closed trades cards (Image 3 style — legs, entry/exit, reason, P&L)
  - [ ] P&L Summary sidebar cards (1Y/6M/3M/1M/Today)
  - [ ] Per-algo calendar (right sidebar)
  - [ ] HALT/START buttons

### Phase 8 — Frontend Backtest Panel
- [ ] frontend/static/js/backtest.js
  - [ ] Date range picker
  - [ ] Algo checkboxes (single or multi-compare)
  - [ ] RUN button → POST /api/backtest
  - [ ] Results: compare table (metrics side by side)
  - [ ] Monthly breakdown table (expandable)
  - [ ] P&L curve chart (Chart.js, one line per algo)

---

## Key Design Decisions

1. **No existing code modified** — algo wrappers copy the logic as pure functions
2. **yfinance for data** — same as existing backtests (^NSEI daily OHLCV)
3. **Dark theme** — exactly like the reference dashboard screenshots
4. **Mobile-first** — TailwindCSS responsive grid (1-col mobile, 3-col desktop)
5. **No build step** — TailwindCSS via CDN, Chart.js via CDN, Alpine.js via CDN
6. **Paper trading = simulated** — real Nifty prices from yfinance, virtual execution
7. **Calendar** — right sidebar on per-algo page, standalone on master dashboard
8. **Trade cards** — Image 3 style: trade name, strategy tag, legs table, close info

---

## Signal Card Mapping (per algo)

### Algo 1 — R&D Straddle
- Daily Range % | Trade Condition (< 1%) | Signal: STRADDLE_SELL
- Exit: TARGET_EXIT / SL_EXIT

### Algo 2 — NiftyTradeBot ScenB
- Daily Range % | Close Move % | Trade Condition | WIN_PNL | LOSS_PNL
- Signal: SHORT_STRADDLE | Exit: THRESHOLD_EXIT / CLOSE_MOVE_EXIT

### Algo 3 — NiftyBot EMA/RSI
- EMA5 | EMA20 | RSI | ADX | ATR% | Regime
- Signal: EMA_BUY_CE / EMA_BUY_PE / IRON_CONDOR / SHORT_STRADDLE
- Exit: TSL_EXIT / SIGNAL_FLIP / TARGET_EXIT / SL_EXIT
