# Postmortem Report: gamma-scalping-main
**Generated:** 2026-05-25
**Algo ID:** imported_gamma_scalping_main_0525
**Manual Review:** YES — auto-extraction COMPLETELY FAILED

---

## 1. Executive Summary

| Attribute | Value |
|-----------|-------|
| **Project Type** | Production-Ready Live Trading System |
| **Author** | Alpaca Markets (official reference implementation) |
| **Broker** | Alpaca API (US equities + options) |
| **Strategy** | Gamma Scalping (market-neutral options) |
| **Complexity** | VERY HIGH — professional-grade |
| **Indian Market Fit** | MEDIUM-HIGH — concept works, needs NSE options + Indian broker |

---

## 2. What is Gamma Scalping?

**Core Concept:** Buy a straddle (long CE + long PE at same strike) → get positive Gamma → scalp the underlying by hedging delta continuously.

**The Race:**
1. **Gamma (Profit Engine):** You benefit from movement in EITHER direction
2. **Theta (Cost):** Every day, your options lose value to time decay
3. **Goal:** Scalp profits from price swings > cost of time decay

**You are betting that REALIZED volatility > IMPLIED volatility.**

---

## 3. Architecture Breakdown

### 3.1 System Components

| Component | File | Purpose |
|-----------|------|---------|
| **MarketDataManager** | `market/state.py` | Streams real-time quotes, filters bad spreads |
| **DeltaEngine** | `engine/delta_engine.py` | Calculates Greeks using QuantLib binomial tree |
| **TradingStrategy** | `strategy/hedging_strategy.py` | Decides when to hedge (delta threshold) |
| **PositionManager** | `portfolio/position_manager.py` | Executes trades via Alpaca API |
| **OptionsStrategy** | `strategy/options_strategy.py` | Finds and opens optimal straddle |

### 3.2 Key Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `HEDGING_ASSET` | `NVDA` | Underlying to trade |
| `HEDGING_DELTA_THRESHOLD` | 2.0 | Hedge when net delta exceeds +/- 2 shares |
| `STRATEGY_MULTIPLIER` | 1 | Number of straddles |
| `MIN_EXPIRATION_DAYS` | 30 | Min days to expiry |
| `MAX_EXPIRATION_DAYS` | 90 | Max days to expiry |
| `MIN_OPEN_INTEREST` | 100 | Liquidity filter |
| `THETA_WEIGHT` | 1.0 | Cost of theta in straddle scoring |
| `PRICE_CHANGE_THRESHOLD` | $0.05 | Recalculate delta after this price move |
| `HEARTBEAT_TRIGGER_SECONDS` | 5 | Recalculate delta every 5s minimum |

### 3.3 Straddle Selection Algorithm

1. Fetch all options expiring 30-90 days
2. Filter by open interest >= 100
3. Group by expiry + strike to find straddle pairs
4. Calculate ATM IV as baseline
5. Score each straddle: `gamma / (theta * THETA_WEIGHT + spread_cost)`
6. Pick highest score (most gamma per rupee of cost)

### 3.4 Delta Hedging Logic

```
Every price move > $0.05 OR every 5 seconds:
  1. Calculate straddle delta using QuantLib binomial tree
  2. Calculate portfolio net delta = options_delta + stock_position
  3. If |net_delta| > threshold:
       Trade shares to bring delta back to zero
       (Buy if delta negative, Sell if delta positive)
  4. Each scalp = profit from gamma capture
```

### 3.5 QuantLib Integration

- **Binomial tree model** (Cox-Ross-Rubinstein) for American options
- **Implied vol back-solve** from market prices
- **Greeks calculation:** Delta, Gamma, Theta
- Dividend yield from continuous approximation (warned as inaccurate near ex-div dates)

---

## 4. Code Quality Assessment

| Aspect | Score | Notes |
|--------|-------|-------|
| Architecture | 9/10 | Clean asyncio, queue-based decoupled design |
| Documentation | 9/10 | Extensive docstrings, README with architecture diagram |
| Error Handling | 8/10 | Try/catch around API calls, graceful shutdown |
| Type Hints | 7/10 | Partial, mostly in newer modules |
| Testing | 5/10 | No visible test suite |
| Production Readiness | 9/10 | Built by Alpaca for live trading |
| **Overall** | **8.5/10** | Best quality project analyzed so far |

---

## 5. Critical Assessment

### Strengths
1. **Real production system** by Alpaca (the broker itself)
2. **Sophisticated options math** with QuantLib binomial tree
3. **Real-time delta hedging** — not a toy backtest
4. **Async architecture** with queues — scalable and decoupled
5. **Straddle scoring function** balances gamma vs theta + execution cost
6. **Spread filtering** rejects illiquid quotes
7. **FIFO P&L tracking** for scalp trades
8. **Implied vol back-solve** from market prices

### Weaknesses
1. **US-only** — Alpaca API doesn't support Indian markets
2. **American options only** — NSE options are European (simpler pricing)
3. **Dividend model** uses continuous approximation (warned as inaccurate)
4. **No backtest results provided** — only live/paper trading
5. **Complexity** — requires understanding of Greeks and options pricing
6. **Capital intensive** — needs margin for long straddle + stock hedges

### Indian Market Adaptation

| Challenge | Severity | Mitigation |
|-----------|----------|------------|
| Alpaca doesn't support NSE | HIGH | Use Zerodha/Kotak/ICICI Breeze APIs |
| Need real-time option chain | HIGH | NSE cookie-based API (already working) |
| European vs American options | LOW | NSE options are European — simpler Black-Scholes |
| No NSE advance/decline for TRIN | LOW | Not needed for gamma scalping |
| Capital requirements | MEDIUM | ₹2-5L for 1 NIFTY straddle + hedges |
| Stamp duty + STT on hedges | MEDIUM | Each hedge trade costs ~0.1% — threshold must account for this |

---

## 6. Auto-Extraction Failure Analysis

The `import_project` pipeline **completely failed:**

| What Was Expected | What Was Extracted |
|-------------------|-------------------|
| Gamma scalping concept | "rsi_based" (WRONG) |
| Delta hedging logic | No indicators detected |
| Straddle selection scoring | Nothing |
| QuantLib binomial tree | Nothing |
| Real-time streaming architecture | Nothing |

**Root Cause:** The project has NO entry/exit in the traditional sense. It's a continuous delta-hedging engine, not a signal-based strategy. The scanner can't recognize this paradigm.

---

## 7. Indian Adaptation Concept: `algo6_gamma_scalp`

### What We'd Need to Build

**Data Layer:**
1. Real-time NIFTY option chain (already have NSE fetcher)
2. Live bid-ask for ATM CE + PE
3. Real-time NIFTY spot

**Pricing Layer:**
1. Black-Scholes (European is fine for NSE) instead of QuantLib binomial
2. IV back-solve from market prices
3. Greeks calculation: Delta, Gamma, Theta

**Strategy Layer:**
1. Buy ATM straddle (CE + PE) at market open
2. Calculate straddle delta every 5 seconds
3. Hedge delta by buying/selling NIFTY futures or NIFTYBEES
4. Hedge threshold: +/- 2 shares per straddle (or adapted for lot size)
5. Close straddle at EOD or when theta burn exceeds gamma profit

**Execution Layer:**
1. Zerodha/Upstox API for order placement
2. WebSocket for fill confirmations

### Estimated Performance (NIFTY)

| Scenario | Assumptions | Daily P&L (per straddle) |
|----------|-------------|--------------------------|
| High volatility day (NIFTY ±1%) | Gamma capture = ₹2000, Theta = -₹500 | +₹1500 |
| Normal day (NIFTY ±0.3%) | Gamma capture = ₹600, Theta = -₹500 | +₹100 |
| Low volatility day (NIFTY ±0.1%) | Gamma capture = ₹200, Theta = -₹500 | -₹300 |
| Flat day | Gamma capture = ₹0, Theta = -₹500 | -₹500 |

> **Key insight:** Needs average NIFTY daily move > ~0.5% to be profitable after theta. India VIX >= 18 is a good precondition.

---

## 8. Comparison vs Baseline

| Metric | Gamma Scalp (estimated NIFTY) | Algo1 | Algo2 | Algo3 | Algo4 | Algo5 |
|--------|-------------------------------|-------|-------|-------|-------|-------|
| Win Rate | N/A (not binary) | 68.7% | 95.3% | 26.0% | 39.0% | 63.2% |
| Daily P&L Range | -₹500 to +₹1500 | ±₹200 | ±₹200 | ±variable | ±₹115 | ±₹166 |
| Sharpe | ~1.0-1.5 (estimated) | 6.40 | 16.75 | -4.33 | -3.15 | 2.06 |
| Capital Required | ₹3-5L per straddle | ₹200K | ₹200K | ₹200K | ₹200K | ₹200K |
| Complexity | VERY HIGH | LOW | LOW | MEDIUM | LOW | LOW |
| Data Cost | Free (NSE) | Free | Free | Free | Free | Free |

> **Note:** Gamma scalping is fundamentally different from our existing algos. It's not about win rate — it's about continuously capturing small profits from volatility while hedging directional risk.

---

## 9. Verdict

| Category | Score | Notes |
|----------|-------|-------|
| Code Quality | 8.5/10 | Best project analyzed so far |
| Strategy Validity | 8/10 | Classic, proven market-neutral concept |
| Indian Adaptability | 6/10 | Needs full rebuild of execution layer |
| Risk Management | 8/10 | Delta hedging IS the risk management |
| Documentation | 9/10 | Excellent README with architecture diagram |
| **Overall** | **8/10** | Highest quality project; worth studying deeply for architecture |

**Recommendation:**
1. **Study the architecture** — queue-based async design is excellent
2. **Study the straddle scoring** — gamma/(theta+cost) is smart
3. **Do NOT attempt direct adaptation** without:
   - Real-time NSE option chain WebSocket
   - Black-Scholes Greeks calculator for European options
   - Zerodha/Upstox API integration
   - ₹3-5L dedicated capital
4. **This is a long-term project** — not a quick algo to add

---
*Report generated by AlgoTrader import_project module + manual review*
