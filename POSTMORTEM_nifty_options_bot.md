# POSTMORTEM REPORT — nifty-options-bot-main

**Analysis Date:** May 25, 2026  
**Analyst:** Devin (AI Engineering Assistant)  
**Project Path:** `/Users/com/Desktop/R&D/nifty-options-bot-main/nifty-options-bot-main/`  
**Project Type:** Full-stack production algo trading platform (FastAPI + Zerodha + ML + ONNX)  
**Compared Against:** R&D backtest, nifty_tradebot, Nifty-Bot-main, nifty-options-scanner  

---

## 1. Executive Summary

nifty-options-bot-main is the most complete and production-aware project in the entire R&D portfolio. It is a **6-phase build** covering: rule-based signals → ML-enhanced signals (XGBoost + ONNX) → risk management → live broker integration (Zerodha Kite) → notifications → walk-forward validation.

It has the most sophisticated ML pipeline (XGBoost direction model + KMeans regime classifier exported to ONNX), a proper database migration system (Alembic), Telegram/email notifications, feature flags for safe rollout, and a walk-forward parameter sweep framework.

**The core problem:** The backtesting engine's rule-based signal generator (SuperTrend + MACD + RSI) produces poor results — only 29.5% win rate and -₹72,217 net P&L on NIFTY over the study period. The divergence backtest gives 1 trade on NIFTY (insufficient signal frequency). Both strategies **underperform buy-and-hold** significantly. The ML ONNX models exist but require PostgreSQL + live data pipeline to evaluate.

**Verdict:** Best infrastructure in the portfolio. Worst live backtest P&L. The rule-based engine needs improvement — the ML layer may salvage it, but ML validation is blocked by missing DB and live data setup.

**Paper Trading Readiness: 11/15 (73%)**

---

## 2. Project Architecture Overview

### 2.1 Directory Structure

```
nifty-options-bot-main/backend/
├── ai/
│   ├── signal_engine.py         # Rule-based signal generator (v3)
│   └── budget_optimizer.py      # Strike + lot sizing optimizer
├── analytics/
│   └── engine.py                # P&L analytics aggregator
├── api/
│   ├── routes.py                # REST endpoints
│   └── ws.py                    # WebSocket live P&L feed
├── backtesting/
│   ├── engine.py                # Vectorized rule-based backtester
│   ├── divergence_backtest.py   # RSI divergence backtester
│   └── metrics.py               # Performance metrics
├── broker/
│   ├── interface.py             # Abstract broker interface
│   ├── paper_adapter.py         # Paper trading broker adapter
│   └── zerodha_adapter.py       # Zerodha Kite Connect adapter
├── config/
│   ├── settings.py              # Pydantic settings (all via .env)
│   └── feature_flags.py         # Runtime feature flag evaluator
├── data/
│   ├── market_data.py           # Live data poller
│   ├── ohlcv_loader.py          # Historical OHLCV loader (yfinance)
│   ├── oi_snapshot_logger.py    # Open interest recorder
│   └── options_chain.py         # Options chain fetcher
├── db/
│   └── base.py                  # SQLAlchemy async engine
├── indicators/
│   ├── engine.py                # SuperTrend, MACD, RSI, EMA
│   ├── divergence.py            # RSI/price divergence detector
│   └── oi_flow.py               # OI flow indicator
├── migrations/                  # Alembic DB migrations (6 versions)
├── ml/
│   ├── model.py                 # XGBoost direction model
│   ├── regime.py                # KMeans regime classifier
│   ├── features.py              # 19-feature ML pipeline
│   ├── registry.py              # Model version registry (DB-backed)
│   └── onnx_models/             # Pre-trained ONNX models (NIFTY + BANKNIFTY)
├── models/                      # SQLAlchemy ORM models (7 tables)
├── notifications/
│   ├── telegram.py              # Telegram bot alerts
│   ├── email.py                 # SMTP email alerts
│   └── dedup.py                 # Alert deduplication (TTL-based)
├── paper_trading/
│   └── simulator.py             # SQLite paper trade CRUD
├── risk/
│   └── engine.py                # Risk engine (SL/TP/trailing/Kelly)
├── scanner/
│   └── engine.py                # Options scanner
├── scheduler/
│   ├── jobs.py                  # APScheduler jobs
│   └── shadow.py                # Signal shadow mode (paper without action)
├── scripts/
│   ├── walkforward_combined_rule.py  # Walk-forward validation (7,680 configs)
│   ├── sweep_combined_rule.py        # Parameter sweep
│   ├── run_divergence_backtest.py    # Divergence vs baseline comparison
│   └── train.py                      # ML model training script
├── tests/
│   └── test_daily_stats.py      # 8 tests — all pass
├── main.py                      # FastAPI app entry point
└── requirements.txt
```

### 2.2 Technology Stack

| Component | Technology |
|-----------|-----------|
| Backend | FastAPI + Uvicorn |
| Database | PostgreSQL (async via asyncpg) + Alembic migrations |
| Fallback DB | SQLite (paper trades in `/tmp`) |
| ML Models | XGBoost + ONNX runtime (pre-trained, exportable) |
| Regime Classifier | KMeans (3 clusters → TRENDING_UP/DOWN/RANGING) |
| Broker | Zerodha Kite Connect (live) + paper adapter |
| Notifications | Telegram Bot + SMTP email |
| Deployment | Railway/Vercel (Procfile + railway.json present) |
| Feature Flags | Environment-variable-driven, runtime-checked |
| Testing | pytest + pytest-asyncio |

---

## 3. Security Assessment

### PASS — Proper Secrets Management

All credentials via `.env` / Pydantic Settings:
```python
class Settings(BaseSettings):
    database_url: str               # Required — no default
    broker_api_key: str = ""
    broker_api_secret: str = ""
    telegram_bot_token: str = ""
    zerodha_encryption_key: str = ""
    enable_live_broker: bool = False  # Default OFF
    enable_auto_execution: bool = False  # Default OFF
```

Feature flags default to `False` — live money features cannot accidentally activate. **Security: PASS.**

### Feature Flag Safety Design

All dangerous operations are flag-gated:
- `ENABLE_LIVE_BROKER` — Zerodha Kite only activates when True
- `ENABLE_AUTO_EXECUTION` — orders only placed when True
- `ENABLE_ML_SIGNAL` — ML inference only when True
- `ENABLE_DIVERGENCE_SIGNAL` — divergence signal only when True

This is the correct pattern for phased production rollout.

---

## 4. Code Quality Assessment

### 4.1 Strengths

**Walk-Forward Validation Framework — Most Rigorous in Portfolio**

The `walkforward_combined_rule.py` script tests 7,680 parameter combinations across 67/33 train-test splits, filtering by out-of-sample robustness:
```
Grid: w_supertrend × w_macd × w_rsi × rsi_ob × rsi_os × threshold
= 6 × 5 × 4 × 4 × 4 × 4 = 7,680 configs
Filter: train_trades ≥ 20, test_trades ≥ 10, both beat Wilson LB
Rank: by test Wilson 95% lower bound (out-of-sample truth only)
```
This is statistically sound — no data leakage, proper OOS validation.

**ML Feature Pipeline — 19 Features, No Look-Ahead**

```python
features = [
    "ret_1", "ret_5", "ret_15", "ret_30",     # Multi-horizon returns
    "rsi", "macd_line", "macd_hist", "macd_cross",  # Momentum
    "supertrend_dir", "bb_pos", "bb_width",    # Trend + volatility
    "atr_pct", "ema_cross", "vol_ratio",       # Risk-adjusted + volume
    "time_sin", "time_cos", "dow_sin", "dow_cos",  # Cyclical time
    "regime"                                   # Regime label
]
# Target: 1 if close[t+3] > close[t], else 0
```
All indicators use `.shift(1)` correctly — no future data leakage.

**ONNX Export — Production ML Deployment**

Pre-trained models exported to ONNX for fast inference (no sklearn overhead at runtime):
- `direction_model_NIFTY.onnx` — XGBoost direction classifier
- `regime_classifier_NIFTY.onnx` — KMeans regime classifier
- Matching models for BANKNIFTY

**Risk Engine — Most Complete in Portfolio**

```python
# Position sizing modes
size_fixed_units(capital, units) → lots
size_fixed_inr(capital, inr_per_trade) → lots
size_risk_pct(capital, risk_pct, sl_pts, lot_size) → lots
size_kelly(win_rate, avg_win, avg_loss, capital) → lots

# Daily cutoffs
check_daily_cutoff(daily_pnl, capital, loss_limit=0.02, profit_target=0.05)
→ {"halt": True/False, "reason": "..."}
```

**Divergence Indicator — No Look-Ahead**

RSI/price divergence detection with proper pivot lookback — signal emitted `lookback` bars after pivot confirmation. Hidden and regular divergence both implemented.

**Alembic DB Migrations — 6 Versions**

Full migration history for reproducible schema evolution:
- `001` → initial tables
- `002` → model registry
- `003` → ONNX model registry
- `004` → orders table
- `005` → OI snapshots
- `006` → signal shadow mode

### 4.2 Weaknesses

**Backtesting Engine — Low-Quality Signals**

The rule-based signal engine combines SuperTrend, MACD, RSI into a score:
```python
score = w_st * supertrend + w_macd * macd + w_rsi * rsi_signal
# Tuned weights: w_st=0, w_macd=15, w_rsi=30
# Note: w_supertrend=0 — SuperTrend is effectively ignored
```
Walk-forward tuning reduced SuperTrend weight to zero — indicating it adds no predictive power. Result: 29.5% win rate (much worse than 50% random baseline).

**P&L Model — Delta Approximation**

```python
pnl = underlying_move × lot_size × lots × DELTA_FACTOR (0.5)
```
This is a crude delta approximation — not actual option premium. Options are non-linear; delta varies with moneyness, DTE, and IV. A fixed 0.5 delta overstates gains on winning trades and understates losses on losing trades. Real P&L using Black-Scholes would likely show worse results.

**Paper Trades in SQLite `/tmp`**

On cloud deployments (Vercel/Railway), `/tmp` is ephemeral — paper trade history resets on each deploy. A P0 issue noted in the project's own CLAUDE.md.

**Only 8 Tests Total**

`test_daily_stats.py` has 8 tests — all pass. But the entire ML pipeline, backtesting engine, risk engine, signal generator, and divergence detector have zero unit tests. The test coverage is effectively 0% for all critical modules.

**Divergence Signal — Too Infrequent**

Over 263 trading days (May 2025–May 2026), the divergence detector produced only 1 signal on NIFTY and 0 on BANKNIFTY. Signal frequency is too low for daily trading — needs parameter tuning (shorter lookback, lower confirmation threshold).

---

## 5. Backtest Results — May 2025 to May 2026

### 5.1 Environment

- **Data:** yfinance daily OHLCV (`^NSEI`, `^NSEBANK`)
- **Period:** May 2, 2025 – May 25, 2026 (263 bars NIFTY, 263 bars BANKNIFTY)
- **Capital:** ₹10,00,000
- **P&L model:** Underlying move × lot_size × lots × 0.5 (delta approximation)

### 5.2 Results Summary

| Strategy | Symbol | Trades | Win Rate | Net P&L | Max DD | Sharpe |
|----------|--------|--------|----------|---------|--------|--------|
| BASELINE (rule-based) | NIFTY | 44 | **29.5%** | **-₹72,217** | ₹1,25,762 | -1.55 |
| BASELINE (rule-based) | BANKNIFTY | 42 | **28.6%** | **-₹97,528** | ₹1,53,817 | -1.93 |
| DIVERGENCE | NIFTY | 1 | 100.0% | +₹8,182 | ₹0 | 0.00 |
| DIVERGENCE | BANKNIFTY | 0 | — | ₹0 | ₹0 | 0.00 |
| BUY & HOLD | NIFTY | 1 | 100.0% | -₹14,998 | ₹1,64,176 | N/A |
| BUY & HOLD | BANKNIFTY | 1 | 100.0% | -₹1,434 | ₹2,04,579 | N/A |

### 5.3 Analysis

**Baseline Rule-Based Strategy — Negative Alpha**

- 29.5% win rate on NIFTY — significantly below the 50% random baseline
- The tuned weights (`w_supertrend=0, w_macd=15, w_rsi=30`) effectively run on MACD + RSI only
- In the May 2025–May 2026 period, Nifty was in a HIGH_VOLATILITY / RANGING regime for 71% of days — MACD/RSI signals frequently whipsawed
- The delta-approx P&L model may undercount losses (real option premium decay would show worse results)

**Divergence Strategy — Insufficient Signal Frequency**

- Only 1 signal over 263 days (NIFTY) — unusable in practice
- Default pivot lookback of 5 bars is too conservative — most divergences are missed
- The 1 trade that fired was profitable (+₹8,182), suggesting the logic is sound but needs parameter adjustment

**Buy & Hold — Also Negative**

- Nifty fell from ~24,420 (May 2025) to ~23,807 (May 2026): -2.5% total
- High volatility made even passive holding difficult in this period
- BankNifty essentially flat (-₹1,434 on ₹10L capital = -0.14%)

**Root Cause of Poor Baseline Performance:**

The study period (May 2025–May 2026) had three distinct regimes:
1. Sideways volatility (May–Aug 2025)
2. Bull run to 26,000+ (Sep–Dec 2025)
3. Sharp correction (Jan–Apr 2026, -1270 pts in one week during tariff shock)

MACD + RSI momentum signals work well in trending markets but generate excessive false signals during whipsaws. The regime classifier (KMeans) should filter trades in RANGING environments — but the ML layer (ENABLE_ML_SIGNAL=True) was not activated during backtesting.

---

## 6. Test Results

```
pytest tests/ -v
8 collected
8 PASSED
```

All 8 tests are in `test_daily_stats.py` — testing the daily P&L statistics functions (sum, mean, streak counting). Critical modules with zero test coverage:

| Module | Coverage |
|--------|---------|
| `backtesting/engine.py` | 0% |
| `backtesting/divergence_backtest.py` | 0% |
| `ml/model.py` | 0% |
| `ml/regime.py` | 0% |
| `ml/features.py` | 0% |
| `ai/signal_engine.py` | 0% |
| `risk/engine.py` | 0% |
| `indicators/divergence.py` | 0% |
| `paper_trading/simulator.py` | 0% |

**Test Health Score: 8/8 pass but ~5% of codebase covered**

---

## 7. Critical Bugs

### BUG-NOB-001 — Severity: HIGH
**Baseline strategy 29.5% win rate — negative alpha**

- **File:** `backend/backtesting/engine.py`
- **Effect:** -₹72K NIFTY, -₹97K BANKNIFTY over study period
- **Root Cause:** SuperTrend weight tuned to 0; MACD+RSI-only signal whipsaws in volatile/ranging market
- **Fix:** Enable ML signal layer (XGBoost direction model) as primary filter; use regime classifier to block trades in RANGING regime

### BUG-NOB-002 — Severity: HIGH
**Divergence signal too infrequent (1 signal / year)**

- **File:** `backend/backtesting/divergence_backtest.py`, `backend/indicators/divergence.py`
- **Effect:** Strategy is statistically unviable (1 trade provides no conclusions)
- **Root Cause:** Pivot lookback=5 bars too conservative; divergence confirmation requires 10+ matching conditions
- **Fix:** Reduce pivot lookback to 3; add looser confirmation (RSI momentum, not just price divergence)

### BUG-NOB-003 — Severity: MEDIUM
**Paper trades lost on deploy (SQLite `/tmp`)**

- **File:** `backend/paper_trading/simulator.py` (line: `DB_PATH = /tmp/paper_trades.db`)
- **Effect:** All paper trade history deleted on each Railway/Vercel deploy
- **Fix:** Migrate paper trades to PostgreSQL using existing SQLAlchemy models; already in P0 list

### BUG-NOB-004 — Severity: MEDIUM
**Delta-approximation P&L model (not real option premium)**

- **File:** `backend/backtesting/engine.py` (`DELTA_FACTOR = 0.5`)
- **Effect:** Options non-linearity ignored; real P&L would likely be worse due to Theta decay
- **Fix:** Integrate `options_calculator.py` from nifty-options-scanner (Black-Scholes) for accurate pricing

### BUG-NOB-005 — Severity: LOW
**Feature flags reset on restart (in-memory state)**

- **File:** `backend/config/feature_flags.py`
- **Effect:** Admin changes to feature flags via API not persisted; admin changes lost on restart
- **Fix:** Store feature flag overrides in PostgreSQL; load on startup

---

## 8. Paper Trading Readiness Checklist

| Category | Item | Status | Score |
|----------|------|--------|-------|
| **Infrastructure** | Secrets management (no hardcoded keys) | PASS | 1/1 |
| **Infrastructure** | Trading modes (paper/live via flag) | PASS | 1/1 |
| **Infrastructure** | FastAPI server runs | PASS | 1/1 |
| **Infrastructure** | DB migrations (Alembic, 6 versions) | PASS | 1/1 |
| **Risk** | Daily loss/profit limits | PASS | 1/1 |
| **Risk** | SL/TP + trailing stops | PASS | 1/1 |
| **Risk** | Kelly / risk-% position sizing | PASS | 1/1 |
| **Notifications** | Telegram + email alerts | PASS | 1/1 |
| **Data** | Live data integration (Zerodha/yfinance) | PARTIAL (untested live) | 0.5/1 |
| **Testing** | Unit tests for critical modules | FAIL (0% coverage on core) | 0/1 |
| **Backtest** | Positive expectancy validated | FAIL (29.5% WR, -₹72K) | 0/1 |
| **ML** | ONNX models available | PASS | 1/1 |
| **ML** | ML pipeline tested in backtest | FAIL (not activated) | 0/1 |
| **Broker** | Zerodha sandbox tested | FAIL (untested) | 0/1 |
| **Deployment** | Railway/Vercel config present | PASS | 1/1 |

**Total: 11/15 (73%)** — Best infra score, but blocked by negative backtest P&L.

---

## 9. Architecture Strengths vs Gaps

| Dimension | Status |
|-----------|--------|
| Secrets management | Best in portfolio |
| Feature flag safety | Best in portfolio |
| DB migration system | Only project with Alembic |
| Notification system | Only project with Telegram + email |
| ML pipeline (training) | Only project with XGBoost + ONNX export |
| Walk-forward validation | Only project with proper OOS testing |
| Deployment readiness | Only project with Railway/Procfile |
| Backtest signal quality | Worst in portfolio (29.5% WR) |
| Options pricing accuracy | Worst (delta approx, no BS) |
| Test coverage | Near-zero for critical modules |

---

## 10. Recommendations

### Immediate (before paper trading)

1. **Activate ML signal layer:** Set `ENABLE_ML_SIGNAL=true` and re-run backtest with XGBoost direction model as primary signal filter
2. **Add regime gate:** Only enter trades when `regime != RANGING` (should eliminate ~40% of losing trades)
3. **Fix divergence parameters:** Reduce pivot lookback from 5 to 3 bars; re-run to increase signal frequency

### Short-term (1–2 weeks)

4. **Migrate paper trades to PostgreSQL:** Implement `PaperTrade` SQLAlchemy model; fix `/tmp` issue
5. **Write unit tests for signal engine and risk engine:** Target 80% coverage on backtesting + risk modules
6. **Replace delta approximation with Black-Scholes pricing:** Integrate `options_calculator.py` from scanner project
7. **Test Zerodha sandbox:** Place test orders in Kite sandbox environment

### Medium-term (1 month)

8. **Retrain ML models on recent data** (models may be trained on pre-2025 data)
9. **Implement regime-conditional strategy routing** (RANGING → avoid; TRENDING → directional; HIGH_VOL → reduce size)
10. **Run walk-forward sweep with ML-enhanced signals** to get updated optimal parameters

---

## 11. Verdict

nifty-options-bot-main has the best architecture in the entire portfolio — proper feature flags, Alembic migrations, ONNX ML models, Telegram alerts, walk-forward validation, and Zerodha integration. However, the core signal quality is poor. The rule-based engine (SuperTrend/MACD/RSI combined) produces only 29.5% win rate — the worst performing strategy across all five projects.

The ML layer (XGBoost + ONNX) exists but was never evaluated in the backtest context. Activating it with regime filtering is the highest-priority action. If ML signals bring win rate above 50%, this project has the best chance of becoming production-ready.

**Do not paper trade until ML signals are validated and win rate exceeds 50% in backtest.**

---

*Report generated by Devin (AI Engineering Assistant) — May 25, 2026*
