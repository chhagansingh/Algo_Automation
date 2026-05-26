# Prompt Quality Assessment: ai-trading-claude-main
**Date:** 2026-05-25
**Assessor:** AlgoTrader Import Engine
**Question:** Will these prompts generate profitable trade signals if connected to an LLM API?

---

## Executive Summary

| Dimension | Score | Weight | Weighted |
|-----------|-------|--------|----------|
| Prompt Engineering Quality | 88/100 | 20% | 17.6 |
| Actionability (Entry/Exit Prices) | 15/100 | 30% | 4.5 |
| Data Reliability | 25/100 | 25% | 6.25 |
| Risk Management Integration | 40/100 | 15% | 6.0 |
| Profitability Track Record | 0/100 | 10% | 0.0 |
| **COMPOSITE SCORE** | | | **34.35/100** |

**Verdict: 34% — BELOW 50% THRESHOLD → DELETE PROJECT**

---

## 1. Prompt Engineering Quality: 88/100

### What's Excellent
- **5 parallel agents** with clear separation of concerns
- **Each agent has 5 sub-dimensions** with explicit 0-20 scoring rubrics
- **Structured JSON output** required from every agent
- **Specific search queries** provided (not vague "research this")
- **Clear rules:** "ALWAYS compare to sector average", "NEVER fabricate numbers"
- **Weighted composite score:** Technical 25%, Fundamental 25%, Sentiment 20%, Risk 15%, Thesis 15%
- **Signal calibration:** BUY needs 3+ conditions, SELL needs 3+ conditions

### Example of Excellent Prompt Design (from trade-risk agent):
```
Volatility Scoring (0-20):
  17-20 = Beta <0.8, historical vol <15%
  13-16 = Beta 0.8-1.0, vol 15-25%
   9-12 = Beta 1.0-1.3, vol 25-35%
   5-8  = Beta 1.3-1.8, vol 35-50%
   0-4  = Beta >1.8, vol >50%
```
This is granular, measurable, and specific.

---

## 2. Actionability: 15/100

### Critical Weakness — No Actual Trading Execution

| What This Project Outputs | What AlgoTrader Needs |
|---------------------------|----------------------|
| "Trade Score: 74/100" | Entry price: ₹24,050 |
| "Grade: A, Signal: BUY" | Strike: 24050 CE @ ₹117 |
| "Technical Strength: Strong" | Exit: 3:25 PM @ ₹X |
| "Bullish momentum" | P&L: +₹3800 per lot |
| "Support at $165" | Stop Loss: ₹100 points |

**The prompts generate RESEARCH, not TRADES.**

- No strike selection logic
- No premium calculation
- No lot size determination
- No intraday entry timing
- No EOD close automation
- No P&L tracking per trade

---

## 3. Data Reliability: 25/100

### Problem: WebSearch Dependency

```
Every analysis uses:
  WebSearch: "[TICKER] stock price today..."
  WebSearch: "[TICKER] analyst rating..."
```

**Issues:**
- Web results vary by time, location, search engine
- LLM can hallucinate numbers even with "never fabricate" instruction
- No structured API (yfinance, NSE API) — all free-text parsing
- For NIFTY specifically: US-centric searches won't work
- Options data (IV, PCR, Max Pain) requires NSE-specific queries

**Comparison:**
| Data Source | AlgoTrader | ai-trading-claude |
|-------------|------------|-------------------|
| Nifty Spot | yfinance API → exact float | WebSearch → text parsing |
| Option Chain | NSE API → JSON parse | Not available |
| IV/PCR | Real NSE data | WebSearch estimate |
| Historical | 19 years structured | Last 30 days text |

---

## 4. Risk Management: 40/100

### What's Good
- Position sizing formula: Base 5% × (Risk Score / 70)
- Stop loss suggestions based on ATR
- Max drawdown history tracked
- Risk/reward ratio calculated in thesis agent

### What's Missing
- No automatic stop loss execution
- No daily loss limit (e.g., max -2% per day)
- No correlation check across portfolio
- Risk agent scores HIGH for safety (opposite of typical risk scoring)
- No Greeks exposure for options (delta, theta, vega)

---

## 5. Profitability Track Record: 0/100

### Cannot Be Backtested

This project has **zero historical trade data** because:
1. Every analysis is live WebSearch → different results each time
2. No trade log, no P&L history
3. No position tracking
4. No way to replay "what would the score have been on March 15, 2025?"

**Cannot compute:** Win rate, Sharpe, max drawdown, profit factor

---

## 6. Applicability to NIFTY Options: 20/100

### Designed for US Stocks, Not Indian Markets

| Feature | US Stocks | NIFTY Options |
|---------|-----------|---------------|
| Ticker format | AAPL, MSFT | ^NSEI (not recognized) |
| Filings | SEC 13F, Form 4 | No equivalent |
| Options | CBOE, monthly | NSE, weekly |
| Lot size | 100 shares | 25 units |
| Market hours | 9:30-16:00 ET | 9:15-15:30 IST |
| Currency | USD | INR |

The `/trade options` skill discusses:
- Long calls, bull spreads, cash-secured puts
- NOT: Short straddles, iron condors (which AlgoTrader uses)
- NOT: IV rank for NIFTY specifically
- NOT: PCR for Indian markets

---

## 7. What CAN Be Salvaged

Despite low trading score, the **scoring rubrics are excellent** and could enhance AlgoTrader:

### Ideas to Port:
1. **Multi-agent scoring** — Before taking AlgoTrader signal, run quick validation:
   - Technical agent checks: Is trend aligned with signal?
   - Risk agent checks: Is IV too high/low for this strategy?
   - Sentiment agent checks: Any news that invalidates the setup?

2. **Structured scoring rubrics** — Replace Algo3's subjective regime detection with explicit scoring tables

3. **Position sizing formula** — Add risk-adjusted lot sizing to paper runner

4. **Thesis documentation** — Log WHY a trade was taken (catalyst, edge)

---

## Final Recommendation

| Use Case | Suitability |
|----------|-------------|
| Automated trading system | ❌ 0% — Not designed for this |
| Pre-trade research validation | ✅ 70% — Good second opinion |
| Options strategy education | ✅ 80% — Excellent learning material |
| NIFTY-specific analysis | ❌ 20% — US-centric design |
| Profitable signal generation | ❌ 35% — Below threshold |

**Decision: DELETE ai-trading-claude-main project**
- Does not meet 50% profitability threshold
- Not a trading algorithm (research tool only)
- Not applicable to NIFTY options
- However: Extract scoring rubrics for future AlgoTrader enhancement

---

*Assessment generated by AlgoTrader import_project module*
*Composite Score: 34/100 — Below 50% threshold*
