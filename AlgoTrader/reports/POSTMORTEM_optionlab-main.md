# Postmortem Report: optionlab-main
**Generated:** 2026-05-25
**Manual Review:** YES — this is NOT a trading strategy

---

## 1. Executive Summary

| Attribute | Value |
|-----------|-------|
| **Project Type** | Options Strategy Evaluation Library (NOT a trading strategy) |
| **Author** | Roberto Gomes (rgaveiga) |
| **Purpose** | Calculate P&L profiles, Greeks, and Probability of Profit (PoP) for any options strategy |
| **Entry/Exit Logic** | **NONE** — no trading signals |
| **Complexity** | MEDIUM — mathematical pricing library |
| **Indian Market Fit** | HIGH — Black-Scholes works on any underlying |

---

## 2. What This Project Actually Is

OptionLab is a **strategy evaluation toolkit**. You input a multi-leg options strategy, and it outputs:

### Outputs Generated

| Output | Description |
|--------|-------------|
| **P&L Profile** | Profit/loss across a range of underlying prices at target date |
| **Probability of Profit (PoP)** | Chance of strategy being profitable at target |
| **Profit/Loss Ranges** | Price ranges where strategy is profitable/unprofitable |
| **Expected Profit** | Average profit IF strategy is profitable |
| **Expected Loss** | Average loss IF strategy is unprofitable |
| **Greeks per leg** | Delta, Gamma, Theta, Vega, Rho for each option leg |
| **Implied Volatility** | Back-solved IV from premium and market parameters |
| **ITM Probability** | Chance of option finishing in-the-money |
| **Probability of Touch** | Chance of option touching strike before expiry |

### Example Usage (from notebook)

```python
from optionlab import run_strategy, Inputs

# Sell 100 naked calls at strike 175, premium 1.15
inputs = Inputs(
    stock_price=164.04,
    volatility=0.272,
    start_date=date(2021, 11, 22),
    target_date=date(2021, 12, 17),
    strategy=[
        {"type": "call", "strike": 175.00, "premium": 1.15, "n": 100, "action": "sell"}
    ],
    model="black-scholes"
)

out = run_strategy(inputs)
# out.profit_probability = 0.839 (83.9% chance of profit)
# out.delta = [-0.204]
# out.theta = [0.091]
```

---

## 3. Code Quality Assessment

| Aspect | Score | Notes |
|--------|-------|-------|
| Structure | 8/10 | Clean package, modular, Pydantic models |
| Documentation | 7/10 | Docstrings, GitHub Pages, examples |
| Mathematical Accuracy | 8/10 | Standard Black-Scholes, all Greeks |
| Type Safety | 8/10 | Pydantic v2, Literal types, validators |
| Testing | 6/10 | Some tests present |
| **Overall** | **7.5/10** | Solid, production-ready library |

---

## 4. How This Relates to Our Trading System

### NOT a Strategy
This project has **ZERO** entry/exit logic. You cannot backtest it. It does NOT tell you when to trade.

### VERY Useful For Our System

| Use Case | How We Can Use It |
|----------|-------------------|
| **Replace our basic BS pricing** | Our `utils/pricing.py` is basic; OptionLab has full Greeks + IV |
| **Add PoP to signal cards** | "Sell straddle at ₹24050 — PoP = 72%" |
| **P&L profile visualization** | Show profit/loss diagram in dashboard before taking trade |
| **Multi-leg strategy support** | Iron condor, calendar spread, butterfly analysis |
| **IV back-solve** | Calculate implied vol from NSE option chain premiums |
| **Risk assessment** | Before entering algo1/algo2, check expected profit/loss ranges |

### Specific Integration Ideas

1. **Dashboard Enhancement:** Before paper trading, show P&L cone + PoP for the selected strategy
2. **Signal Card Update:** Add "PoP", "Expected Profit", "Max Loss" to all algo signal cards
3. **algo3 (EMA-Cross) improvement:** Instead of just "buy CE", calculate PoP and expected return for the ATM CE
4. **Risk manager:** Before any trade, run OptionLab to check if expected loss > risk budget

---

## 5. Comparison: Our Current Pricing vs OptionLab

| Feature | Our `utils/pricing.py` | OptionLab |
|---------|----------------------|-----------|
| Black-Scholes price | ✅ Basic | ✅ Full |
| Delta | ✅ Yes | ✅ Yes |
| Gamma | ❌ No | ✅ Yes |
| Theta | ❌ No | ✅ Yes |
| Vega | ❌ No | ✅ Yes |
| Rho | ❌ No | ✅ Yes |
| Implied Vol | ❌ No | ✅ Yes |
| Probability of Profit | ❌ No | ✅ Yes |
| P&L Profile | ❌ No | ✅ Yes (multi-leg) |
| ITM Probability | ❌ No | ✅ Yes |
| Probability of Touch | ❌ No | ✅ Yes |
| Multi-leg strategies | ❌ No | ✅ Yes |

> **Conclusion:** OptionLab is significantly more comprehensive. We should integrate it as a dependency.

---

## 6. Verdict

| Category | Score | Notes |
|----------|-------|-------|
| Code Quality | 7.5/10 | Solid library with Pydantic models |
| Strategy Validity | **N/A** | NOT a strategy |
| Research Value | 8/10 | Excellent for options pricing and risk analysis |
| Indian Adaptability | 9/10 | Black-Scholes universal; just change country to "IN" |
| Integration Potential | **9/10** | Can significantly enhance our pricing and risk metrics |
| **Overall** | **8/10** | Valuable library — should be integrated as a dependency |

**Recommendation:**
1. **Do NOT extract as an algo** — this is not a strategy
2. **DO integrate as a library dependency** — replace/augment our basic BS pricing
3. **Use for:** PoP calculation, P&L profiles, IV back-solve, Greeks, risk assessment
4. **Installation:** `pip install optionlab` (already on PyPI)
5. **Short-term win:** Add PoP and expected P&L to our signal cards and dashboard

---
*Report generated by manual review*
