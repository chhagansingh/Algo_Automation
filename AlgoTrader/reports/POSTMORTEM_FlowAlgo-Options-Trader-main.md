# Postmortem Report: FlowAlgo-Options-Trader-main
**Generated:** 2026-05-25
**Algo ID:** imported_flowalgo_options_trader_main_0525
**Manual Review:** YES — auto-extraction FAILED, corrected by hand

---

## 1. Executive Summary

| Attribute | Value |
|-----------|-------|
| **Project Type** | Real Trading System (US Equity Options Flow) |
| **Strategy Type** | Options-Flow-Driven Stock Picking (LONG only) |
| **Data Source** | FlowAlgo.com (paid subscription, US-only) |
| **Broker** | Alpaca API (US equities) |
| **ML Components** | DQN Agent, PPG (Phasic Policy Gradient), K-Means/DBSCAN Clustering |
| **Complexity** | HIGH — multi-strategy architecture |
| **Indian Market Fit** | MEDIUM — concept transferable, data source incompatible |

---

## 2. Architecture Breakdown

### 2.1 Rules-Based Strategy (`backtest.py`, `trade.py`)
The core engine. Uses options flow data to generate stock BUY signals.

**Entry Rules:**
| Rule | Default | Description |
|------|---------|-------------|
| `min_time` | 09:45 | Ignore options before market open + 15min |
| `top_n_tickers` | 50 | Only consider top 50 tickers by option frequency |
| `call_occurences` | 2 | Minimum call count before considering a ticker |
| `cp_ratio_min` | 0 | Minimum overall call/put ratio |
| `put_penalty` | -1 | Frequency penalty for PUT contracts |
| `min_premium` | $20,000 | Minimum contract premium |
| `max_premium` | $1,000,000 | Maximum contract premium |
| `max_days_to_exp` | 7 | Maximum days to expiry |
| `spy_ema` | True | Only trade if SPY > EMA-13 |
| `target_pos` | 0.10 | Position size = 10% of equity |

**Exit Rules:**
| Rule | Default | Description |
|------|---------|-------------|
| `sell_after_gain` | +0.15 | Sell if gain exceeds 15% |
| `sell_after_loss` | -0.06 | Sell if loss exceeds 6% |
| `sell_perc_to_expiry` | 1.0 | Sell when % days to expiry reached |

**Key Insight:** This strategy buys the **UNDERLYING STOCK**, not options. Options flow is used purely as a sentiment signal.

**Original Results (US Market, 2017-2020):**
| Metric | Value |
|--------|-------|
| Starting Balance | $25,000 |
| Final Balance | $110,261 |
| Total Return | 341.04% |
| Annualized Return | 55.05% |
| Average Loss | -1.37% |
| Information Ratio | 2.361 |
| Biggest Drawdown | -31.38% |

> **Author's own warning:** Results include overfitting from grid search. Poor performance in 2017-2018. Most gains from COVID-19 volatility.

### 2.2 Reinforcement Learning Agents

**DQN Agent** (`model/dqn_agent.py`):
- State = encoded option flow features
- Action = 0 (BUY) or 1 (HOLD)
- Reward = portfolio return %
- Network: 2-layer MLP (128 hidden units)
- Epsilon-greedy exploration
- Target network with hard updates

**PPG Agent** (`model/ppg.py`):
- Phasic Policy Gradient (more stable than PPO)
- Actor-Critic architecture with auxiliary phase
- Used for learning from historical option flow

**Clustering Strategy** (`clustering.py`):
- Encodes option flow data into feature vectors
- Clusters with K-Means (n=50/100/250) or DBSCAN
- Trades only on the most profitable cluster
- Results show severe overfitting: 133% train return → 11.91% test return

---

## 3. Critical Assessment

### Strengths
1. **Real strategy with real backtest** — not a toy project
2. **Well-documented parameters** with grid-search defaults
3. **Multiple approach validation** — rules + RL + clustering
4. **Honest author disclosure** about overfitting and data bias
5. **Live trading capability** via Alpaca API

### Weaknesses
1. **Data dependency** — FlowAlgo subscription required (~$200+/month)
2. **US-only** — Alpaca and FlowAlgo don't support Indian markets
3. **Overfitting confirmed** — clustering shows massive train/test gap
4. **COVID bias** — majority of gains from a single black-swan event
5. **LONG only** — no short capability; one-sided market exposure
6. **False signal risk** — large puts could be hedges, not bearish bets

### Indian Market Adaptation Challenges
| Challenge | Severity | Mitigation |
|-----------|----------|------------|
| No FlowAlgo equivalent for NIFTY | HIGH | Build scraper for NSE option chain OI changes |
| Alpaca doesn't support India | HIGH | Use Zerodha/Kotak/ICICI Breeze APIs |
| SPY → NIFTY proxy | LOW | Use NIFTY 50 index or NIFTYBEES |
| Stock universe different | MEDIUM | NIFTY 50 constituents instead of S&P 500 |
| Currency/premium scaling | LOW | Convert $20K-$1M to ₹2L-₹1Cr range |

---

## 4. Auto-Extraction Failure Analysis

The `import_project` pipeline **completely failed** to extract this strategy:

| What Was Expected | What Was Extracted |
|-------------------|-------------------|
| Options flow counting | EMA crossover (WRONG) |
| Call/put ratio filtering | No indicators detected |
| +15% / -6% gain/loss exits | No exit conditions found |
| 10% position sizing | No position size found |
| SPY EMA filter | Ignored |

**Root Cause:** The `scanner.py` / `extractor.py` look for conventional technical indicator patterns (RSI, EMA, MACD). FlowAlgo uses a fundamentally different paradigm — event-driven options flow counting — which doesn't match any known pattern.

---

## 5. NIFTY Adaptation Design

### Concept: `algo4_flow_nifty`
Use our existing NSE option chain fetcher as a proxy for "options flow":

**Entry Logic:**
1. Fetch NIFTY option chain every 5 minutes
2. Track cumulative Call OI vs Put OI change per strike
3. If Call OI increase > Put OI increase for 3+ consecutive reads → BULLISH signal
4. Only enter if NIFTY spot > EMA-13
5. Only enter after 09:45 IST
6. Buy NIFTYBEES or closest ATM CE

**Exit Logic:**
1. +15% gain → exit
2. -6% loss → exit
3. EOD if neither hit

**Position Size:** 10% of capital = ₹20,000 per trade (on ₹200K capital)

### Implemented Proxy Backtest (Daily Bars, 1 Year)
Since we don't have historical options flow data, we created a simplified proxy:
- Signal = Previous day's Close > EMA-13 (trend following)
- Entry = Buy NIFTY at next day's Open
- Exit = Sell at that day's Close
- Position size = 10% of capital

**Actual Backtest Results (2025-05-25 to 2026-05-25):**
| Metric | Value |
|--------|-------|
| Total Trades | 118 |
| Win Rate | 39.0% |
| Final P&L | -₹2,786 |
| ROC | -1.39% |
| Sharpe | -3.15 |
| Max Drawdown | ₹2,729 |
| Max Consecutive Losses | 8 |
| Avg Win | ₹94 |
| Avg Loss | -₹99 |

> **Interpretation:** The proxy (simple EMA trend-following) is NOT profitable on NIFTY daily data. The original FlowAlgo's edge comes from **proprietary options flow data**, not the EMA filter. Without real-time OI/premium flow, this strategy has no edge.

---

## 6. Comparison vs Baseline

| Metric | FlowAlgo (Original US) | Algo4 Proxy (NIFTY) | Algo1 (RD-Straddle) | Algo2 (NTB-ScenB) | Algo3 (EMA-Cross) |
|--------|------------------------|---------------------|---------------------|-------------------|-------------------|
| Win Rate | ~55%* | 39.0% | 68.7% | 95.3% | 26.0% |
| Annualized Return | 55%* | -1.4% | ~9% | ~265% | -79% |
| Max Drawdown | -31.4%* | -1.4% | -2.4% | -16.6% | -129% |
| Sharpe | 2.36* | -3.15 | 6.40 | 16.75 | -4.33 |
| Data Cost | $200+/month | Free (yfinance) | Free (yfinance) | Free (yfinance) | Free (yfinance) |
| Broker Support | Alpaca (US only) | Any (India) | Any (India) | Any (India) | Any (India) |

> *FlowAlgo results are claimed/estimated from US backtest (2017-2020) and likely overfit.

---

## 7. Verdict

| Category | Score | Notes |
|----------|-------|-------|
| Code Quality | 8/10 | Clean, modular, well-structured |
| Strategy Validity | 6/10 | Real concept but overfit results |
| Indian Adaptability | 5/10 | Needs significant data layer rebuild |
| Risk Management | 7/10 | Fixed % stops, position sizing present |
| Documentation | 8/10 | Honest about limitations |
| **Overall** | **6.5/10** | Worth studying for the options-flow concept, but not directly usable |

**Recommendation:** Study the options-flow counting logic. Build a NSE option-chain-based adaptation (`algo4_flow_nifty`). Do NOT expect FlowAlgo-level returns — the data quality and market structure are different.

---
*Report generated by AlgoTrader import_project module + manual review*
