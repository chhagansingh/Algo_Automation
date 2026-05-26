# Postmortem Report: fully-automated-nifty-options-trading-main
**Generated:** 2026-05-25
**Manual Review:** YES — real Indian NIFTY options trading bot

---

## 1. Executive Summary

| Attribute | Value |
|-----------|-------|
| **Project Type** | Fully Automated Live Trading Bot |
| **Author** | Srikar Kodakandla (kodakandlasrikar99@gmail.com) |
| **Broker** | Zerodha Kite (via Selenium) + Fyers (data) |
| **Strategy** | SuperTrend + ADX → Credit Spread on NIFTY options |
| **Complexity** | HIGH — 39K lines across 59 files |
| **Indian Market Fit** | **EXCELLENT** — built specifically for NIFTY |

---

## 2. Strategy Breakdown

### Core Concept

**SuperTrend + ADX** on 5-minute NIFTY chart → **Credit Spread** construction.

### Entry Logic

| Signal | Action | Spread Construction |
|--------|--------|---------------------|
| SuperTrend turns UP (bullish) | Sell ATM CE + Buy OTM CE | Hedge = `risk` points above |
| SuperTrend turns DOWN (bearish) | Sell ATM PE + Buy OTM PE | Hedge = `risk` points below |

**Example:** NIFTY at 24000, risk=500:
- SuperTrend UP → Sell 24000 CE + Buy 24500 CE (₹500 spread)
- SuperTrend DOWN → Sell 24000 PE + Buy 23500 PE (₹500 spread)

### Key Parameters (Author's Optimized Values)

| Parameter | Value | Description |
|-----------|-------|-------------|
| `timeframe` | 5min | Chart resolution |
| `period` | 15 | SuperTrend ATR period |
| `multiplier` | 14.2 | SuperTrend ATR multiplier |
| `risk` | 500 | Strike spread width (50-1000) |
| `target_price` | 0.95 | Exit at 95% of max profit |
| `qty` | 50 | Lot size |

### Risk Parameter Explained

The `risk` parameter controls the width of the credit spread:
- **risk=50** (lowest risk): Sell 24000 CE, Buy 24050 CE → max loss = ₹50/lot
- **risk=500**: Sell 24000 CE, Buy 24500 CE → max loss = ₹500/lot
- **risk=1000** (highest risk): Sell 24000 CE, Buy 25000 CE → max loss = ₹1000/lot

Higher risk = wider spread = more premium collected but higher max loss.

### Exit Logic

1. **Target Exit:** When option price drops to 95% of entry premium (collect 95% of max profit)
2. **Trend Reversal:** Close position when SuperTrend flips direction
3. **Expiry Handling:** Roll to next expiry before weekly expiry

### ADX Filter

ADX > threshold used to confirm trend strength before entering. Weak trends (ADX < 20) are avoided.

---

## 3. Architecture

| Component | File | Purpose |
|-----------|------|---------|
| **Strategy Engine** | `kite_strategy.py` | Main trading loop, signal generation |
| **Execution** | `kite_fun.py` | Selenium-based Zerodha order placement |
| **Data** | `login_fyers.py` | Fyers API for historical 5min data |
| **Indicators** | `common/indicator.py` | SuperTrend, ATR, EMA, MACD |
| **Backtest** | `common/backtestingsuper.py` | Backtesting library optimization |
| **Brokers** | `zerodha_own_api.py` | Zerodha Kite wrapper |

### Data Flow

```
Fyers API → 5min NIFTY data → SuperTrend/ADX calculation → Signal
                                        ↓
Zerodha Kite (Selenium) ← Order placement ← Credit spread construction
```

---

## 4. Backtested Parameters

The author performed rigorous backtesting on NIFTY 5min data to find optimal SuperTrend values:

| Parameter | Backtest Optimal | Live Used |
|-----------|-----------------|------------|
| period | 147 (optimized) | 15 |
| multiplier | 13.9 (optimized) | 14.2 |

> Note: The live parameters (15, 14.2) differ from backtest optimal (147, 13.9). The author may have adjusted for practical execution concerns.

---

## 5. Code Quality Assessment

| Aspect | Score | Notes |
|--------|-------|-------|
| Strategy Logic | 7/10 | Clear SuperTrend + ADX + spread concept |
| Code Organization | 4/10 | Monolithic files, duplicated code, spaghetti |
| Error Handling | 3/10 | Bare except clauses, no graceful degradation |
| Security | 2/10 | Hardcoded credentials in source files |
| Documentation | 4/10 | README explains concept but no inline docs |
| Testing | 2/10 | Minimal test coverage |
| Production Readiness | 3/10 | Selenium-based execution is fragile |
| **Overall** | **4/10** | Good strategy, poor code quality |

---

## 6. Critical Issues

1. **Hardcoded credentials** — Zerodha username/password/pin in source code
2. **Selenium-based execution** — Fragile, breaks on UI changes, slow
3. **No risk management** — No position sizing based on account value
4. **Bare except clauses** — `except: pass` everywhere = silent failures
5. **Deprecated** — Fyers API v2 no longer supported
6. **No stop loss** — Only target exit at 95%, no hard SL on spread
7. **Duplicate code** — Same functions in `kite_strategy.py` and `kite_fun.py`

---

## 7. India Adaptation: `algo6_supertrend_spread`

### Strategy Design

**Entry:**
1. Calculate SuperTrend(15, 14.2) on NIFTY daily data
2. When trend flips from down→up → Sell ATM CE (credit spread)
3. When trend flips from up→down → Sell ATM PE (credit spread)
4. ADX > 20 filter for trend confirmation

**Spread Construction (simplified for daily backtest):**
- Instead of buying hedge leg, simulate credit spread P&L
- For daily bars: premium decay ≈ distance from strike to close

**Exit:**
- EOD (daily bars can't track 95% target intraday)
- Or trend reversal

**Note:** True credit spread backtesting requires intraday option data. Our daily approximation will underestimate the edge.

---

## 8. Comparison vs Baseline

| Metric | SuperTrend Spread (estimated) | Algo1 | Algo2 | Algo3 | Algo4 | Algo5 |
|--------|------------------------------|-------|-------|-------|-------|-------|
| Strategy | Credit spread on trend | Short straddle | Short straddle | EMA cross | EMA trend | VIX mean-rev |
| Win Rate | ~55-60%* | 68.7% | 95.3% | 26.0% | 39.0% | 63.2% |
| Max DD | ~15-20%* | -2.4% | -16.6% | -129% | -1.4% | -0.4% |
| Sharpe | ~1.0-1.5* | 6.40 | 16.75 | -4.33 | -3.15 | 2.06 |
| Complexity | HIGH | LOW | LOW | MEDIUM | LOW | LOW |

> *Estimated based on similar SuperTrend strategies. True backtest requires 5min option chain data.

---

## 9. Verdict

| Category | Score | Notes |
|----------|-------|-------|
| Strategy Concept | 8/10 | SuperTrend + ADX + credit spread is sound |
| Code Quality | 4/10 | Poor — spaghetti, hardcoded creds, fragile Selenium |
| Indian Adaptability | 9/10 | Built for NIFTY, exactly our market |
| Risk Management | 4/10 | Spread width only, no position sizing |
| Production Readiness | 3/10 | Selenium breaks, deprecated APIs |
| **Overall** | **5.5/10** | Good strategy buried in poor code |

**Recommendation:**
1. **Extract the strategy concept** — SuperTrend(15, 14.2) + ADX on 5min NIFTY → credit spread
2. **Create `algo6_supertrend_spread`** with clean code
3. **Use our NSE fetcher** instead of Fyers/Zerodha Selenium
4. **Add proper risk management** — position sizing, hard SL
5. **Delete original zip** — code quality too poor to reuse directly

---
*Report generated by manual review*
