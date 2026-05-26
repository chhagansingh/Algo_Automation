# POSTMORTEM REPORT — Algo-Trading-main

**Analysis Date:** May 26, 2026
**Analyst:** Devin (AI Engineering Assistant)
**Project Path:** `/Users/com/Desktop/R&D/Algo-Trading-main/Algo-Trading-main/`
**Project Type:** Intraday bullish swing option buying strategy (Angel One SmartAPI)
**Compared Against:** AlgoTrader algo1-algo12

---

## 1. Executive Summary

Algo-Trading-main implements an **intraday bullish swing pattern** strategy for NIFTY 50 Call Options using Angel One's SmartAPI. The strategy detects a specific price structure (L1 → H1 → A → B → C → D) and buys CE on breakout above D with a 1:2 risk-reward setup.

**Core Problem:** The strategy is fundamentally designed for **intraday minute-level data**. On daily bars, the swing detection is noisy, position sizing becomes erratic, and the 80% max drawdown far exceeds acceptable risk limits.

**Verdict:** PARKED — Positive P&L concept but requires intraday data and drawdown control to be viable.

---

## 2. Project Architecture Overview

### 2.1 Directory Structure

```
Algo-Trading-main/
├── brokers/
│   └── angelone.py          # Angel One SmartAPI broker client
├── config/
│   └── settings.py          # API keys, lot size, risk limits
├── data/
│   └── ohlcv.py             # OHLCV data fetching
├── models/
│   └── option.py            # OptionData model with Greeks
├── strategies/
│   └── bullish_swing.py     # Main strategy: L1→H1→A→B→C→D pattern
├── utils/
│   └── helpers.py           # Utility functions
│   └── logger.py            # Logging
├── main.py                  # Entry point
└── README.md
```

### 2.2 Technology Stack

| Component | Technology |
|-----------|-----------|
| Broker API | Angel One SmartAPI |
| Auth | pyotp TOTP |
| Data | Live ticks via SmartAPI |
| Option Selection | Greeks-based (Delta, Theta, IV, Vega) |
| Order Type | Bracket Order (BO) intraday |
| Lot Size | 75 (BNF or NIFTY) |

---

## 3. Strategy Analysis

### 3.1 Original Strategy (Intraday)

**Pattern Detection (L1 → H1 → A → B → C → D):**
```
L1 = First swing low (starting point)
H1 = Swing high after L1
A  = Swing low after H1 (must be > L1)
B  = Swing low after A (must be > A) 
C  = Pullback low after B (between B and D, > B)
D  = Highest high between B and C
```

**Entry:** Buy CE when price breaks above D + 0.05 buffer
**Stop Loss:** C - 0.05 buffer
**Target:** Entry + 2 × Risk (1:2 R:R)
**Position Sizing:** Greeks-based optimal strike selection
**Product:** INTRADAY (MIS) bracket order

### 3.2 India Adaptation (Daily Bars)

Since the original is intraday and we only have daily NIFTY data:
- **Swing detection:** 3-bar rolling window, 1-bar lag for confirmation
- **Pattern:** Higher lows sequence (L1 < A < B) + breakout above D
- **Entry:** Next-day Open (if High ≥ D)
- **Option:** ATM CE, 7-day expiry proxy via Black-Scholes
- **Exit:** Target hit, SL hit, or 10-day max hold
- **Position size:** 5% of capital per trade

**FIX APPLIED:** Proper 1-bar lag for swing confirmation to avoid look-ahead bias.

---

## 4. Backtest Results

**Period:** Jan 2022 → May 2025 (NIFTY daily via yfinance)
**Data Source:** yfinance `^NSEI` (no auth required)

| Metric | Value |
|--------|-------|
| Total Trades | 57 |
| Wins | 26 |
| Losses | 31 |
| Win Rate | **45.6%** |
| Final P&L | **+₹2,09,096** |
| ROC | **+104.5%** |
| Max Drawdown | **₹1,60,142** (80% of capital) |
| Sharpe | **0.31** |
| Max Consecutive Losses | 10 |
| Avg Win | ₹26,794 |
| Avg Loss | -₹15,728 |

### Monthly Breakdown (Sample)

| Month | P&L |
|-------|-----|
| 2022-10 | +₹1,39,908 |
| 2023-06 | +₹1,60,339 |
| 2022-11 | -₹45,701 |
| 2024-07 | -₹37,148 |

---

## 5. Issues Found

### A. Temporal Mismatch (CRITICAL)
The strategy is built for **intraday minute-level** swing detection. Daily bars:
- Compress multiple intraday swings into a single bar
- Cause delayed entries (breakout on daily bar = already moved significantly)
- Make the 1:2 R:R unrealistic (daily range often exceeds target in one bar)

### B. Excessive Drawdown (CRITICAL)
80% MaxDD means the strategy would have wiped out most of the capital at its worst point. This is far above the 30% threshold. The 10 consecutive losses streak is dangerous.

### C. Fixed IV Assumption
Using BASE_IV = 0.13 for all entries doesn't capture real market IV. In high IV environments, option prices are higher but also decay faster.

### D. No Regime Filter
The strategy enters in ALL market conditions — trending up, trending down, and ranging. It should only trade in confirmed uptrends.

### E. Broker Auth Dependency
Original requires Angel One SmartAPI with TOTP. Backtest bypassed this with yfinance + BS pricing.

---

## 6. Verdict

### Decision Criteria Check

| Criteria | Threshold | Result |
|----------|-----------|--------|
| Sharpe ≥ 1.5 | 1.5 | 0.31 ❌ |
| Win Rate ≥ 45% | 45% | 45.6% ✅ |
| Positive P&L | > 0 | +₹2.09L ✅ |
| MaxDD < 30% | 30% | 80% ❌ |

**Result: DOES NOT QUALIFY FOR INTEGRATE**

---

## 7. Recommendation: PARKED

**Why PARKED and not DISCARD:**
- Positive P&L (+104% ROC) shows the concept has merit
- 45.6% WR is at the threshold
- Pattern-based entry is a novel approach not present in algo1-algo12
- Intraday version might perform very differently

**To revive this strategy, the following are REQUIRED:**

1. **Intraday data (5m or 15m)** — Daily bars fundamentally break the pattern
2. **Drawdown control** — Add max daily loss limit (2%), max consecutive loss limit (3), or portfolio-level stop
3. **Trend filter** — Only trade when NIFTY > 20 EMA (or ADX > 25)
4. **Dynamic IV** — Use India VIX or option chain IV instead of fixed 0.13
5. **Position sizing fix** — Current sizing grows with equity but doesn't shrink after losses; add Kelly or fixed fractional
6. **Time-based exit** — Close by 3:15 PM IST regardless of target/SL for intraday

**Without intraday data, this strategy cannot be properly validated.**

---

## 8. Security Assessment

**PASS** — No hardcoded credentials. `config/settings.py` uses empty strings for API_KEY, USERNAME, PASSWORD, TOTP_KEY. User must fill these in.

---

## 9. Code Quality Assessment

### Strengths
- Clean class-based structure (`BullishSwingStrategy`)
- Greeks-based option selection (`OptionData.select_optimal_strike`)
- Comprehensive logging and CSV order history
- Swing detection logic is clearly documented

### Weaknesses
- `refresh_option_greeks()` has a placeholder implementation (not actually fetching Greeks in the provided code)
- No backtesting module — strategy is live-only
- Swing detection uses 1-bar lookahead in original (fixed in our adaptation)
- No risk management beyond per-trade SL

---

*Report generated by Devin on May 26, 2026*
