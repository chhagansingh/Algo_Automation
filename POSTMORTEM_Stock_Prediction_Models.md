# POSTMORTEM — Stock-Prediction-Models-master
## Date: 2026-05-26
## Verdict: CONDITIONAL INTEGRATE (Daily) / PARK (Intraday)

---

## 1. PROJECT OVERVIEW

**Source:** `Stock-Prediction-Models-master.zip` (huseinzol05 / GitHub)
**Type:** Deep Learning + Reinforcement Learning research project for stock forecasting
**Contents:**
- 18 Deep Learning forecasting models (LSTM, GRU, Seq2Seq, Attention, CNN, etc.)
- 23 Trading agents (3 rule-based, 20 RL-based: Q-learning, Actor-Critic, Evolution Strategy, Neuro-evolution, Curiosity-driven, etc.)
- Stacking ensemble models (Autoencoder + RNN + ARIMA + XGB)
- Monte Carlo simulations
- JavaScript TensorFlow.js frontend

**Data:** US stocks only (GOOG, TSLA, FB, etc.) via CSV. No NIFTY. No India.
**Framework:** TensorFlow 1.x (deprecated — not installed, won't run on modern Python)
**Asset Class:** Equity-only. No options. No Greeks.
**Timeframe:** Daily bars only in original.

---

## 2. DUPLICATE CHECK

| Strategy | Duplicate? | Notes |
|----------|-----------|-------|
| Moving Average Agent | YES | algo3 (EMA Cross) — identical concept |
| Signal Rolling Agent | NO | Consecutive-close momentum — not in suite |
| Turtle Trading Agent | PARTIAL | Similar to algo7 (Dual Thrust) but simpler |
| ABCD Strategy Agent | PARTIAL | Similar to Algo-Trading-main bullish swing |
| DL/RL Agents | N/A | Equity-only, require retraining — not directly comparable |
| ML Classifier (RF) | NO | First ML-based strategy in suite |

---

## 3. ADAPTATION & BACKTEST METHODOLOGY

Since the original project is TF 1.x based and equity-only, we extracted and adapted the **3 most promising concepts** for NIFTY options:

1. **Signal Rolling** — Buy CE after N consecutive up closes, PE after N consecutive down closes. Exit: 1:2 R:R, 50% SL, max hold.
2. **Turtle Trading** — Buy CE on break above N-period high, PE on break below N-period low. Same exit rules.
3. **ML Direction Classifier** — RandomForest on technical indicators (RSI, MACD, BB, returns, volatility) trained on rolling window to predict next-bar direction. Buy CE if up, PE if down.

**Backtest Parameters:**
- Capital: ₹2,00,000
- Position: Fixed 1 lot (50 qty) per trade
- Option pricing: Black-Scholes proxy (IV=0.13, r=0.05)
- Timeframes: Daily (2018-2025), 1H (2024-2026)

---

## 4. BACKTEST RESULTS

### Daily Backtest (7+ Years: 2018–2025)

| Strategy | Trades | WR% | P&L | ROC% | MaxDD | Sharpe |
|----------|--------|-----|-----|------|-------|--------|
| **SignalRolling(d=3)** | 319 | **48.6%** | **+₹7.21L** | **360.5%** | ₹16,774 (8.4%) | **7.06** |
| SignalRolling(d=5) | 104 | 48.1% | +₹2.09L | 104.3% | ₹32,646 (16.3%) | 3.30 |
| Turtle(w=10) | 253 | 47.8% | +₹5.21L | 260.3% | ₹12,306 (6.2%) | 5.78 |
| Turtle(w=20) | 184 | 45.7% | +₹2.94L | 147.0% | ₹17,976 (9.0%) | 4.22 |
| **ML-RF(lb=60)** | 261 | **48.7%** | **+₹6.54L** | **327.0%** | ₹20,923 (10.5%) | **6.41** |

### 1H Intraday Backtest (~1 Year: 2024–2026)

| Strategy | Trades | WR% | P&L | ROC% | MaxDD | Sharpe |
|----------|--------|-----|-----|------|-------|--------|
| SignalRolling(d=3) | 381 | 35.4% | +₹1.46L | 72.8% | ₹72,776 (36.4%) | 1.36 |
| SignalRolling(d=5) | 110 | 30.9% | -₹34K | -17.0% | ₹56,813 (28.4%) | -0.82 |
| Turtle(w=10) | 316 | 32.0% | +₹32K | 15.8% | ₹1,16,604 (58.3%) | 0.31 |
| Turtle(w=20) | 231 | 31.6% | +₹13K | 6.4% | ₹1,24,391 (62.2%) | 0.14 |
| **ML-RF(lb=60)** | 153 | **35.9%** | **+₹1.27L** | **63.5%** | ₹22,070 (11.0%) | **1.67** |

---

## 5. ANALYSIS

### Daily Performance
All 3 strategies pass every threshold on daily timeframe:
- Sharpe > 1.5 ✅
- WR > 45% ✅ (for d=3, w=10, ML-RF)
- Positive P&L ✅
- MaxDD < 30% ✅

**Caveat:** Daily backtest covers NIFTY's strong bull run (10,000 → 25,000). Strategies have slight long bias. Performance in sideways/bear market is untested.

### Intraday Performance
Only **ML-RF** shows positive Sharpe (1.67) with controlled MaxDD (11%). However:
- **WR = 35.9%** — fails the 45% threshold ❌
- Simple rule-based strategies (SignalRolling, Turtle) fail on 1H due to market noise
- MaxDD for rule-based strategies is catastrophic (36-62%)

### Key Issues Found
1. **Original project is TF 1.x** — cannot run without compatibility hacks or full rewrite
2. **20+ RL agents** — require hours/days of GPU training on NIFTY data. Not practical for quick evaluation
3. **All original agents are equity-only** — no option pricing, no Greeks, no expiry management
4. **ML model requires retraining every bar** — computationally expensive for live trading (~2-5 min per prediction on CPU)
5. **BS proxy limitations** — fixed IV doesn't capture intraday IV crush/expansion
6. **Intraday noise** — simple breakout/momentum strategies struggle on 1H NIFTY

---

## 6. PHASE 4 VERDICT

### RECOMMENDATION: CONDITIONAL INTEGRATE (Daily) + PARK (Intraday)

**For DAILY / WEEKLY OPTIONS:**
| Strategy | Verdict | Rationale |
|----------|---------|-----------|
| **SignalRolling(d=3)** | **INTEGRATE** | Best daily performer. Sharpe 7.06, WR 48.6%, MaxDD 8.4%. Clean, simple, no training required. |
| **ML-RF(lb=60)** | **INTEGRATE** | First ML algo in suite. Sharpe 6.41, WR 48.7%. Adds ML diversity. |
| Turtle(w=10) | PARK | Similar to algo7. Slightly inferior to SignalRolling. |
| Turtle(w=20) | PARK | Lower trade count, lower Sharpe. |
| SignalRolling(d=5) | PARK | Too few trades (104 in 7 years = ~15/year). |

**For INTRADAY (1H / 5M / 15M):**
| Strategy | Verdict | Rationale |
|----------|---------|-----------|
| ML-RF | **PARK** | Best intraday Sharpe (1.67) and MaxDD (11%) but WR 35.9% fails threshold. Needs: (1) better feature engineering, (2) gradient boosting instead of RF, (3) walk-forward training instead of per-bar retrain. |
| SignalRolling | DISCARD | 36% MaxDD exceeds threshold. |
| Turtle | DISCARD | 58-62% MaxDD, Sharpe < 0.5. |

**Original 20 RL Agents:** NOT EVALUATED — require full TF 1.x rewrite + weeks of NIFTY retraining. Not viable for short-term integration.

---

## 7. INTEGRATION PLAN (If Approved)

**algo13: SignalRollingDaily**
- File: `algos/algo13_signal_rolling.py`
- Class: `Algo13SignalRolling`
- Logic: Consecutive 3-day momentum on NIFTY daily → buy ATM CE/PE
- Exit: 50% SL / 1:2 target / 5-day max hold
- Backtest: 319 trades, 48.6% WR, +₹7.2L, Sharpe 7.06, 8.4% MaxDD

**algo14: ML-RF Daily**
- File: `algos/algo14_ml_rf.py`
- Class: `Algo14MLRF`
- Logic: RandomForest on technicals trained on rolling 60-day window → direction prediction → ATM CE/PE
- Exit: Same as above
- Backtest: 261 trades, 48.7% WR, +₹6.5L, Sharpe 6.41, 10.5% MaxDD
- **Note:** Live inference requires pre-trained model + daily retraining pipeline

---

## 8. RISK DISCLOSURE

- Daily strategies were tested during NIFTY's strongest bull market in history (2018-2025)
- Untested in prolonged bear/sideways markets
- ML-RF may overfit to training window — requires regularization and out-of-sample validation
- BS proxy is approximate; live option premiums will differ
- Both strategies trade directionally — not market-neutral

---

*Report generated: 2026-05-26*
*Backtest script: /tmp/spm_nifty_backtest_v2.py*
