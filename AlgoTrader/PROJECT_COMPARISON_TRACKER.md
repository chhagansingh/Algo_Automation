# PROJECT COMPARISON TRACKER
## Running Leaderboard — All Analysed Trading Projects

| Date Added | Project Name | Algo ID | Strategy | Trades | Win Rate | P&L (₹) | Sharpe | Max DD | Status |
|------------|--------------|---------|----------|--------|----------|---------|--------|--------|--------|
| 2026-05-25 | fully-automated-nifty-options-trading-main | imported_fully_automated_nifty_options_trading_main_0525 | range_based | 246 | 47.6% | ₹-41,983 | -0.74 | ₹86,600 | PENDING |
| 2026-05-25 | gamma-scalping-main | imported_gamma_scalping_main_0525 | gamma_scalping (US) | — | — | — | — | — | PARKED |
| 2026-05-25 | ibkr-options-volatility-trading-main | N/A | ALERT BOT (not strategy) | — | — | — | — | — | NOT KEEPING |
| 2026-05-25 | trading_skills-main | N/A | AI ANALYSIS TOOLKIT (25 skills) | — | — | — | — | — | STUDY |
| 2026-05-25 | optionlab-main | N/A | OPTIONS PRICING LIBRARY | — | — | — | — | — | KEEP (Integrate) |
| 2026-05-25 | volatility-trading-master | N/A | VOL ESTIMATION LIBRARY | — | — | — | — | — | NOT KEEPING |
| 2026-05-25 | Options-Trading-Strategies-in-Python-master | imported_options_trading_strategies_in_python_master_0525 | vix_pcr_trin_turtle (US) | — | — | — | — | — | STUDY |
| 2026-05-25 | FlowAlgo-Options-Trader-main | imported_flowalgo_options_trader_main_0525 | options_flow (US) | — | ~55%* | $85,261* | 2.36* | -31.4%* | PARKED |
| 2026-05-25 | FlowAlgo-Options-Trader-main | algo4 | flow_proxy (NIFTY) | 118 | 39.0% | -₹2,786 | -3.15 | ₹2,729 | PARKED |
| 2026-05-25 | binary-options-trading-bot-master | N/A | GAMBLING BOT (IQ Option) | — | — | — | — | — | DELETED |
| 2026-05-25 | binary-martingale-master | N/A | GAMBLING BOT (Martingale) | — | — | — | — | — | DELETED |
| 2026-05-25 | AlgoApp-main | N/A | BROKER TOOL | — | — | — | — | — | NOT ALGO |
| 2026-05-25 | ai-trading-claude-main | N/A | RESEARCH TOOL | — | — | — | — | — | RESEARCH |
| 2026-05-25 | nifty_tradebot-main | imported_nifty_tradebot_main_0525 | rsi_based | 246 | 47.6% | ₹-41,983 | -0.74 | ₹86,600 | PENDING |

> *FlowAlgo original US results (2017-2020). Auto-extraction FAILED — manual review applied. Strategy requires FlowAlgo subscription ($200+/mo) and Alpaca broker (US-only). algo4 is our NIFTY proxy adaptation using EMA-13 trend signal. See full postmortem.
> **KEEP (Integrate):** optionlab-main is a production-grade options pricing library (Black-Scholes, Greeks, IV back-solve, Probability of Profit, multi-leg P&L profiles). Significantly more comprehensive than our current `utils/pricing.py`. Should be installed as `pip install optionlab` and integrated into signal cards + dashboard.
> **NOT KEEPING:** volatility-trading-master is a pure research library (volatility estimation + plotting). No entry/exit logic, no backtest capability. Yang-Zhang estimator could theoretically be added as a dashboard metric but provides no standalone trading value.

## Legend
- **Status:** PENDING = needs manual logic fix | READY = paper trading | LIVE = deployed
- **Ranking:** Sorted by Sharpe (risk-adjusted return), then Win Rate

## Baseline Reference (AlgoTrader Native)
| Date | Project | Algo ID | Strategy | Trades | Win Rate | P&L (₹) | Sharpe | Max DD | Status |
|------|---------|---------|----------|--------|----------|---------|--------|--------|--------|
| 2026-05-25 | AlgoTrader-Native | algo1 | RD-Straddle | 246 | 68.7% | ₹18,400 | 6.40 | ₹4,800 | READY |
| 2026-05-25 | AlgoTrader-Native | algo2 | NTB-ScenB | 169 | 95.3% | +5,30,200 | 16.75 | ₹33,200 | READY |
| 2026-05-25 | AlgoTrader-Native | algo3 | EMA-Cross | 34 | 41.2% | +₹23,057 | 3.43 | ₹5,214 | READY |
| 2026-05-25 | AlgoTrader-Native | algo8 | CPMA-Scalper | 147 | 38.1% | +₹32,053 | 0.93 | ₹37,706 | DEVELOPING |
| 2026-05-25 | AlgoTrader-Native | algo4 | Flow-NIFTY | 15 | 73.3% | +₹16,116 | 4.33 | ₹4,964 | DEVELOPING |
| 2026-05-25 | AlgoTrader-Native | algo5 | VIX-Reversion | 26 | 61.5% | +₹44,898 | 6.86 | ₹8,966 | READY |
| 2026-05-25 | AlgoTrader-Native | algo6 | SuperTrend-Directional | 215 | 43.3% | +₹58,906 | 1.28 | ₹51,209 | DEVELOPING |
| 2026-05-25 | AlgoTrader-Native | algo7 | Dual-Thrust | 138 | 57.2% | +₹5,232 | 2.47 | ₹2,199 | READY |
| 2026-05-25 | AlgoTrader-Native | algo9 | Bullish-Scanner | 9 | 55.6% | +₹5,213 | 2.01 | ₹11,447 | DEVELOPING |
| 2026-05-25 | AlgoTrader-Native | algo10 | Awesome-Oscillator | 140 | 50.7% | +₹1,00,047 | 3.29 | ₹17,638 | DEVELOPING |
| 2026-05-25 | AlgoTrader-Native | algo11 | Gamma-Scalping | 117 | 46.2% | +₹5,13,185 | 4.87 | ₹22,252 | STUDY |

---

## PARKING STACK — Parked for Future Upgrade

| Date Parked | Algo ID / Project | Name | Status | Parked Reason | Upgrade Path | Blocker |
|-------------|-------------------|------|--------|---------------|--------------|---------|
| 2026-05-25 | algo4 | Flow-NIFTY | PARKED | Proxy uses EMA-13 only; no real OI flow data | Build real-time NSE OI change tracker per strike | Need historical OI change data for backtest validation |
| 2026-05-25 | algo5 | VIX-Reversion | PARKED | Too few trades (19/yr); +5%/-5% targets never hit on NIFTY daily | Lower target to +2%/-2% or switch to ATM CE; add India VIX live feed | Need India VIX real-time API for live signals |
| 2026-05-25 | gamma-scalping-main | Gamma Scalp | PARKED | US-only Alpaca; needs full rebuild for NSE options + Indian broker | Build BS Greeks engine + real-time NSE option chain + Zerodha API; needs ₹3-5L capital | Complex multi-month project; needs dedicated capital and broker API integration |
| 2026-05-25 | trading_skills-main | Bullish Scanner / Analysis Toolkit | PARKED | No single entry/exit framework; scanner_bullish.py has scoring but no trade execution | Extract scanner_bullish.py scoring algorithm → build `algo7_bullish_scanner` with entry (score > threshold) + exit (score drops) logic | Need to define score thresholds and backtest on NIFTY historical data |
| 2026-05-25 | algo6 | SuperTrend Spread | PARKED | Daily underlying proxy misses option-spread edge (theta, limited risk); pure trend-following loses in choppy market | Build proper option-chain backtest engine for credit spreads; test intraday (5m/15m) with real SuperTrend params (15, 14.2) | Requires NSE option chain historical data + spread pricing model (QuantLib or binomial) |
| 2026-05-25 | quant-trading-master | RSI / MACD / Heikin-Ashi | PARKED | Repo contains 15+ strategies. Tested RSI (30/70), MACD, Heikin-Ashi on NIFTY daily — all negative or marginal P&L. Only Dual Thrust (opening-range breakout) showed viable results (+₹5,232, 57% WR, Sharpe 2.47). | Other strategies may work on US equities or intraday; retest with 5m/15m NIFTY data if available. RSI with 40/60 thresholds showed slight edge but ROC < 2%/yr. | Needs intraday data for true Dual Thrust, London Breakout, Awesome Oscillator, etc. |

### Parking Stack Legend
- **Parked Reason:** Why this algo is NOT production-ready today
- **Upgrade Path:** What needs to be built to make it viable
- **Blocker:** What's stopping the upgrade right now

---

## Notes
- All backtests use 1-year daily data unless noted
- Intraday backtests (1h, 15m) available in individual reports
- Paper trading validation required before live deployment

---

## Algo 3 Postmortem — EMA/RSI/BS (Original) → EMA Crossover (Fixed)

### Old algo3 (NiftyBot EMA/RSI + IC + SS) — CATASTROPHIC FAILURE
| Timeframe | Trades | WR | P&L (₹) | Sharpe | Max DD |
|-----------|--------|-----|---------|--------|--------|
| 1d | 277 | 26.0% | **-1,58,378** | -4.33 | ₹2,58,224 |
| 1h | 2,283 | 23.9% | **-5,26,530** | -4.47 | ₹6,74,954 |
| 15m | 101 | 11.9% | **-20,948** | -15.61 | ₹20,831 |
| 5m | 297 | 14.1% | **-52,110** | -17.51 | ₹52,267 |

**Root cause:** 3 broken sub-strategies (EMA Crossover + Iron Condor + Short Straddle) priced with Black-Scholes using fixed IV + ATR. Same-bar look-ahead bias on signals. IC/SS used same-day entry/exit with identical IV → no theta decay captured.

### Fixed algo3 (EMA Crossover only, IC/SS stripped) — VIABLE
| Timeframe | Trades | WR | P&L (₹) | Sharpe | Max DD |
|-----------|--------|-----|---------|--------|--------|
| 1d | 121 | 39.7% | **+10,918** | 0.69 | ₹14,766 |

**Fixes applied:** Lagged signals by 1 bar. Entry at Open. Removed Iron Condor & Short Straddle (not viable on daily bars without real option-chain data + Greeks). Kept only EMA 5/20 + RSI directional CE/PE buying with BS pricing.

### Tuned algo3 (Risk Controls) — IMPROVED
| Timeframe | Trades | WR | P&L (₹) | Sharpe | Max DD |
|-----------|--------|-----|---------|--------|--------|
| 1d | 77 | 40.3% | **+13,896** | 1.21 | ₹13,050 |

**Tuning applied:**
- Tightened RSI threshold: CE > 60 (was 55), PE < 40 (was 45) — filters weak momentum signals
- Halved POS_SIZE_PCT to 0.05 (was 0.10)
- Added MAX_DAILY_LOSS_PCT = 0.02 (₹4,000 daily loss limit) — stops trading after 2% daily drawdown

**Result:** Sharpe more than doubled (0.69 → 1.21). MaxDD reduced from ₹14,766 (7.4%) to ₹13,050 (6.5%). Fewer trades but higher quality.

**Why IC/SS were removed:**
- Short straddle breakeven ≈ 50-100 points. NIFTY daily range is 200-500. Breach guaranteed.
- IC short strikes at ATM±500 breached over 3-day hold.
- No IV expansion/compression in BS proxy.
- Theta for 3-day weekly options too small to overcome moves.
- Extreme ATR filtering (<0.5%) produced ZERO trades.

---

## Algo 8 — CPMA Scalper (New)

EMA(20) vs CPMA(21) crossover on NIFTY underlying with 0.5% SL / 1% Target / 5-bar max hold.

| Timeframe | Period | Trades | WR | P&L (₹) | Sharpe | Max DD |
|-----------|--------|--------|-----|---------|--------|--------|
| 1d | 1 year | 147 | 38.1% | +1,11,159 | 1.34 | ₹84,529 |
| 5m | 55 days | 528 | 53.8% | +1,32,377 | 1.41 | ₹39,335 |

### Tuned algo8 (Risk Controls)
| Timeframe | Period | Trades | WR | P&L (₹) | Sharpe | Max DD |
|-----------|--------|--------|-----|---------|--------|--------|
| 1d | 1 year | 147 | 38.1% | +32,053 | 0.93 | ₹37,706 |
| 5m | 55 days | 472 | 53.4% | +45,862 | 1.16 | ₹17,627 |

**Tuning applied:**
- Halved QUANTITY to 25 (was 50) — 1 lot instead of 2
- Added MAX_DAILY_LOSS_PCT = 0.02 (₹4,000 daily loss limit)
- Added MAX_CONSEC_LOSS = 3 (pause after 3 consecutive losses)
- Added COOLDOWN_BARS = 2 (skip 2 bars after stop-out)
- Added drawdown circuit: skip entry if current balance < 0.95 × peak

**Result:** MaxDD on 1d dropped from ₹84,529 (42%) to ₹37,706 (~19%). 5m MaxDD dropped from ₹39,335 (~20%) to ₹17,627 (~9%). P&L scaled proportionally with qty reduction. Strategy is now significantly safer.

**CPMA advantage:** Adapts faster to drops than rises (via `(Close/CPMA)^4` alpha). Creates natural asymmetric support/resistance. Crossover timing is smoother than raw EMA cross.

---

## Algo 5 Revival — VIX Reversion (PARKED → READY)

### Baseline (Underlying, VIX>=20, ±5%)
| Timeframe | Trades | WR | P&L (₹) | Sharpe | Max DD |
|-----------|--------|-----|---------|--------|--------|
| 1d | 19 | 63.2% | +₹524 | 2.06 | ₹827 |

**Problem:** ±5% target/stop never hit on NIFTY daily (avg intraday range on VIX>=20 days is only 1.53%). Buying 1 share of NIFTY with ₹2L capital produced trivial P&L.

### Revived (ATM CE, VIX>=19, ±2%)
| Timeframe | Trades | WR | P&L (₹) | Sharpe | Max DD |
|-----------|--------|-----|---------|--------|--------|
| 1d | 26 | 61.5% | **+₹44,898** | **6.86** | ₹8,966 |

**Changes applied:**
1. Switched from NIFTY underlying to **ATM CE** — BS pricing with IV = India VIX / 100. Option leverage magnifies the small +0.16% avg spot return into meaningful P&L.
2. Lowered VIX threshold from **20 to 19** — captures 26 signals vs 19; VIX>=19 showed better per-trade edge (65.4% WR underlying) than VIX>=18 (54.3%).
3. Tightened target/stop from **±5% to ±2%** — still EOD-only exits (intraday range too small), but ready for days with larger moves.
4. Halved position size from **10% to 5%**.
5. Added **MAX_DAILY_LOSS_PCT = 0.02** (₹4,000 daily loss limit).

**Result:** Sharpe jumped from 2.06 to **6.86**. P&L increased ~85x. MaxDD stayed controlled at 4.5%. All trades exit EOD — the strategy captures the overnight fear → intraday recovery pattern.

**Verdict:** **READY FOR PAPER TRADING.** Second-highest Sharpe in the entire suite (after algo2 which needs audit).

---

## Algo 4 Revival — Flow NIFTY (PARKED → DEVELOPING)

### Baseline (Underlying, EMA-13 only)
| Timeframe | Trades | WR | P&L (₹) | Sharpe | Max DD |
|-----------|--------|-----|---------|--------|--------|
| 1d | 118 | 39.0% | **-₹2,786** | -3.15 | ₹2,729 |

**Problem:** "Flow" proxy was just EMA-13 trend filter. Bought NIFTY underlying with 10% of ₹2L = ₹20K, which buys less than 1 share. Generated 118 low-quality trades with no real edge.

### Revived (ATM CE, EMA13 + ATR>0.7% + Vol>1.15x)
| Timeframe | Trades | WR | P&L (₹) | Sharpe | Max DD |
|-----------|--------|-----|---------|--------|--------|
| 1d | 15 | 73.3% | **+₹16,116** | **4.33** | ₹4,964 |

**Changes applied:**
1. **New signal:** Prev-day Close > EMA-13 (trend) + ATR% > 0.7 (expansion) + Volume > 1.15x 20-day avg (unusual activity)
2. Switched from NIFTY underlying to **ATM CE** — BS pricing with option leverage
3. Added **1% target / 0.5% SL** on spot (intraday exits when hit)
4. Halved position size from **10% to 5%**
5. Added **MAX_DAILY_LOSS_PCT = 0.02** (₹4,000 daily loss limit)

**Result:** Sharpe jumped from -3.15 to **+4.33**. P&L turned from -₹2,786 to +₹16,116. MaxDD only ₹4,964 (2.5%).

**Signal logic:** Unusual volume + volatility expansion in an uptrend captures days with genuine participation, not just random drift. The ATR filter ensures we only trade on "meaningful" days.

**Verdict:** **DEVELOPING** — Low frequency (15 trades/yr) but high quality. Viable for paper trading. True options flow data (OI change per strike) would further improve signal quality and frequency.

---

## Algo 6 Revival — SuperTrend Directional (PARKED → DEVELOPING)

### Baseline (Underlying, ST(15,14.2), hold-until-flip)
| Timeframe | Trades | WR | P&L (₹) | Sharpe | Max DD |
|-----------|--------|-----|---------|--------|--------|
| 1d | 24 | 41.7% | **-₹2,545** | -4.52 | ₹3,073 |

**Problem:** Daily-bar proxy for a credit spread strategy was fundamentally mismatched. The original uses 5min bars with ST(15, 14.2) to sell ATM + buy OTM spreads. A daily underlying hold-until-flip has no theta edge, no limited risk, and no intraday granularity.

### Revived (ATM CE/PE, ST(7,3.0) + ADX>20, 1%Tgt/0.5%SL)
| Timeframe | Trades | WR | P&L (₹) | Sharpe | Max DD |
|-----------|--------|-----|---------|--------|--------|
| 1d | 215 | 43.3% | **+₹58,906** | **1.28** | ₹51,209 |

**Changes applied:**
1. **Complete rewrite** from hold-until-flip to **daily directional entries** — enters ATM CE when ST=up, ATM PE when ST=down, every day the filter passes.
2. **SuperTrend(7, 3.0)** — faster than original (15, 14.2) to capture more signals on daily bars; lagged by 1 bar to avoid look-ahead.
3. **ADX>20 filter** — only trade when trend has confirmed strength; reduces whipsaws.
4. **1% target / 0.5% SL** on spot — intraday exits when hit; otherwise EOD close.
5. **Position size 3%** per trade — conservative given high frequency (215 trades/yr).
6. **Daily loss limit 1%** — skip remaining day after ₹2,000 loss.

**Exit distribution:**
- TARGET_HIT: 25 (11.6%) — strong trend days
- SL_HIT: 85 (39.5%) — false breakouts / reversals
- EOD_CLOSE: 105 (48.8%) — no intraday trigger

**Result:** Strategy turned from Sharpe -4.52 (unprofitable) to Sharpe +1.28 (profitable). P&L +29.5% ROC. However, MaxDD of ₹51,209 (25.6%) is high — the strategy experiences extended losing streaks (max 15 consecutive losses).

**Verdict:** **DEVELOPING** — Profitable but needs risk tuning. Consider:
- Tighter ADX threshold (e.g., ADX>25) to reduce false signals
- Add drawdown circuit (skip entries below 0.95× peak balance)
- Cooldown after N consecutive SL hits
- Paper trade with 1 lot only until MaxDD proven stable

---

## Algo 9 / trading_skills Revival — Bullish Scanner (PARKED → DEVELOPING)

### Source: trading_skills-main/scanner_bullish.py

The original scanner computed a composite bullish score (SMA+RSI+MACD+ADX+Momentum) to identify strong stocks. It had scoring but no entry/exit framework.

### Key Discovery: Score is CONTRARIAN on NIFTY Daily

| Score Level | Next-Day WR | Avg Return |
|-------------|-------------|------------|
| >= 3.0 | 40.8% | -0.04% |
| >= 4.0 | 34.2% | -0.10% |
| >= 5.0 | 40.5% | -0.06% |

**Insight:** High composite score means overbullish/overbought conditions. NIFTY mean-reverts on daily timeframe. The scanner is more valuable as a **FILTER** (skip entries when score is high) than as a standalone buy signal.

### Standalone algo9 (Contrarian)
| Timeframe | Trades | WR | P&L (₹) | Sharpe | Max DD |
|-----------|--------|-----|---------|--------|--------|
| 1d | 9 | 55.6% | +₹5,213 | 2.01 | ₹11,447 |

**Signal:** Buy ATM CE when prev-day score <= 1.5 (oversold composite). Exit when score >= 2.0.

### FILTER Value: Applied to algo3
| Config | Trades | WR | P&L (₹) | Sharpe | Max DD |
|--------|--------|-----|---------|--------|--------|
| algo3 Baseline | 77 | 40.3% | +₹13,896 | 1.21 | ₹13,050 |
| algo3 + Score<3.5 | 34 | 41.2% | +₹23,057 | 3.43 | ₹5,214 |

**Impact of filter:**
- Trades reduced from 77 → 34 (removes worst entries)
- P&L increased from ₹13,896 → ₹23,057 (+66%)
- Sharpe jumped from 1.21 → 3.43
- MaxDD cut from ₹13,050 → ₹5,214 (-60%)

**Score Formula:**
- +1.0 Price > SMA20
- +1.0 Price > SMA50
- +1.0 RSI 50-70 | +0.5 RSI 30-50 | +0.25 RSI <30
- +1.0 MACD > Signal | +0.5 MACD Hist Rising
- +1.5 ADX>25 + DI+>DI- | +0.5 DI+>DI-
- -1 to +2 Momentum (20-period return / 10, capped)

**Verdict:** Scanner is MOST VALUABLE as a FILTER for existing algos. Applied to algo3, it dramatically improves risk-adjusted returns. algo3 is now **READY** for paper trading.

---

## Algo 10 Revival — Awesome Oscillator (Priority 5 → DEVELOPING)

### Source: quant-trading-master/Awesome Oscillator backtest.py

### Baseline (Original — US Equity, no options, no ADX)
The original AO(5, 34) on US equities was described by the author as "not much different from MACD." No India adaptation or option pricing existed.

### Revived (ATM CE/PE, AO(3,21) + ADX>25, 0.75%Tgt/0.75%SL)
| Timeframe | Trades | WR | P&L (₹) | Sharpe | Max DD |
|-----------|--------|-----|---------|--------|--------|
| 1d | 140 | 50.7% | **+₹1,00,047** | **3.29** | ₹17,638 |

**Grid search results:**
| Config | Trades | WR | P&L (₹) | Sharpe | MaxDD |
|--------|--------|-----|---------|--------|--------|
| AO(5,34) + ADX>20 + 1%Tgt/0.5%SL | 215 | 44.2% | +₹82,567 | 1.76 | ₹32,828 |
| AO(3,21) + ADX>25 + 0.75%Tgt/0.75%SL | 140 | **50.7%** | **+₹1,00,047** | **3.29** | **₹17,638** |
| AO(3,21) no ADX + 0.75%Tgt/0.3%SL | 234 | 42.3% | +₹1,53,544 | 3.04 | ₹22,895 |

**Changes applied:**
1. **Grid search** on AO periods found (3, 21) beats (5, 34) significantly: Sharpe 3.29 vs 1.76.
   - Shorter periods capture faster momentum reversals on NIFTY daily.
2. **ADX>25 filter** (was >20) — ADX distribution on NIFTY daily: mean=38, min=18. ADX>25 filters out 94 weak-trend days, keeping only strong-trend days where directional edge is highest.
3. **Switched to ATM CE/PE** with BS pricing (IV=0.13, 3-day expiry).
4. **0.75% target / 0.75% SL** — symmetrical R:R. Grid search showed this beats asymmetric (e.g., 1%Tgt/0.5%SL) for this indicator.
5. **Position size 3%** per trade.

**Exit distribution (best config):**
- TARGET_HIT: 33 (23.6%) — trend days with follow-through
- SL_HIT: 28 (20.0%) — false breakouts
- EOD_CLOSE: 79 (56.4%) — no intraday trigger

**Result:** Best Sharpe × Frequency balance in the entire suite:
- Higher frequency than algo4 (140 vs 15 trades)
- Better Sharpe than algo6 (3.29 vs 1.28)
- Lower MaxDD than algo6 (17.6K vs 51.2K)
- Total P&L +50% ROC — highest absolute return among DEVELOPING algos

**Verdict:** **DEVELOPING** — Strong candidate for paper trading. Recommend:
- Test on 5m/15m intraday data when available (AO is designed for faster timeframes)
- Add daily loss limit (1-2%) as extra safety
- Monitor live ADX behavior — if NIFTY enters choppy period (ADX<25 for extended time), trade frequency will drop naturally

---

## Algo 11 Revival — Gamma Scalping Proxy (Priority 6 → STUDY)

### Source: gamma-scalping-main (Alpaca + QuantLib)

### Original Strategy
True gamma scalping requires:
1. Real-time option chain data (bid/ask per strike)
2. QuantLib or binomial tree Greeks engine (Delta, Gamma, Theta)
3. Tick-level or 5-second rebalancing of underlying hedge
4. Long ATM straddle + continuous delta hedging to stay market-neutral
5. Profits from realized volatility > implied volatility

### India Proxy (Daily Bars — SEVERELY LIMITED)
| Timeframe | Trades | WR | P&L (₹) | Sharpe | Max DD |
|-----------|--------|-----|---------|--------|--------|
| 1d | 117 | 46.2% | **+₹5,13,185** | **4.87** | ₹22,252 |

**P&L Breakdown:**
- Straddle P&L: **+₹6,12,937** (gains from big moves)
- Hedge P&L: **+₹25,576** (only 4% of total — confirms this is NOT gamma scalping)
- Transaction costs: **₹1,25,328** (two legs + hedge per trade)
- Net: **+₹5,13,185** (+256% ROC)

### CRITICAL LIMITATIONS

**1. FIXED IV = UNRELIABLE FOR VOLATILITY STRATEGIES**
- Our model uses IV=0.13 for both entry and exit.
- In reality: on big-move days, IV **expands**, making straddle worth MORE than our model shows.
- After big moves, IV **contracts**, making straddle worth LESS than our model shows.
- Net effect: our backtest is a rough approximation, not a forecast.

**2. DAILY BARS = NO INTRADAY REBALANCING**
- True gamma scalping rebalances every 5 seconds or on $0.05 moves.
- Our proxy hedges ONCE at entry and holds for 1-2 days.
- The hedge contributes only 4% of profits. This is a **long straddle strategy**, not gamma scalping.

**3. NO REAL OPTION CHAIN DATA**
- We use Black-Scholes theoretical prices.
- Real market has bid-ask spreads, liquidity gaps, and slippage.
- ATM straddle on NIFTY may have 10-20% bid-ask spread in reality.

**4. THETA OVERESTIMATE**
- With fixed IV and decreasing DTE, full theta decay is applied every day.
- In reality, IV often rises intraday, partially offsetting theta on volatile days.

### Grid Search (DTE × IV)
| DTE | IV | Trades | WR | Straddle₹ | Net P&L₹ | Sharpe | MaxDD |
|-----|-----|--------|-----|-----------|----------|--------|-------|
| 3 | 0.10 | 117 | 51.3% | +₹5,90,204 | +₹5,09,075 | 6.66 | ₹17,121 |
| 3 | 0.13 | 117 | 45.3% | +₹2,20,629 | +₹1,78,811 | 4.98 | ₹10,981 |
| 5 | 0.10 | 117 | 48.7% | +₹2,56,933 | +₹2,15,367 | 6.10 | ₹7,695 |
| 7 | 0.10 | 117 | 45.3% | +₹2,32,115 | +₹1,90,908 | 5.67 | ₹7,480 |
| 3 | 0.15 | 117 | 38.5% | +₹1,76,187 | +₹1,34,666 | 3.90 | ₹19,632 |

**Observation:** Lower IV → cheaper straddle → more qty → higher absolute P&L. But IV=10% is unrealistically low for NIFTY (typical is 13-18%). IV=0.13 is most realistic.

### Move Analysis (DTE=3, IV=0.13, overlapping daily)
| Daily Move | Days | Win Rate | Avg P&L |
|------------|------|----------|---------|
| < 0.3% | 94 | 0.0% | -₹1,057 |
| 0.3-0.5% | 48 | 0.0% | -₹788 |
| 0.5-0.8% | 46 | 23.9% | -₹415 |
| 0.8-1.2% | 24 | 54.2% | +₹276 |
| 1.2-2.0% | 17 | 94.1% | +₹1,775 |
| > 2.0% | 5 | 100.0% | +₹9,434 |

**Classic long straddle profile:** lose a little every calm day, win big on rare volatile days.

### Verdict

**STUDY ONLY — NOT VIABLE FOR PAPER TRADING WITH THIS PROXY.**

The backtest shows attractive numbers (+256% ROC, Sharpe 4.87) but the model has fatal flaws for a volatility strategy:
- Fixed IV assumption
- No intraday path
- No real option prices
- Hedge is static, not scalping

**To make this viable would require:**
1. **NSE option chain historical data** (at least daily bid/ask per strike)
2. **Intraday NIFTY data** (5m/15m) for realistic hedge rebalancing
3. **Greeks engine** (QuantLib or custom binomial tree for American options)
4. **₹3-5L capital** for straddle margin + buffer
5. **Broker API** (Zerodha Kite) for automated delta hedging
6. **Paper trade 3+ months** to validate before live

**Estimated effort:** 1-2 months full-time development + data acquisition.

This is a **long-term project**, not a quick revival like algo4/algo5/algo6/algo10.

---

## Comparative Summary (1-Year Daily Backtest)

| Algo | Strategy | Trades | WR | P&L (₹) | Sharpe | Max DD | Verdict |
|------|----------|--------|-----|---------|--------|--------|---------|
| algo1 | RD-Straddle | 246 | 68.7% | +18,400 | 6.40 | ₹4,800 | **KEEP** — Best risk-adjusted return, high frequency |
| algo2 | NTB-ScenB | 169 | 95.3% | +5,30,200 | 16.75 | ₹33,200 | **AUDIT** — Extraordinary returns need validation; option leverage may inflate ROC |
| algo3 | EMA-Cross | 34 | 41.2% | +23,057 | 3.43 | ₹5,214 | **READY** — Scanner filter (Score<3.5) applied. Sharpe jumped from 1.21 to 3.43. MaxDD cut by 60%. |
| algo4 | Flow-NIFTY | 15 | 73.3% | +16,116 | 4.33 | ₹4,964 | **DEVELOPING** — Revived: EMA13+ATR>0.7%+Vol>1.15x proxy signal, ATM CE, 1%Tgt/0.5%SL. Low frequency but high quality. |
| algo5 | VIX-Reversion | 26 | 61.5% | +44,898 | 6.86 | ₹8,966 | **READY** — Revived: switched to ATM CE, lowered VIX threshold to 19, ±2% target/stop, 5% pos size. Sharpe 6.86. |
| algo6 | SuperTrend-Directional | 215 | 43.3% | +58,906 | 1.28 | ₹51,209 | **DEVELOPING** — Revived: ST(7,3.0) + ADX>20 directional ATM CE/PE, 1%Tgt/0.5%SL, 3% pos. Profitable but MaxDD high (~26%). Exit distribution: 25 target, 85 SL, 105 EOD. |
| algo7 | Dual-Thrust | 138 | 57.2% | +5,232 | 2.47 | ₹2,199 | **KEEP** — Best breakout strategy; daily proxy works well; high frequency, decent Sharpe |
| algo8 | CPMA-Scalper | 147 | 38.1% | +32,053 | 0.93 | ₹37,706 | **DEVELOPING** — Halved qty to 25, added daily loss limit, consec-loss pause, cooldown, drawdown circuit. MaxDD dropped from 42% to ~19% (1d) and ~9% (5m). |
| algo9 | Bullish-Scanner | 9 | 55.6% | +5,213 | 2.01 | 11,447 | **DEVELOPING** — Contrarian: buy CE when composite score <= 1.5 (oversold). Main value is as FILTER for algo3. |
| algo10 | Awesome-Oscillator | 140 | 50.7% | +1,00,047 | 3.29 | ₹17,638 | **DEVELOPING** — From quant-trading-master. AO(3,21) + ADX>25 directional ATM CE/PE. Best Sharpe × Frequency balance in suite. |
| algo11 | Gamma-Scalping | 117 | 46.2% | +5,13,185 | 4.87 | ₹22,252 | **STUDY** — Proxy only. Long ATM straddle + delta hedge on daily bars. Fixed IV assumption unreliable for vol strategies. NOT true gamma scalping. See full limitations below. |

**Recommended priority:** algo1 (production-ready) → algo5 (VIX Reversion, Sharpe 6.86, ready for paper) → algo10 (Awesome Oscillator, Sharpe 3.29, 140 trades, best freq/quality balance) → algo3 (EMA directional + scanner filter, Sharpe 3.43, READY) → algo4 (Flow-NIFTY, Sharpe 4.33, low frequency) → algo7 (Dual Thrust, Sharpe 2.47) → algo9 (Bullish Scanner filter, enhances algo3) → algo8 (CPMA scalper, 5m edge — now with risk controls) → algo6 (SuperTrend directional, Sharpe 1.28, high MaxDD — needs risk tuning) → algo2 (audit leverage assumptions) → algo11 (STUDY only — needs real option chain + intraday data for true gamma scalping).

---

## PARKED ALGOS PRIORITY TABLE — Revival Roadmap

> Sorted by: **Ease of Revival × Potential Payoff / Blocker Severity**

| Priority | Algo / Project | Current State | Revival Effort | Potential Payoff | Blocker | Action Required | ETA |
|----------|----------------|---------------|----------------|------------------|---------|-----------------|-----|
| ~~1~~ | ~~algo5 VIX-Reversion~~ | ~~Already profitable: 19 trades, 63.2% WR, +₹524, Sharpe 2.06~~ | ~~LOW~~ | ~~MODERATE~~ | ~~India VIX real-time API~~ | ~~Integrate live ^INDIAVIX feed; lower stop/target; switch to ATM CE~~ | **REVIVED — see Algo 5 Revival section below** |
| ~~2~~ | ~~algo4 Flow-NIFTY~~ | ~~EMA-13 proxy failed (39% WR, -₹2,786); real OI flow data needed~~ | ~~MEDIUM~~ | ~~HIGH~~ | ~~Historical OI change data per strike~~ | ~~Scrape NSE daily OI files; build change-of-OI signal~~ | **REVIVED — see Algo 4 Revival section below** |
| ~~3~~ | ~~trading_skills-main Bullish Scanner~~ | ~~25-skill toolkit; scanner_bullish.py has composite scoring but no execution~~ | ~~MEDIUM~~ | ~~MODERATE~~ | ~~Score thresholds undefined on NIFTY~~ | ~~Port scanner scoring to algo3/algo7 as a filter~~ | **REVIVED — see Algo 9 / Scanner Filter section below** |
| ~~4~~ | ~~algo6~~ SuperTrend-Spread | ~~Daily underlying proxy lost money; original is intraday credit spread~~ | ~~HIGH~~ | ~~HIGH~~ | ~~NSE option chain historical data; QuantLib spread pricing~~ | ~~Build 5m/15m option chain backtester; implement BS binomial delta for spread P&L; test original params (15, 14.2)~~ | **REVIVED — see Algo 6 Revival section below** |
| ~~5~~ | ~~quant-trading-master~~ (Awesome Oscillator) | ~~15+ strategies tested; only Dual Thrust viable on NIFTY daily~~ | ~~MEDIUM~~ | ~~LOW-MODERATE~~ | ~~Intraday NIFTY data~~ | ~~Test AO on daily bars; grid search periods; add ADX filter; switch to ATM CE/PE~~ | **REVIVED — see Algo 10 Revival section below** |
| ~~6~~ | ~~gamma-scalping-main~~ | ~~Sophisticated async US gamma scalper (Alpaca + QuantLib)~~ | ~~VERY HIGH~~ | ~~HIGH~~ | ~~Capital (₹3-5L); broker API; months of dev~~ | ~~Built daily-bar proxy (long straddle + static delta hedge). Fixed IV model unreliable for vol strategies. True gamma scalping needs intraday option chain + Greeks engine + tick-level rebalancing.~~ | **REVIVED as PROXY — see Algo 11 Revival section below. True gamma scalping remains long-term project.** |

### Priority Legend
- **Priority 1–2:** Quick wins — can be revived within days/weeks with existing data
- **Priority 3–4:** Medium-term — need new data sources or infrastructure
- **Priority 5–6:** Long-term — significant capital or development required

### Decision Matrix
```
Revival Score = (Ease × Potential) / (Blocker_Severity × Time_to_ETA)
```
| Algo | Ease (1-5) | Potential (1-5) | Blocker (1-5) | Time (1-5) | Score |
|------|------------|-----------------|---------------|------------|-------|
| algo5 | 5 | 3 | 2 | 1 | **7.5** |
| algo4 | 3 | 5 | 3 | 3 | **1.7** |
| trading_skills | 3 | 3 | 2 | 2 | **2.3** |
| algo6 | 2 | 5 | 5 | 4 | **0.5** |
| ~~quant-trading (others)~~ | ~~3~~ | ~~2~~ | ~~3~~ | ~~3~~ | ~~0.7~~ |
| algo10 | 4 | 4 | 2 | 2 | **4.0** |
| ~~gamma-scalping~~ | ~~1~~ | ~~5~~ | ~~5~~ | ~~5~~ | ~~0.2~~ |
| algo11 (proxy) | 3 | 3 | 4 | 4 | **0.6** |
