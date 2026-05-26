# Algo Automation — NIFTY50 Options Algo Lab

> **Educational purpose only. NOT financial advice. No real money is deployed here.**

A personal research & experimentation platform for studying NIFTY50 options trading strategies. Built as a unified dashboard to backtest, paper-trade, and compare 17 different algorithms — from classic technical analysis to machine learning.

---

## What This Is

This repo is a learning lab. Each algo started as a hypothesis — *"what if I traded only when VIX spikes?"* or *"can a Random Forest predict NIFTY direction?"* — and this platform is the framework to test those ideas with real historical data, structured logging, and a visual dashboard.

**Not intended for live trading.**

---

## Project Structure

```
AlgoTrader/
├── algos/              # 17 strategy implementations
├── api/                # FastAPI route handlers
├── backtest/           # Backtesting engine
├── data_sources/       # yfinance, NSE, Dhan fetchers
├── frontend/           # HTML dashboard (no framework)
├── import_project/     # Tool to analyse & import external algo projects
├── paper/              # Paper trading runner
├── storage/            # CSV trade/P&L storage
├── utils/              # Logger, settings, helpers
├── config.py           # Central config — all algo metadata, paths, constants
├── main.py             # FastAPI entry point
└── reports/            # Postmortem reports for each algo
```

---

## Algorithms

| # | Name | Type | Win Rate | Notes |
|---|------|------|----------|-------|
| 1 | **RD-Straddle** | Short Straddle (Daily Range Filter) | 58% | Stable baseline |
| 2 | **NTB-ScenB** | Short Straddle (Close-Move Filter) | 97% | Best performer — close-move filtered |
| 3 | **EMA Crossover** | EMA 5/20 + RSI → CE/PE Buy | 39% | Under development |
| 4 | **Flow-NIFTY** | EMA-13 Trend Proxy → NIFTY Buy | 39% | Study / exploratory |
| 5 | **VIX Reversion** | India VIX spike → Mean reversion Buy | — | Study |
| 6 | **SuperTrend Spread** | SuperTrend + ADX Credit Spread | — | Study |
| 7 | **Dual Thrust** | Opening Range Breakout | 57% | Viable |
| 8 | **CPMA Scalper** | EMA(20) vs CPMA(21) Crossover | 38% | Under development |
| 9 | **Bullish Scanner** | Composite score (SMA+RSI+MACD+ADX+Momentum) | — | Under development |
| 10 | **Awesome Oscillator** | AO(3,21) + ADX>25 → CE/PE | 50% | Under development |
| 11 | **Gamma Scalping Proxy** | Long ATM Straddle + Delta Hedge | — | Study (not true gamma) |
| 12 | **Dip Recovery** | 2% dip from 20d high → CE Buy | — | Study |
| 13 | **Signal Rolling** | 3-day close momentum streak → CE/PE | 49% | Viable |
| 14 | **ML-RF Classifier** | RandomForest on RSI/MACD/BB/Vol | 49% | Viable |
| 15 | **Aggregate Score** | 9 indicators → weighted dynamic score | 45% | Viable (ported from FreqAI project) |
| 16 | **Scalper 4/5** | VWAP+EMA+ST+RSI+VIX — 4/5 confluence | 94% | Intraday |
| 17 | **Scalper 3/5** | VWAP+EMA+ST+RSI+VIX — 3/5 confluence | 95% | Intraday (aggressive) |

All algos trade NIFTY50 ATM options. Lot size: 25. Starting capital per algo: ₹2,00,000.

---

## Features

- **Backtesting** — Run any algo on historical NIFTY data, see trade-by-trade P&L
- **Paper Trading** — Simulated live trading using NSE option chain + yfinance data (no real orders)
- **Live Dashboard** — FastAPI + plain HTML dashboard to monitor all algos, signals, and P&L
- **Option Chain** — Live NSE option chain polling (60s refresh)
- **Trade Logs** — Structured CSV logs per algo with entry/exit reasons
- **Import Tool** — Analyse and import external algo projects into the framework
- **Postmortem Reports** — Written analysis of each experiment's outcome

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3, FastAPI, Uvicorn |
| Data | yfinance, NSE OCA (option chain), Dhan API |
| Computation | pandas, numpy, scipy, scikit-learn |
| Storage | CSV files (no database) |
| Frontend | Plain HTML + JS (no framework) |

---

## Setup

```bash
# Clone
git clone https://github.com/chhagansingh/Algo_Automation.git
cd Algo_Automation/AlgoTrader

# Install dependencies
pip install -r requirements.txt

# Run the server
python main.py
# OR
./start.sh

# Open dashboard
# http://localhost:5000
```

To stop:
```bash
./stop.sh
```

---

## Data Sources

- **yfinance** — Historical NIFTY daily OHLCV (`^NSEI`)
- **NSE Option Chain API** — Live option chain data (no auth required)
- **Dhan API** — Optional; configure token in Settings page

---

## Disclaimer

This project is built purely for **learning and research purposes**.

- No real trades are placed
- Backtest results do not guarantee future performance
- Options trading involves substantial risk of loss
- Past win rates shown are on historical data only

---

## Author

**Chhagan Singh** — experimenting with algo trading concepts, one strategy at a time.
