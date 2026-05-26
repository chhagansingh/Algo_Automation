# Postmortem Report: ai-trading-claude-main
**Generated:** 2026-05-25
**Algo ID:** imported_ai_trading_claude_main_0525
**Classification:** RESEARCH TOOL (NOT an executable trading algorithm)

---

## 1. Project Type — AI Trading Analyst for Claude Code

This is **not** a Python backtest project. It is an **AI Agent Skill System** for Claude Code (Anthropic's CLI tool).

### What It Actually Is:
- **16 SKILL.md files** — Instruction prompts for Claude AI agents
- **5 Parallel Agents** — Technical, Fundamental, Sentiment, Risk, Thesis
- **0 Python trading logic** — No backtest, no entry/exit rules, no P&L calculation
- **WebSearch-based** — Fetches real-time data from the internet
- **Research-only** — Generates reports, does NOT execute trades

### How It Works:
```
User types: /trade analyze AAPL
         |
         +-- trade-technical agent (WebSearch)
         +-- trade-fundamental agent (WebSearch)
         +-- trade-sentiment agent (WebSearch)
         +-- trade-risk agent (WebSearch)
         +-- trade-thesis agent (WebSearch)
         |
         +-- Composite Trade Score (0-100)
         +-- Grade: A+ / A / B / C / D / F
         +-- Signal: Strong Buy / Buy / Hold / Caution / Avoid
         +-- PDF Report generated
```

---

## 2. Why It Cannot Be Backtested

| Requirement | AlgoTrader | ai-trading-claude |
|-------------|------------|-------------------|
| Entry/exit rules | Hard-coded Python logic | AI-generated from WebSearch |
| Data source | yfinance CSV / NSE API | Real-time web search |
| Reproducibility | Same code + same data = same result | Different web results every time |
| P&L calculation | Exact math (₹ per trade) | No P&L — only scores |
| Backtest possible | Yes — historical data replay | No — needs live web data |

**Conclusion:** This tool generates **opinions/reports**, not **executable trades**. It cannot be backtested because its output depends on live web search results, not deterministic code.

---

## 3. Scoring Methodology (What It Actually Does)

| Category | Weight | Source |
|----------|--------|--------|
| Technical Strength | 25% | WebSearch: price, EMA, RSI, MACD, patterns |
| Fundamental Quality | 25% | WebSearch: PE, EPS, revenue, growth |
| Sentiment & Momentum | 20% | WebSearch: news, analyst ratings, social |
| Risk Profile | 15% | WebSearch: volatility, drawdown, beta |
| Thesis Conviction | 15% | AI synthesis of all 4 agents above |

**Composite Score (0-100):**
- 85-100 = A+ = Strong Buy
- 70-84 = A = Buy
- 55-69 = B = Hold
- 40-54 = C = Caution
- 25-39 = D = Caution
- 0-24 = F = Avoid

---

## 4. Skills Inventory

| # | Skill | Purpose |
|---|-------|---------|
| 1 | `/trade analyze` | Full 5-agent analysis + composite score |
| 2 | `/trade quick` | 60-second snapshot |
| 3 | `/trade technical` | Price action + indicators |
| 4 | `/trade fundamental` | Financials + valuation |
| 5 | `/trade sentiment` | News + social sentiment |
| 6 | `/trade sector` | Sector rotation |
| 7 | `/trade thesis` | Bull/bear case + entry/exit |
| 8 | `/trade compare` | Head-to-head stock comparison |
| 9 | `/trade options` | Options strategy recommendations |
| 10 | `/trade earnings` | Pre-earnings analysis |
| 11 | `/trade portfolio` | Portfolio correlation + rebalance |
| 12 | `/trade risk` | Position sizing + max drawdown |
| 13 | `/trade screen` | Stock screener |
| 14 | `/trade watchlist` | Scored watchlist builder |
| 15 | `/trade report-pdf` | Professional PDF report |

---

## 5. Options Analysis Skill (Detailed)

The `/trade options` skill is the most relevant to AlgoTrader. It analyzes:
- IV Rank / IV Percentile (52-week)
- Expected move (straddle price)
- Put/Call ratio (volume + OI)
- Max Pain
- Unusual options activity
- Earnings context

**Strategy Matrix:**
| IV Environment | Strategy Bias |
|----------------|---------------|
| Very High IV (>70%) | Sell Premium |
| High IV (50-70%) | Sell or Spreads |
| Moderate IV (30-50%) | Neutral / Directional |
| Low IV (10-30%) | Buy Premium |
| Very Low IV (<10%) | Long Straddles |

---

## 6. Comparison with AlgoTrader

| Dimension | AlgoTrader | ai-trading-claude |
|-----------|------------|-------------------|
| **Type** | Automated trading system | AI research analyst |
| **Input** | NSE spot + option chain | Any ticker (stocks, crypto) |
| **Output** | Entry/exit signals + P&L | Research report + score |
| **Automation** | Fully automated execution | Manual report reading |
| **Backtest** | Yes — 19 years daily | No — requires live web data |
| **Paper Trading** | Yes — real LTP tracking | No — no position tracking |
| **Speed** | 60-second loops | Minutes per analysis |
| **Data** | Structured (OHLCV, option chain) | Unstructured (web scraping) |
| **Objective** | Generate alpha | Generate insights |

---

## 7. Value for AlgoTrader Users

**How this tool COMPLEMENTS AlgoTrader:**
1. **Pre-trade research** — Before AlgoTrader takes a signal, use `/trade analyze` for human validation
2. **Options context** — `/trade options` gives IV rank, max pain, PCR for the same ticker
3. **Sentiment check** — `/trade sentiment` explains WHY a move might be happening
4. **Risk sizing** — `/trade risk` suggests position size for the capital allocated

**Integration idea:**
```
09:15 AM — AlgoTrader generates signal (e.g., STRADDLE_SELL at ATM 24050)
09:16 AM — User runs: /trade options NIFTY
09:18 AM — AI analyst confirms: "IV rank 65% — options expensive, good for selling"
09:20 AM — User decides to follow AlgoTrader signal (or skip if AI disagrees)
```

---

## 8. Verdict

| Metric | Score |
|--------|-------|
| **Backtestability** | 0/10 — Not possible |
| **Live Trading** | 0/10 — No execution |
| **Research Quality** | 9/10 — Comprehensive multi-agent analysis |
| **Options Knowledge** | 8/10 — IV framework + strategy matrix |
| **Complement to AlgoTrader** | 7/10 — Good pre-trade validation tool |

**Overall:** This is a **research companion**, not a competitor to AlgoTrader. It cannot replace algo execution, but it can enhance decision-making before taking trades.

---

## 9. Recommendations

1. **Keep as separate tool** — Install via `curl` for pre-trade research
2. **Do NOT import into AlgoTrader** — It has no deterministic trading logic
3. **Use workflow:** AlgoTrader generates signal → ai-trading-claude validates → User decides
4. **Options skill is most useful** — IV rank + max pain + PCR are actionable for option sellers

---

*Report generated by AlgoTrader import_project module*
*Project classification: RESEARCH TOOL — Not backtestable*
