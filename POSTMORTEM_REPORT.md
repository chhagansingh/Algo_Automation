# Postmortem Report: Nifty Options Trading AI

**Project:** Nifty Options Trading AI  
**Files Analyzed:** `backtest_strategy.py`, `options_screener.py`, `requirements.txt`, `README.md`  
**Report Date:** 2026-05-25  
**Status:** R&D / Pre-Production  

---

## 1. Executive Summary

This project consists of two components:

| Component | Purpose | Status |
|---|---|---|
| `backtest_strategy.py` | Historical backtest of a short-straddle/strangle strategy on Nifty | Structurally incomplete — significant logic flaws |
| `options_screener.py` | Streamlit live screener fetching NSE option chain data | Functionally fragile — API and signal logic issues |

The headline numbers in the README (60.89% win rate, ₹10,800 P/L) are **mathematically consistent** with the code but are built on **unrealistic assumptions** that would not hold in live trading. The backtest as written cannot be used to validate any live strategy without major rework.

---

## 2. Component 1: `backtest_strategy.py` — Deep Analysis

### 2.1 What the Strategy Intends to Do

Sell ATM (or ATM+1% OTM) Call and Put options every day when Nifty's intraday range is less than 1%. Collect a flat ₹100 per leg per day as profit. Exit at a flat ₹100 loss per leg if the market moves more than 1%.

This is conceptually a **short straddle / short strangle** strategy, also known as a **theta decay / premium selling** strategy.

### 2.2 Verified Metrics (from README)

The README states results from a historical run:

| Metric | Value |
|---|---|
| Total Trades | 248 |
| Winning Trades | 151 |
| Losing Trades | 97 |
| Win Rate | 60.89% |
| Final P/L | ₹10,800 |

**Math verification:** (151 × ₹200) + (97 × −₹200) = **₹10,800 ✓** — the numbers are internally consistent.

### 2.3 Derived Risk Metrics (based on stated stats)

| Risk Metric | Value | Assessment |
|---|---|---|
| Annualized Sharpe Ratio | ~3.82 | Unrealistically high — artifacts of binary P/L |
| Max Drawdown (estimated) | ~₹1,400 – ₹4,000 | Understated due to binary loss cap |
| Calmar Ratio | ~8.3 | Inflated for same reason |
| Avg Daily P/L | ₹46.77 | Low absolute return vs capital required |
| Payoff Ratio | 1:1 | No edge; purely win-rate dependent |
| Expected Value per Trade | ₹46.77 | Positive but unreliable (see bugs) |

> **Key insight:** Because both profit and loss are capped at ₹100/leg, the Sharpe ratio is artificially inflated. In reality, short options have asymmetric risk — small frequent gains vs large occasional losses.

---

## 3. Critical Bugs in `backtest_strategy.py`

### BUG 1 — Both Legs Are Identical (Severity: HIGH)

```python
data['Sell Call P/L'] = np.where(data['Daily Move %'] < 1, 100, -100)
data['Sell Put P/L']  = np.where(data['Daily Move %'] < 1, 100, -100)
```

Both the Call and Put P/L use **exactly the same condition and same values**. In a real short straddle:
- On a big UP move → CE loses, PE profits (partially)
- On a big DOWN move → PE loses, CE profits (partially)

The legs offset each other's risk. The code treats both legs as losing simultaneously on any move > 1%, which overstates losses and eliminates the natural hedge.

**Fix:** Model each leg separately based on direction of move, option premium, and delta.

---

### BUG 2 — Every Day is Traded, Including High-Volatility Days (Severity: HIGH)

```python
# Strategy condition: only trade when move < 1%
data['Sell Call P/L'] = np.where(data['Daily Move %'] < 1, 100, -100)
```

The strategy **never skips a trade**. On high-volatility days (move ≥ 1%), it records a ₹200 loss. A real implementation should:
- Only enter a position when forecasted volatility is low
- Skip or hedge on days with macro events (RBI, Budget, earnings)

The current code is not a conditional entry strategy — it is a "trade every day and lose on bad days" strategy. A strict conditional version would have:
- Wins: days where move < 1% (enter + profit)
- No trade: days where move ≥ 1% (simply skip)
- Result: much fewer trades but no losing days

---

### BUG 3 — Intraday Range % is a Proxy, Not a Real Volatility Signal (Severity: MEDIUM)

```python
data['Daily Move %'] = ((data['High'] - data['Low']) / data['Open']) * 100
```

This measures intraday high-low range as % of open. This is **not the same as**:
- Implied Volatility (IV) — what options are priced at
- Realized volatility — close-to-close standard deviation
- ATR (Average True Range) — accounts for gaps

A proper options-selling strategy should use **India VIX** or the **IV of the specific option** as the entry filter, not intraday range.

---

### BUG 4 — Flat ₹100 P/L Ignores Reality (Severity: HIGH)

Real Nifty options trading involves:

| Factor | Ignored in Code | Real Value |
|---|---|---|
| Lot size | Yes | 25 units per lot |
| Premium received | Yes | ₹80–₹300+ per ATM option |
| Max loss per contract | Capped at ₹100 | Theoretically unlimited (naked short) |
| Margin requirement | Not modeled | ₹1–1.5 lakh per lot |
| ROC per trade | Not calculated | ~0.007–0.02% on capital |

The flat ₹100 target and ₹100 stop-loss is an oversimplification that:
1. Does not reflect actual premium levels
2. Does not reflect tail risk (a 3% gap-down could lose ₹5,000+ per lot, not ₹100)

---

### BUG 5 — No Transaction Costs or Slippage (Severity: MEDIUM)

Each trade involves 4 legs (sell CE, sell PE, buy back CE, buy back PE). Approximate real costs:

| Cost Item | Amount per Lot |
|---|---|
| Brokerage (flat) | ₹40–₹80 |
| STT on exercise/sell | ₹15–₹50 |
| Exchange + SEBI charges | ₹10–₹20 |
| Slippage (2–5 points) | ₹50–₹125 |
| **Total per round trip** | **~₹115–₹275** |

At ₹200 avg profit per winning day, costs eat 57–137% of gross profit. After costs, the strategy is likely **break-even or negative**.

---

### BUG 6 — No Data File Included; No Validation (Severity: MEDIUM)

```python
file_path = 'data/NIFTY_data.csv'
data = pd.read_csv(file_path)
```

The `data/` directory does not exist in the repo. The script will crash immediately for any new user. There is:
- No sample data file
- No data download script
- No fallback or mock data for testing
- No validation of required columns beyond a simple `if 'Date' in data.columns`

---

### BUG 7 — README Terminology Inconsistency (Severity: LOW)

The README says "Sell ATM+1% Call and Put Options" but in options terminology:
- **ATM** = At-the-Money (strike = spot)
- **ATM+1%** = 1% Out-of-the-Money (OTM) Call / Put

If you are selling OTM options, it is a **short strangle**, not a short straddle. The distinction matters for:
- Premium received (lower for OTM)
- Win probability (higher for OTM)
- Breakeven range (wider for OTM)

The code does not model strike selection at all, so the README description cannot be verified.

---

## 4. Component 2: `options_screener.py` — Deep Analysis

### 4.1 What It Does

A Streamlit dashboard that:
1. Fetches live NSE option chain for NIFTY or BANKNIFTY
2. Screens for "BUY CE" or "BUY PE" signals based on price patterns
3. Displays filtered results and allows CSV export
4. Auto-refreshes at a user-selected interval (15–120 seconds)

### 4.2 Signal Logic Analysis

**CE BUY Signal:**
```python
ce_signal = (ce.get('open') == ce.get('low')) and (ce.get('previousClose') < strike)
```

| Condition | Interpretation | Issue |
|---|---|---|
| `open == low` | Option opened at day's low (bullish — can only go up) | Valid pattern for intraday momentum |
| `previousClose < strike` | Previous close of the option was below strike price | **Wrong metric** — should compare spot price to strike |

For a CE (Call), what matters is whether **spot > strike** (ITM) or spot momentum. Comparing the option's `previousClose` to `strike` conflates option price with moneyness.

**PE BUY Signal:**
```python
pe_signal = (pe.get('open') == pe.get('high')) and (pe.get('previousClose') > strike)
```

| Condition | Interpretation | Issue |
|---|---|---|
| `open == high` | Option opened at day's high (bearish — can only go down) | Valid pattern for intraday momentum |
| `previousClose > strike` | Previous option close > strike | **Same issue** — should use spot vs strike |

Additionally, for PEs: if `previousClose > strike` this means OTM put option had a price above the strike, which is only possible for deep ITM puts with strike values near zero. This condition is nearly always false.

**Signal Quality Assessment:** The signals would fire very infrequently and mostly due to data anomalies (e.g., illiquid strikes where open = low/high due to no mid-day trading, not momentum).

---

### 4.3 NSE API Reliability Issues (Severity: HIGH)

```python
session = requests.Session()
session.get("https://www.nseindia.com", headers=headers)
response = session.get(url, headers=headers)
```

**Known problems with this approach:**

1. **Single cookie initialization** — NSE requires a valid browser session. One GET to the homepage is often insufficient; multiple sequential requests are needed to build valid cookies.

2. **No timeout** — `requests.get()` can hang for 30–60 seconds if NSE is slow or blocking.

3. **No retry logic** — On 401/403/429, the app silently returns empty data (safe fallback exists but no user notification of why).

4. **Rate limiting** — Auto-refresh at 15 seconds = 4 requests/minute. NSE actively blocks IPs that make frequent automated requests.

5. **No User-Agent rotation or proxy** — NSE detects and blocks static user-agent strings.

6. **No expiry date filtering** — The option chain returns all expiries mixed together. Near-expiry and far-expiry options have very different behavior; they should be separated.

---

### 4.4 Architecture Issues in `options_screener.py`

| Issue | Severity | Description |
|---|---|---|
| `symbol` used from outer scope in `fetch_option_chain()` | MEDIUM | Should be passed as a parameter for clarity and testability |
| No OI / Volume / IV columns | HIGH | These are the 3 most important metrics for options screening |
| No ATM row highlight | MEDIUM | Users cannot identify which strikes are near current spot |
| No expiry date column/filter | HIGH | All expiries mixed; weekly vs monthly options behave differently |
| No error state for network failure | MEDIUM | Empty table appears without explanation |
| No logging | LOW | Hard to debug in production |

---

## 5. What's Missing for a Production-Ready System

### 5.1 Backtest Engine Gaps

| Missing Feature | Why It Matters |
|---|---|
| Option premium modeling (Black-Scholes / market data) | Current flat ₹100 is fictional |
| Greeks tracking (Delta, Theta, Vega, Gamma) | Essential for understanding risk over time |
| IV/VIX filter for entry | Avoid selling cheap options |
| Stop-loss based on spot move, not flat amount | Realistic risk management |
| Portfolio-level margin and capital tracking | To compute real ROC |
| Transaction costs model | 57–137% cost drag identified |
| Out-of-sample / walk-forward testing | Avoid overfitting |
| Rolling window analysis | Understand regime dependency |

### 5.2 Screener Gaps

| Missing Feature | Why It Matters |
|---|---|
| Open Interest (OI) and OI change | Key indicator of institutional positioning |
| IV (Implied Volatility) per strike | Critical for premium selling decisions |
| IV Percentile / IV Rank | Context for whether IV is high or low |
| PCR (Put-Call Ratio) | Market sentiment indicator |
| ATM/ITM/OTM classification | Basic orientation for any user |
| Max Pain strike | Important for expiry-week strategies |
| Expiry date selector | Can't mix weekly and monthly |
| Spot price display | Not shown anywhere in the UI |

---

## 6. Positive Observations

1. **Clean code structure** — Both files are well-organized and readable for their scope.
2. **Safe API fallback** — `options_screener.py` returns empty data on API failure instead of crashing.
3. **Correct math** — The P/L arithmetic and cumulative calculation are error-free.
4. **Good UI foundation** — Streamlit with auto-refresh, CSV download, and index selector is a solid starting point.
5. **Strategy concept is sound** — Short-straddle/strangle theta decay is a legitimate and widely-used strategy; the idea just needs proper implementation.

---

## 7. Recommendations for Integration into Other Algo Trading Projects

### Priority 1 — Fix Before Any Live Use

- [ ] Remove flat ₹100 P/L assumption; use actual option premium from historical data (NSE Bhavcopy)
- [ ] Add transaction cost model (minimum ₹150 per round-trip per lot)
- [ ] Make backtest conditional entry-only (only trade on days where movement forecast is < 1%, skip otherwise)
- [ ] Add India VIX filter: only sell options when VIX is between 12–20 (not during panic)
- [ ] Fix signal logic in screener: use spot price vs strike for moneyness check
- [ ] Add NSE session cookie refresh mechanism with retry logic

### Priority 2 — Enhance Before Scaling

- [ ] Add lot-size-aware P/L (Nifty = 25, BankNifty = 15)
- [ ] Add max loss per trade based on a percentage of margin (e.g., 2× premium received)
- [ ] Add expiry selection in screener (weekly 0DTE, next week, monthly)
- [ ] Add OI, OI change, IV, and PCR columns to screener
- [ ] Add walk-forward or out-of-sample backtest period

### Priority 3 — Production Features

- [ ] Add India VIX historical data integration
- [ ] Implement proper options pricing (Black-Scholes or binomial for intraday marks)
- [ ] Add broker API integration (Zerodha Kite, ICICI Breeze, Upstox) for live execution
- [ ] Add position tracking across multiple legs
- [ ] Add alerting (Telegram/email) for screener signals

---

## 8. Reusable Components for Other Projects

The following parts of this codebase can be directly reused or adapted:

| Component | File | Reusability | Notes |
|---|---|---|---|
| NSE option chain fetcher | `options_screener.py` lines 18–37 | HIGH | Fix cookie handling; core structure is good |
| Signal filter / DataFrame builder | `options_screener.py` lines 40–76 | HIGH | Clean pattern; easy to add more signal types |
| Cumulative P/L chart | `backtest_strategy.py` lines 34–43 | MEDIUM | Replace synthetic P/L with real values |
| Performance metrics printer | `backtest_strategy.py` lines 46–60 | HIGH | Add Sharpe, drawdown, Calmar to the output |
| Streamlit layout with auto-refresh | `options_screener.py` lines 7–15 | HIGH | Solid boilerplate for any live dashboard |

---

## 9. Summary Verdict

| Dimension | Score | Notes |
|---|---|---|
| Code quality | 6/10 | Clean, readable, but structurally naive |
| Strategy logic | 4/10 | Conceptually valid but critically flawed execution |
| Backtest realism | 2/10 | Flat P/L, no costs, no real premium — not tradeable as-is |
| Screener functionality | 5/10 | Good UI skeleton; signal logic and API need fixing |
| Production readiness | 2/10 | Missing margin, costs, real premiums, robust API |
| Potential | 8/10 | Solid foundation for a real theta-decay strategy system |

**Bottom line:** This is a promising R&D prototype that correctly identifies a real trading strategy (short straddle/strangle theta decay) and builds useful scaffolding. However, the backtest numbers are not trustworthy for live deployment due to the flat P/L model, missing transaction costs, and symmetric leg assumption. With the fixes outlined above — particularly real premium data, transaction costs, and correct signal logic — this can become a solid component in a larger options algo trading system.

---

*Report generated by automated analysis of source code, logic simulation, and options strategy domain review.*
