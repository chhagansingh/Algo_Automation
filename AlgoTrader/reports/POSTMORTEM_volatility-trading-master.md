# Postmortem Report: volatility-trading-master
**Generated:** 2026-05-25
**Manual Review:** YES — this is NOT a trading strategy

---

## 1. Executive Summary

| Attribute | Value |
|-----------|-------|
| **Project Type** | Research / Analytics Library (NOT a trading strategy) |
| **Author** | Jason Strimpel (@jasonstrimpel) |
| **Based On** | Euan Sinclair's "Volatility Trading" (book) |
| **Purpose** | Volatility estimation using multiple estimators + visualization |
| **Entry/Exit Logic** | **NONE** — no trading signals |
| **Complexity** | MEDIUM — mathematical library |
| **Indian Market Fit** | HIGH — estimators work on any OHLC data |

---

## 2. What This Project Actually Is

This is a **volatility estimation and visualization toolkit**. It does NOT trade. It calculates and plots:

### Volatility Estimators Implemented

| Estimator | Uses | Formula Key |
|-----------|------|-------------|
| **Garman-Klass** | OHLC | Most efficient using open, high, low, close |
| **Parkinson** | HL only | Uses high-low range (ignores open/close) |
| **Rogers-Satchell** | OHLC | Handles drift, no open-gap bias |
| **Yang-Zhang** | OHLC | Best unbiased estimator, handles overnight gaps |
| **Hodges-Tompkins** | Close only | Adjustment for small sample bias |
| **Raw (Std Dev)** | Close only | Standard close-to-close volatility |
| **Skew** | Close only | Distribution skewness |
| **Kurtosis** | Close only | Distribution tail fatness |

### Visualization Outputs

1. **Volatility Cones** — compare current vol vs historical percentiles across time windows
2. **Rolling Quantiles** — 25th/75th percentile bands over time
3. **Rolling Extremes** — min/max volatility envelope
4. **Rolling Descriptives** — mean, std dev, z-score
5. **Histogram** — distribution of realized volatility
6. **Benchmark Comparison** — vol ratio vs benchmark (e.g., stock vs SPY)
7. **Correlation** — rolling correlation with benchmark volatility
8. **OLS Regression** — vol vs benchmark vol regression

### Deliverable
- **PDF Term Sheet** with all metrics — used for institutional options desks

---

## 3. Code Quality Assessment

| Aspect | Score | Notes |
|--------|-------|-------|
| Structure | 7/10 | Clean package structure, modular estimators |
| Documentation | 6/10 | Docstrings present but brief |
| Error Handling | 6/10 | Input validation on constructor |
| Mathematical Accuracy | 8/10 | Standard textbook implementations |
| Visualization | 8/10 | Professional matplotlib output, PDF term sheets |
| **Overall** | **7/10** | Solid research library |

---

## 4. How This Relates to Our Trading System

### NOT a Strategy
This project has **ZERO** entry/exit logic. You cannot run a backtest on it. It tells you:
- "Current realized vol is 15%, historical median is 18%, 75th percentile is 22%"
- But it does NOT tell you: "Buy CE because vol is low"

### Useful For Our System

| Use Case | How We Can Use It |
|----------|-------------------|
| **IV vs RV comparison** | Compare NSE implied vol (from option chain) vs Yang-Zhang realized vol |
| **Regime detection** | "Current vol is in bottom 25th percentile" = low vol regime = sell straddles |
| **Position sizing** | Scale straddle size by current vol level |
| **Signal validation** | If our algo signals a trade but vol is at historical extremes, be cautious |
| **Term sheets** | Generate professional PDF reports for clients/stakeholders |

### Specific Integration Ideas

1. **algo1/algo2 enhancement:** Before selling straddle, check if current Yang-Zhang vol is in bottom 25% of last 90 days. If yes, straddle premium is cheap → good time to sell.

2. **algo5 (VIX) enhancement:** Instead of just India VIX level, compare realized vol (Yang-Zhang) vs implied vol. If RV < IV significantly, market is overpricing fear → bullish.

3. **Dashboard metric:** Add "Realized Vol (Yang-Zhang)" and "IV-RV Spread" as signal cards.

---

## 5. Comparison: Estimator Efficiency

(from academic literature — Yang-Zhang is the "best" for practical use)

| Estimator | Efficiency vs Close-to-Close | Uses Overnight Gap? |
|-----------|-------------------------------|---------------------|
| Close-to-Close (Raw) | 1.0x (baseline) | No |
| Parkinson | 5.2x | No |
| Garman-Klass | 7.4x | No |
| Rogers-Satchell | 8.0x | No |
| **Yang-Zhang** | **14.0x** | **Yes** |

> **Yang-Zhang** is the most statistically efficient estimator because it combines overnight gap (open vs prev close), open-to-close move, and intraday range. It is the recommended default for NIFTY analysis.

---

## 6. Verdict

| Category | Score | Notes |
|----------|-------|-------|
| Code Quality | 7/10 | Solid mathematical library |
| Strategy Validity | N/A | NOT a strategy |
| Research Value | 8/10 | Excellent for vol regime analysis |
| Indian Adaptability | 9/10 | Works on any OHLC data, including NIFTY |
| Integration Potential | 7/10 | Can enhance existing algos with vol context |
| **Overall** | **7.5/10** | Valuable research tool, not a standalone strategy |

**Recommendation:**
1. **Do NOT extract as an algo** — this is not a strategy
2. **Salvage the Yang-Zhang estimator** for our dashboard/backtest engine
3. **Add IV-RV spread** as a signal card for existing algos
4. **Use for term sheet generation** if we ever need professional PDF reports

---
*Report generated by manual review*
