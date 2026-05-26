# R&D Algo Trading — Cross-Project Comparison Tracker

**Last Updated:** May 25, 2026  
**Analyst:** Devin (AI Engineering Assistant)  
**Scope:** All 5 projects in `/Users/com/Desktop/R&D/`

---

## Projects Analyzed — All Complete

| # | Project | Postmortem Report | Status |
|---|---------|-------------------|--------|
| 1 | R&D (backtest_strategy.py + options_screener.py) | `POSTMORTEM_REPORT.md` | Complete |
| 2 | nifty_tradebot-main | `POSTMORTEM_nifty_tradebot.md` | Complete |
| 3 | Nifty-Bot-main | `POSTMORTEM_Nifty_Bot.md` | Complete |
| 4 | nifty-options-bot-main | `POSTMORTEM_nifty_options_bot.md` | Complete |
| 5 | nifty-options-scanner-main | `POSTMORTEM_nifty_options_scanner.md` | Complete |

---

## Scoring Matrix (Out of 5)

| Dimension | R&D backtest | nifty_tradebot | Nifty-Bot-main | options-bot | options-scanner |
|-----------|:-----------:|:--------------:|:--------------:|:-----------:|:---------------:|
| Architecture quality | 1 | 2 | 4 | **5** | 3 |
| Secrets management | N/A | **0 (CRITICAL)** | 5 | 5 | 5 |
| Options pricing accuracy | 1 | 1 | 5 | 2 (delta approx) | **5** (pure BS) |
| Strategy sophistication | 2 | 3 | 5 | 4 | 1 (scanner only) |
| Backtest validity | 3 | 3 | 4 | 2 | N/A |
| Test coverage | 0 | 0 | 3 | 1 | 0 |
| Live trading readiness | 0 | 1 | 4 | 3 | 0 |
| Risk management | 0 | 1 | 4 | **5** | 0 |
| Notifications/alerting | 0 | 0 | 0 | **5** (Telegram+email) | 1 (not wired) |
| ML / AI | 0 | 2 (LSTM, bad) | 0 | **5** (XGBoost+ONNX) | 2 (FinBERT) |
| DB / persistence | 0 | 1 | 2 | **5** (Postgres+Alembic) | 2 (SQLite) |
| Code reusability | 2 | 2 | 4 | 4 | **5** |
| **TOTAL (/ 60)** | **9** | **16** | **40** | **42** | **24** |

---

## Backtest Performance (May 2025 – May 2026)

| Project | Strategy | Symbol | Trades | Win Rate | Net P&L | Sharpe |
|---------|----------|--------|--------|----------|---------|--------|
| R&D | EMA+RSI sell straddle (binary ₹100) | NIFTY | 223 | 77.6% | +₹24,600 | — |
| nifty_tradebot | Same R&D strategy on 1-min data | NIFTY | 223 | 77.6% | +₹24,600 | — |
| nifty_tradebot | LSTM directional | NIFTY | — | **42.75%** | Negative | — |
| Nifty-Bot-main | **EMA 5/20 + RSI (CE/PE buy)** | NIFTY | 131 | **59.5%** | **+₹1,14,401** | **6.59** |
| Nifty-Bot-main | Iron Condor (daily — broken model) | NIFTY | 96 | 0.0% | -₹44,899 | -36.01 |
| Nifty-Bot-main | Short Straddle (weekly — corrected) | NIFTY | 51 | 52.9% | -₹43,723 | — |
| options-bot | Baseline rule (MACD+RSI, tuned) | NIFTY | 44 | **29.5%** | **-₹72,217** | -1.55 |
| options-bot | Baseline rule (MACD+RSI, tuned) | BANKNIFTY | 42 | **28.6%** | **-₹97,528** | -1.93 |
| options-bot | RSI Divergence | NIFTY | 1 | 100% | +₹8,182 | 0.00 |
| options-bot | RSI Divergence | BANKNIFTY | 0 | — | ₹0 | — |
| options-scanner | N/A (scanner, no backtest) | — | — | — | — | — |

**Best performer:** Nifty-Bot-main EMA 5/20 + RSI → +₹1,14,401 (+11.44% ROC, Sharpe 6.59)  
**Worst performer:** options-bot baseline → -₹72K (NIFTY) / -₹97K (BANKNIFTY), 29% win rate

---

## Critical Issues Summary

### R&D backtest — 8 critical bugs
- Binary ±₹100 P&L model (not real option premium)
- No stop-loss, no slippage, no brokerage
- NSE API hardcoded (fragile)
- No lot size, no risk management, no live integration

### nifty_tradebot-main — 1 critical, 4 major
- **CRITICAL: ICICI Breeze API keys hardcoded** in `ntb_get_history.py`
- LSTM accuracy 42.75% — worse than random (50%); MAE 5.7× worse than naive baseline
- No options pricing, no paper trading, no risk management

### Nifty-Bot-main — 0 critical, 5 major
- Daily-bar theta≈0 bug → 0% win rate for Iron Condor/Straddle in backtest
- 59/213 tests failing (strategy + risk manager import errors)
- Paper trading tests using deprecated single-leg API
- Static Iron Condor wing width (not IV-based)
- Short Straddle lacks per-leg stop-loss

### nifty-options-bot-main — 0 critical, 5 major
- Baseline rule 29.5% win rate → negative alpha
- RSI divergence too infrequent (1 signal/year — statistically useless)
- Paper trades in SQLite `/tmp` (reset on every cloud deploy)
- Delta-approximation P&L (not real Black-Scholes)
- Near-zero unit test coverage for all critical modules

### nifty-options-scanner-main — 0 critical, 4 major
- `closes[-1]` integer indexing crashes on DatetimeIndex Series
- Boolean ambiguity in `compute_emas()` — always crashes
- Telegram alerts not wired to any agent
- Project is 25% complete (Sessions 3–8 not built)

---

## Reusability Map — Best Components Across All Projects

| Component | Best Source | Quality | Action |
|-----------|-------------|---------|--------|
| **Black-Scholes + Greeks + Max Pain + PCR** | options-scanner (`options_calculator.py`) | Production-ready, zero deps, verified | Extract to shared lib |
| **Technical indicators (RSI/MACD/BB/EMA/HV)** | options-scanner (`technical_indicators.py`) | Good, 2 bugs to fix | Fix `.iloc`, extract |
| **Risk engine (SL/TP/trailing/Kelly/daily cutoff)** | options-bot (`risk/engine.py`) | Best in portfolio | Reuse as-is |
| **Feature flags + safety defaults** | options-bot (`config/`) | Best in portfolio | Reuse pattern |
| **Alembic migrations + Postgres** | options-bot (`migrations/`) | Production-grade | Reuse schema |
| **Telegram + email notifications** | options-bot (`notifications/`) | Complete, dedup | Reuse as-is |
| **XGBoost + ONNX ML pipeline** | options-bot (`ml/`) | Strong, needs live eval | Activate + test |
| **Market Regime Classifier (ADX/BB/ATR)** | Nifty-Bot-main (`intelligence/market_regime.py`) | Validated, correct | Reuse as-is |
| **Paper Trading Manager (multi-leg, JSON/CSV)** | Nifty-Bot-main (`managers/paper_trading_manager.py`) | Solid | Fix API, reuse |
| **EMA+RSI signal generator** | Nifty-Bot-main (`strategies/`) | 59% WR proven | Deploy to paper |
| **1-min live data pipeline (Breeze)** | nifty_tradebot | Real intraday data | Fix keys, reuse |
| **NSE option chain scraper (free)** | options-scanner (`nse_fetcher.py`) | Good, no API key | Integrate |
| **News sentiment (FinBERT/VADER)** | options-scanner (`sentiment_engine.py`) | Novel signal | Add as pre-filter |
| **LSTM model** | nifty_tradebot | 42.75% accuracy | **DISCARD** |
| **Binary ±₹100 P&L model** | R&D backtest | Unrealistic | **DISCARD** |

---

## Paper Trading Readiness — Final Rankings

| Rank | Project | Score | Deployable? | Blocker |
|------|---------|-------|-------------|---------|
| 1 | **Nifty-Bot-main (EMA/RSI)** | **12/15** | Yes — paper mode | Install Upstox SDK |
| 2 | nifty-options-bot-main | 11/15 | No | 29.5% WR, fix ML layer |
| 3 | nifty_tradebot | 4/15 | No | Hardcoded API keys |
| 4 | R&D backtest | 2/15 | No | No live integration |
| 5 | nifty-options-scanner | 2/15 | N/A | Scanner only |

---

## Recommended Unified Architecture

If consolidating all projects into one production system:

```
unified-nifty-bot/
├── lib/                          ← shared utilities
│   ├── bs_pricer.py              from options-scanner (zero-dep BS)
│   ├── technical.py              from options-scanner (fix .iloc bugs)
│   ├── nse_chain.py              from options-scanner (free NSE data)
│   └── sentiment.py              from options-scanner (FinBERT/VADER)
├── strategies/
│   ├── ema_rsi.py                from Nifty-Bot-main (59% WR, validated)
│   ├── iron_condor.py            from Nifty-Bot-main (fix: IV-based wings)
│   └── straddle.py               from Nifty-Bot-main (fix: add stop-loss)
├── intelligence/
│   ├── regime.py                 from Nifty-Bot-main (ADX/BB/ATR, validated)
│   ├── ml_signal.py              from options-bot (XGBoost+ONNX, activate)
│   ├── pcr.py                    from Nifty-Bot-main + scanner
│   └── iv_rank.py                from Nifty-Bot-main
├── risk/
│   └── engine.py                 from options-bot (Kelly, daily cutoff, trailing)
├── managers/
│   ├── paper.py                  from Nifty-Bot-main (multi-leg JSON/CSV)
│   └── notifications.py          from options-bot (Telegram + email)
├── data/
│   ├── upstox.py                 from Nifty-Bot-main (daily/options)
│   ├── breeze.py                 from nifty_tradebot (1-min intraday)
│   └── nse_chain.py              from options-scanner (free chain data)
├── config/
│   ├── settings.py               from options-bot (Pydantic + feature flags)
│   └── migrations/               from options-bot (Alembic, 6+ versions)
└── backtest/
    ├── engine.py                 from Nifty-Bot-main (improve: real BS pricing)
    └── walkforward.py            from options-bot (7,680-config sweep)
```

---

## Action Priority List — All 5 Projects

### Immediate (security + correctness)
1. **Fix hardcoded ICICI Breeze keys** in `nifty_tradebot-main/ntb_get_history.py` — **security risk**
2. **Fix `.iloc` bugs** in `options-scanner/utils/technical_indicators.py` (BUG-NOS-001/002)
3. **Fix broken tests** in Nifty-Bot-main (conftest mock + paper trading API update)

### Short-term (backtest validation)
4. **Activate ML signal** in options-bot (set `ENABLE_ML_SIGNAL=true`) and re-run backtest
5. **Paper trade EMA/RSI** via Nifty-Bot-main (install Upstox SDK, run paper mode)
6. **Collect 5-min data** (from nifty_tradebot's Breeze pipeline) for Iron Condor re-validation
7. **Tune divergence params** in options-bot (pivot lookback 5→3) to increase signal frequency

### Medium-term (integration)
8. **Extract `options_calculator.py`** from scanner into shared lib; replace options-bot's delta-approx
9. **Migrate paper trades** in options-bot from SQLite `/tmp` to Postgres
10. **Build Strategy Scanner** sessions 3–8 in options-scanner
11. **Walk-forward retrain** options-bot ML models on 2025–2026 data
12. **Wire Telegram alerts** in options-scanner agents

---

## Final Rankings

| Category | Winner | Runner-up |
|----------|--------|-----------|
| Best backtest P&L | Nifty-Bot-main EMA/RSI (+₹1,14,401) | R&D backtest (+₹24,600 binary) |
| Best architecture | nifty-options-bot-main | Nifty-Bot-main |
| Best options pricing | nifty-options-scanner | Nifty-Bot-main |
| Best risk management | nifty-options-bot-main | Nifty-Bot-main |
| Best ML / AI | nifty-options-bot-main (XGBoost+ONNX) | nifty_tradebot (LSTM, but bad) |
| Best for paper trading NOW | Nifty-Bot-main | — |
| Most reusable code | nifty-options-scanner | nifty-options-bot-main |
| Most complete product | nifty-options-bot-main | Nifty-Bot-main |
| Worst win rate | nifty-options-bot-main (29.5%) | LSTM in nifty_tradebot (42.75%) |
| Security failure | nifty_tradebot (hardcoded keys) | — |

---

*Tracker maintained by Devin — final update after all 5 project postmortems completed (May 25, 2026)*
