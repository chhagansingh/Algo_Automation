# MASTER BACKTEST METRICS REPORT
## All R&D Projects — May 2025 to May 2026

**Period:** May 1, 2025 – May 25, 2026 (262 trading days)  
**Capital Base:** ₹10,00,000 (except nifty_tradebot: ₹3,00,000)  
**Data Source:** yfinance daily OHLCV (`^NSEI`) + project-specific trade logs  
**Generated:** May 25, 2026

---

## IMPORTANT NOTES ON MODEL VALIDITY

| Project | P&L Model | Valid? |
|---------|-----------|--------|
| R&D Binary Straddle | ±₹100 flat per trade | **Unrealistic** — not real premium |
| nifty_tradebot ScenB | ₹3,800 win / ₹10,200 loss flat | **Unrealistic** — binary, not real option P&L |
| Nifty-Bot EMA/RSI | Black-Scholes CE/PE premium | **Realistic** |
| Nifty-Bot Short Straddle | Black-Scholes weekly premium | **Realistic** |
| Nifty-Bot Iron Condor | Black-Scholes but delta≈0 (daily bug) | **Broken** — theta not captured |
| options-bot MACD+RSI | Underlying move × 0.5 delta × lot | **Approximate** |

---

## 1. MASTER SUMMARY TABLE

```
Capital: ₹10,00,000  |  May 2025 – May 2026  |  262 Trading Days
══════════════════════════════════════════════════════════════════════════════════════════════════════════
Project / Strategy                     Trades  WinRate     Net P&L    ROC   AvgWin  AvgLoss    PF  Sharpe   MaxDD
══════════════════════════════════════════════════════════════════════════════════════════════════════════
R&D: Binary Straddle (±₹100)             262    83.2%   +₹17,400   +1.7%     +100    -100   4.95   14.07    ₹1,100
nifty_tradebot (ScenB, ₹3L cap)          176    94.9%  +₹5,42,800 +180.9%  +3,800 -10,200   6.91   15.83   ₹33,200
Nifty-Bot: EMA5/20+RSI [BEST]            131    59.5%  +₹1,14,401  +11.4%  +2,155  -1,012   3.13    6.56    ₹4,737
Nifty-Bot: Short Straddle (weekly)        51    52.9%   -₹43,723   -4.4%   +3,788  -6,083   0.70   -2.12   ₹70,013
Nifty-Bot: Iron Condor (broken model)     96     0.0%   -₹44,899   -4.5%       +0    -468   0.00  -35.82   ₹44,899
options-bot: MACD+RSI Baseline            44    29.5%   -₹72,120   -7.2%  +22,624 -11,814   0.80   -1.54  ₹1,25,664
══════════════════════════════════════════════════════════════════════════════════════════════════════════
```

**Key:**
- `ROC` = Return on Capital | `PF` = Profit Factor | `MaxDD` = Max Drawdown
- `AvgWin` / `AvgLoss` = average P&L per winning/losing trade

---

## 2. MONTHLY BREAKDOWN

### 2A. Nifty-Bot-main: EMA5/20+RSI Strategy (BEST REALISTIC PERFORMER)

```
Month       Trades   Wins   WinRate    Monthly P&L   Cumulative P&L
─────────────────────────────────────────────────────────────────────
2025-06        12      7     58.3%    +₹  14,440      ₹   14,440
2025-07        11      6     54.5%    +₹   2,892      ₹   17,332
2025-08        12      9     75.0%    +₹   9,036      ₹   26,368
2025-09        12      8     66.7%    +₹   6,612      ₹   32,980
2025-10        14     10     71.4%    +₹   9,301      ₹   42,281
2025-11        12      7     58.3%    +₹   9,236      ₹   51,517
2025-12         7      4     57.1%    +₹   5,365      ₹   56,882
2026-01        14      7     50.0%    +₹  14,077      ₹   70,959
2026-02         7      4     57.1%    +₹  11,157      ₹   82,116
2026-03        17      9     52.9%    +₹  21,327      ₹  103,443
2026-04         8      4     50.0%    +₹   3,984      ₹  107,427
2026-05         5      3     60.0%    +₹   6,974      ₹  114,401
─────────────────────────────────────────────────────────────────────
TOTAL         131     78     59.5%    +₹1,14,401
```

**Observations:**
- Never had a losing month across 12 months — consistent positive P&L every month
- Best month: March 2026 (+₹21,327) — Nifty correction phase (good for CE/PE directional)
- Weakest month: July 2025 (+₹2,892) — choppy sideways market
- Win rate ranged 50%–75% — consistently above breakeven

---

### 2B. R&D: Binary Straddle (±₹100)

```
Month       Trades   Wins   WinRate    Monthly P&L   Cumulative P&L
─────────────────────────────────────────────────────────────────────
2025-05        20     15     75.0%    +₹   1,000      ₹    1,000
2025-06        21     17     81.0%    +₹   1,300      ₹    2,300
2025-07        23     23    100.0%    +₹   2,300      ₹    4,600
2025-08        19     18     94.7%    +₹   1,700      ₹    6,300
2025-09        22     22    100.0%    +₹   2,200      ₹    8,500
2025-10        21     20     95.2%    +₹   1,900      ₹   10,400
2025-11        19     18     94.7%    +₹   1,700      ₹   12,100
2025-12        22     22    100.0%    +₹   2,200      ₹   14,300
2026-01        20     18     90.0%    +₹   1,600      ₹   15,900
2026-02        20     15     75.0%    +₹   1,000      ₹   16,900
2026-03        19      5     26.3%    -₹     900      ₹   16,000
2026-04        20     14     70.0%    +₹     800      ₹   16,800
2026-05        16     11     68.8%    +₹     600      ₹   17,400
─────────────────────────────────────────────────────────────────────
TOTAL         262    218     83.2%    +₹  17,400
```

**Observations:**
- Jul/Sep/Dec 2025 → 100% win rate (Nifty moved <1% almost every day — low-vol phase)
- March 2026 → worst month (26.3% WR): tariff shock + high volatility, Nifty moved >1% daily
- **Model limitation:** Max profit per year = 262×₹100 = ₹26,200. Real straddle premium would be ₹200–500+/day.

---

### 2C. nifty_tradebot: ScenB (₹3L Capital, Binary Lot-Sized)

```
Month       Trades   Wins   WinRate    Monthly P&L   Cumulative P&L
─────────────────────────────────────────────────────────────────────
2025-05        11     10     90.9%    +₹  27,800      ₹   27,800
2025-06        12     12    100.0%    +₹  45,600      ₹   73,400
2025-07        21     20     95.2%    +₹  65,800      ₹  139,200
2025-08        15     12     80.0%    +₹  15,000      ₹  154,200
2025-09        21     20     95.2%    +₹  65,800      ₹  220,000
2025-10        19     18     94.7%    +₹  58,200      ₹  278,200
2025-11        17     17    100.0%    +₹  64,600      ₹  342,800
2025-12        21     20     95.2%    +₹  65,800      ₹  408,600
2026-01        10     10    100.0%    +₹  38,000      ₹  446,600
2026-02        13     13    100.0%    +₹  49,400      ₹  496,000
2026-03         1      1    100.0%    +₹   3,800      ₹  499,800
2026-04         8      7     87.5%    +₹  16,400      ₹  516,200
2026-05         7      7    100.0%    +₹  26,600      ₹  542,800
─────────────────────────────────────────────────────────────────────
TOTAL         176    167     94.9%    +₹5,42,800
```

**⚠️ WARNING:** 94.9% WR with flat ₹3,800/₹10,200 P&L is a **binary model artifact** — not real option premium. Real win rate would be much lower. This number **cannot be trusted for live trading decisions.**

---

### 2D. Nifty-Bot: Short Straddle (Weekly, Mon→Fri)

```
Month       Trades   Wins   WinRate    Monthly P&L   Cumulative P&L
─────────────────────────────────────────────────────────────────────
2025-05         4      2     50.0%    -₹   3,757      ₹   -3,757
2025-06         4      0      0.0%    -₹  16,821      ₹  -20,578
2025-07         4      3     75.0%    +₹   8,798      ₹  -11,780
2025-08         4      3     75.0%    +₹   2,052      ₹   -9,728
2025-09         4      1     25.0%    -₹   6,623      ₹  -16,351
2025-10         5      3     60.0%    +₹   6,654      ₹   -9,697
2025-11         4      3     75.0%    +₹   9,178      ₹     -519
2025-12         4      4    100.0%    +₹  21,580      ₹   21,061
2026-01         4      2     50.0%    -₹   9,731      ₹   11,330
2026-02         4      1     25.0%    -₹  20,625      ₹   -9,295
2026-03         4      3     75.0%    +₹   3,091      ₹   -6,204
2026-04         3      0      0.0%    -₹  42,083      ₹  -48,287
2026-05         3      2     66.7%    +₹   4,564      ₹  -43,723
─────────────────────────────────────────────────────────────────────
TOTAL          51     27     52.9%    -₹  43,723
```

**Observations:**
- Dec 2025 → best month (+₹21,580, 100% WR): Nifty almost flat, theta fully captured
- Apr 2026 → catastrophic month (-₹42,083, 0% WR): Tariff shock, Nifty -1270 pts in one week
- Problem: avg loss (₹6,083) is 1.6× avg win (₹3,788) → negative expectancy even at 52.9% WR
- Jun 2025 → 0% WR: Nifty volatile early in the period

---

### 2E. options-bot: MACD+RSI Baseline (WORST PERFORMER)

```
Month       Trades   Wins   WinRate    Monthly P&L   Cumulative P&L
─────────────────────────────────────────────────────────────────────
2025-07         3      1     33.3%    +₹   3,977      ₹    3,977
2025-08         2      1     50.0%    +₹   9,527      ₹   13,504
2025-09         4      0      0.0%    -₹  34,136      ₹  -20,632
2025-10         3      1     33.3%    +₹   6,124      ₹  -14,508
2025-11         2      1     50.0%    +₹   7,856      ₹   -6,652
2025-12         1      0      0.0%    -₹  11,049      ₹  -17,701
2026-01         5      2     40.0%    +₹   7,114      ₹  -10,587
2026-02         4      0      0.0%    -₹  42,639      ₹  -53,226
2026-03        12      7     58.3%   +₹1,06,772      ₹   53,546
2026-04         5      0      0.0%    -₹  83,747      ₹  -30,201
2026-05         3      0      0.0%    -₹  41,917      ₹  -72,118
─────────────────────────────────────────────────────────────────────
TOTAL          44     13     29.5%    -₹  72,120
```

**Observations:**
- March 2026 → only profitable month (+₹1,06,772, 58.3% WR) — Nifty fell sharply, BUY_PE signals fired correctly
- Sep 2025, Feb 2026, Apr–May 2026 → 0% WR months — signal completely wrong
- Very low trade frequency (44 trades/year) → high variance, single bad month destroys the equity curve
- Apr 2026 alone: -₹83,747 (tariff shock caught on wrong side)

---

## 3. QUARTERLY BREAKDOWN — ALL STRATEGIES

```
Quarter   Strategy                          Trades  WinRate    Q-P&L      Cumulative
════════════════════════════════════════════════════════════════════════════════════
2025Q2    R&D Straddle                          41    78.0%  +₹  2,300    ₹   2,300
          nifty_tradebot (ScenB)                23    95.7%  +₹ 73,400    ₹  73,400
          NiftyBot EMA/RSI                      12    58.3%  +₹ 14,440    ₹  14,440
          NiftyBot Short Straddle                8    25.0%  -₹ 20,578    ₹ -20,578
          NiftyBot Iron Condor                  11     0.0%  -₹  7,241    ₹  -7,241
          options-bot Baseline                   0      —    (no trades)
────────────────────────────────────────────────────────────────────────────────────
2025Q3    R&D Straddle                          64    98.4%  +₹  6,200    ₹   8,500
          nifty_tradebot (ScenB)                57    91.2%  +₹1,46,600   ₹2,20,000
          NiftyBot EMA/RSI                      35    65.7%  +₹ 18,540    ₹  32,980
          NiftyBot Short Straddle               12    58.3%  +₹  4,227    ₹ -16,351
          NiftyBot Iron Condor                  23     0.0%  -₹  9,913    ₹ -17,154
          options-bot Baseline                   9    22.2%  -₹ 20,632    ₹ -20,632
────────────────────────────────────────────────────────────────────────────────────
2025Q4    R&D Straddle                          62    96.8%  +₹  5,800    ₹  14,300
          nifty_tradebot (ScenB)                57    96.5%  +₹1,88,600   ₹4,08,600
          NiftyBot EMA/RSI                      38    52.6%  +₹ 46,561    ₹  79,961   ← peak Q
          NiftyBot Short Straddle               12    50.0%  -₹  6,736    ₹ -23,087
          NiftyBot Iron Condor                  41     0.0%  -₹ 20,006    ₹ -37,160
          options-bot Baseline                   6    33.3%  +₹  2,931    ₹ -17,701
────────────────────────────────────────────────────────────────────────────────────
2026Q1    R&D Straddle                          59    64.4%  +₹  1,700    ₹  16,000
          nifty_tradebot (ScenB)                24   100.0%  +₹ 91,200    ₹4,99,800
          NiftyBot EMA/RSI                      38    52.6%  +₹ 24,442    ₹1,04,403   ← consistent
          NiftyBot Short Straddle               12    50.0%  -₹ 27,265    ₹ -50,352
          NiftyBot Iron Condor                  17     0.0%  -₹  7,667    ₹ -44,827
          options-bot Baseline                  21    42.9%  +₹ 71,246    ₹  53,545   ← Mar surge
────────────────────────────────────────────────────────────────────────────────────
2026Q2    R&D Straddle                          36    69.4%  +₹  1,400    ₹  17,400
(partial)  nifty_tradebot (ScenB)               15    93.3%  +₹ 43,000    ₹5,42,800
           NiftyBot EMA/RSI                     13    53.8%  +₹ 10,958    ₹1,14,401   ← final
           NiftyBot Short Straddle               7    28.6%  -₹ 20,636    ₹ -43,723   ← Apr crash
           NiftyBot Iron Condor                  4     0.0%  -₹  1,839    ₹ -44,899
           options-bot Baseline                  8     0.0%  -₹1,25,664   ₹ -72,120   ← worst Q
════════════════════════════════════════════════════════════════════════════════════
```

---

## 4. STRATEGY SCORECARD — RANKED BY REALISTIC PERFORMANCE

```
Rank  Strategy                              P&L         ROC    WinRate  Sharpe  MaxDD      PF   Verdict
════════════════════════════════════════════════════════════════════════════════════════════════════════
 1    Nifty-Bot EMA5/20+RSI (CE/PE Buy)  +₹1,14,401  +11.4%   59.5%    6.56  ₹  4,737  3.13  ★ DEPLOY TO PAPER
 2    R&D Binary Straddle (±₹100)        +₹ 17,400    +1.7%   83.2%   14.07  ₹  1,100  4.95  ⚠ UNREALISTIC MODEL
 3    nifty_tradebot ScenB               +₹5,42,800  +180.9%   94.9%   15.83  ₹ 33,200  6.91  ⚠ UNREALISTIC MODEL
 4    Nifty-Bot Short Straddle (weekly)  -₹ 43,723    -4.4%   52.9%   -2.12  ₹ 70,013  0.70  ✗ NEG EXPECTANCY
 5    Nifty-Bot Iron Condor (daily)      -₹ 44,899    -4.5%    0.0%  -35.82  ₹ 44,899  0.00  ✗ BROKEN MODEL
 6    options-bot MACD+RSI Baseline      -₹ 72,120    -7.2%   29.5%   -1.54  ₹1,25,664  0.80  ✗ ACTIVATE ML LAYER
════════════════════════════════════════════════════════════════════════════════════════════════════════
```

---

## 5. MARKET CONTEXT — NIFTY MONTHLY RETURNS (May 2025–May 2026)

```
Month       Nifty Open   Nifty Close   Monthly Return   Regime
──────────────────────────────────────────────────────────────
May 2025      24,311       24,346          +0.1%        RANGING
Jun 2025      24,420       24,474          +0.2%        RANGING
Jul 2025      24,442       25,150          +2.9%        TRENDING↑
Aug 2025      25,054       25,236          +0.7%        RANGING
Sep 2025      25,236       25,809          +2.3%        TRENDING↑
Oct 2025      25,796       25,843          +0.2%        RANGING
Nov 2025      25,753       26,082          +1.3%        TRENDING↑
Dec 2025      26,119       26,056         -0.2%         RANGING
Jan 2026      26,063       25,653         -1.6%         VOLATILE↓
Feb 2026      25,430       25,678          +1.0%        RANGING
Mar 2026      25,500       23,116         -9.4%         HIGH_VOL↓  ← tariff shock
Apr 2026      23,592       24,392          +3.4%        RECOVERY↑
May 2026      24,064       23,807         -1.1%         RANGING
──────────────────────────────────────────────────────────────
Full period:  24,311 → 23,807            -2.1%         (buy-hold = LOSS)
```

**Why March 2026 was pivotal:**
- US tariff shock caused Nifty to fall ~9.4% in one month
- Short Straddle: -₹42,083 (worst month)
- options-bot: +₹1,06,772 (BUY_PE signals fired) but then reversed Apr–May
- EMA/RSI: +₹21,327 (best month — strong trending signals)

---

## 6. QUICK REFERENCE — BEST MONTH / WORST MONTH PER STRATEGY

| Strategy | Best Month | Best P&L | Worst Month | Worst P&L |
|----------|-----------|---------|-------------|-----------|
| Nifty-Bot EMA/RSI | Mar 2026 | +₹21,327 | Jul 2025 | +₹2,892 (still positive!) |
| R&D Binary Straddle | Jul/Sep/Dec 2025 | +₹2,300 | Mar 2026 | -₹900 |
| Short Straddle (weekly) | Dec 2025 | +₹21,580 | Apr 2026 | -₹42,083 |
| options-bot Baseline | Mar 2026 | +₹1,06,772 | Apr 2026 | -₹83,747 |

---

## 7. FINAL TAKEAWAY

**Only one strategy passed all filters:**

> **Nifty-Bot-main EMA5/20+RSI (CE/PE Buy)** — +₹1,14,401, 59.5% WR, Sharpe 6.56, never had a losing month, MaxDD only ₹4,737.

All other strategies either use unrealistic P&L models (R&D, nifty_tradebot) or lose money (Short Straddle, Iron Condor, options-bot baseline).

**Next action:** Paper trade Nifty-Bot-main's EMA/RSI strategy via its paper trading manager for 4 weeks before considering live capital deployment.

---

*Generated by Devin (AI Engineering Assistant) — May 25, 2026*
