"""
AlgoTrader — Algo 15: Aggregate Score (Dynamic Weighted Multi-Indicator)
Source: freqAI-LSTM-main (Freqtrade freqAI module by Netanelshoshan)

Original Strategy (Crypto Futures):
  - 10+ technical indicators → z-score normalization → dynamic weighting
  - Aggregate score S with market regime filter + volatility adjustment
  - LSTM regression to predict target score
  - Entry/exit via threshold comparison on predicted score

Why Chosen:
  - First multi-factor composite scoring system in the suite
  - Combines 9 normalized indicators with dynamic momentum boost
  - Volatility-adjusted signals reduce chop during high-vol periods
  - Rule-based aggregate score outperformed the LSTM enhancement on NIFTY
  - Asymmetric thresholds (CE: +0.4, PE: -1.6) align with NIFTY bull bias

India Adaptation:
  - Compute 9 indicators manually (no talib dependency)
  - Z-score normalize over rolling 14-20 window
  - Dynamic weight: momentum boosted 1.5x in strong trends
  - Volatility adjustment: ATR percentile dampens score in high vol
  - Buy ATM CE when final score > 0.4, ATM PE when < -1.6
  - Exit: 50% SL / 1:2 R:R target / 5-day max hold
  - Position: 5% capital per trade
  - Daily loss limit: 2%
"""
import uuid
import math
import pandas as pd
import numpy as np
from scipy.stats import norm
from typing import Dict, Any, List

from .base import AlgoBase
from utils.logger import (
    log_session_start, log_session_end, log_market_snapshot,
    log_signal_check, log_trade_entry, log_trade_exit, log_backtest_run
)
from data_sources.yf_fetcher import fetch_nifty_data

# ── Constants ──────────────────────────────────────────────────────────────────
LOT_SIZE         = 25
INITIAL_CAPITAL  = 200_000
POS_SIZE_PCT     = 0.05
MAX_DAILY_LOSS_PCT = 0.02
TX_COST_SINGLE   = 200
RISK_FREE_RATE   = 0.07
EXPIRY_DAYS      = 5
STRIKE_STEP      = 50
BASE_IV          = 0.13

# Aggregate Score parameters
BUY_THRESHOLD    = 0.40    # Optimized for NIFTY daily (was 0.59453 in crypto)
SELL_THRESHOLD   = 1.60    # Asymmetric: harder to go short (NIFTY bull bias)
SL_PCT           = 0.50
RR_RATIO         = 2.0
MAX_HOLD_DAYS    = 5

# Indicator periods
MA_PERIOD        = 10
ROC_PERIOD       = 2
MACD_FAST        = 12
MACD_SLOW        = 26
MOM_PERIOD       = 4
RSI_PERIOD       = 10
BB_PERIOD        = 20
CCI_PERIOD       = 20
STOCH_K          = 14
STOCH_D          = 3
ATR_PERIOD       = 14
VOL_WIN          = 60      # ATR percentile window

# Weights (from FreqAI hyperopt, optimized for crypto — kept for NIFTY)
W_MA      = 0.54347
W_MACD    = 0.82226
W_ROC     = 0.56675
W_MOM     = 0.77918
W_RSI     = 0.98488
W_BB      = 0.31368
W_CCI     = 0.75916
W_STOCH   = 0.09226
W_ATR     = 0.85667


def bs_price(spot, strike, days, sigma, opt="CE", r=RISK_FREE_RATE):
    t = days / 365.0
    if t <= 0 or sigma <= 0:
        return max(0.0, spot - strike) if opt == "CE" else max(0.0, strike - spot)
    d1 = (math.log(spot / strike) + (r + 0.5 * sigma ** 2) * t) / (sigma * math.sqrt(t))
    d2 = d1 - sigma * math.sqrt(t)
    if opt == "CE":
        return max(0.0, spot * norm.cdf(d1) - strike * math.exp(-r * t) * norm.cdf(d2))
    return max(0.0, strike * math.exp(-r * t) * norm.cdf(-d2) - spot * norm.cdf(-d1))


def atm(spot):
    return round(spot / STRIKE_STEP) * STRIKE_STEP


# ── Manual indicator implementations (no talib dependency) ────────────────────
def _sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(period).mean()

def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()

def _roc(series: pd.Series, period: int) -> pd.Series:
    return (series - series.shift(period)) / series.shift(period) * 100

def _momentum(series: pd.Series, period: int) -> pd.Series:
    return series - series.shift(period)

def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / (loss + 1e-9)
    return 100 - (100 / (1 + rs))

def _bbands(series: pd.Series, period: int = 20, std: int = 2):
    mid = series.rolling(period).mean()
    sigma = series.rolling(period).std()
    return mid + std * sigma, mid, mid - std * sigma

def _cci(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 20) -> pd.Series:
    tp = (high + low + close) / 3
    ma = tp.rolling(period).mean()
    md = tp.rolling(period).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
    return (tp - ma) / (0.015 * md + 1e-9)

def _stoch(high: pd.Series, low: pd.Series, close: pd.Series, k: int = 14, d: int = 3):
    lowest = low.rolling(k).min()
    highest = high.rolling(k).max()
    k_line = 100 * (close - lowest) / (highest - lowest + 1e-9)
    return k_line, k_line.rolling(d).mean()

def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def _obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    obv = pd.Series(0, index=close.index, dtype=float)
    obv.iloc[0] = volume.iloc[0]
    for i in range(1, len(close)):
        if close.iloc[i] > close.iloc[i-1]:
            obv.iloc[i] = obv.iloc[i-1] + volume.iloc[i]
        elif close.iloc[i] < close.iloc[i-1]:
            obv.iloc[i] = obv.iloc[i-1] - volume.iloc[i]
        else:
            obv.iloc[i] = obv.iloc[i-1]
    return obv


def _zscore(series: pd.Series, window: int = 14) -> pd.Series:
    return (series - series.rolling(window).mean()) / (series.rolling(window).std() + 1e-9)


class Algo15AggregateScore(AlgoBase):
    algo_id = "algo15"
    name    = "Aggregate Score"

    def _compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute all 9 normalized indicators + aggregate score."""
        c = df["Close"]
        h = df["High"]
        l = df["Low"]
        v = df["Volume"]

        # Raw indicators
        ma10 = _sma(c, MA_PERIOD)
        roc2 = _roc(c, ROC_PERIOD)
        macd_line = _ema(c, MACD_FAST) - _ema(c, MACD_SLOW)
        mom4 = _momentum(c, MOM_PERIOD)
        rsi10 = _rsi(c, RSI_PERIOD)
        bb_up, bb_mid, bb_low = _bbands(c, BB_PERIOD)
        cci20 = _cci(h, l, c, CCI_PERIOD)
        stoch_k, stoch_d = _stoch(h, l, c, STOCH_K, STOCH_D)
        atr14 = _atr(h, l, c, ATR_PERIOD)
        obv_series = _obv(c, v)

        # Normalized (z-score)
        df["norm_ma"] = _zscore(c - ma10, MA_PERIOD)
        df["norm_macd"] = _zscore(macd_line, MACD_SLOW)
        df["norm_roc"] = _zscore(roc2, ROC_PERIOD)
        df["norm_momentum"] = _zscore(mom4, MOM_PERIOD)
        df["norm_rsi"] = _zscore(rsi10, RSI_PERIOD)
        df["norm_bb_width"] = _zscore((bb_up - bb_low) / bb_mid, BB_PERIOD)
        df["norm_cci"] = _zscore(cci20, CCI_PERIOD)
        df["norm_stoch"] = _zscore(stoch_k, STOCH_K)
        df["norm_atr"] = _zscore(atr14, ATR_PERIOD)

        # Dynamic weighting: boost momentum in strong trends
        trend_strength = abs(ma10 - c)
        strong_thresh = trend_strength.rolling(14).mean() + 1.5 * trend_strength.rolling(14).std()
        is_strong = trend_strength > strong_thresh
        w_momentum = np.where(is_strong, W_MOM * 1.5, W_MOM)

        # Aggregate score S
        df["S"] = (W_MA * df["norm_ma"] +
                   W_MACD * df["norm_macd"] +
                   W_ROC * df["norm_roc"] +
                   w_momentum * df["norm_momentum"] +
                   W_RSI * df["norm_rsi"] +
                   W_BB * df["norm_bb_width"] +
                   W_CCI * df["norm_cci"] +
                   W_STOCH * df["norm_stoch"] +
                   W_ATR * df["norm_atr"])

        # Volatility adjustment (ATR percentile)
        atr_pct = atr14.rolling(VOL_WIN).apply(lambda x: pd.Series(x).rank(pct=True).iloc[-1], raw=False)
        df["vol_adj"] = 1.0 - 0.5 * atr_pct
        df["target_score"] = df["S"] * df["vol_adj"]

        return df

    def run_backtest(self, start_date: str, end_date: str, interval: str = "1d") -> Dict[str, Any]:
        nifty = fetch_nifty_data(start_date, end_date, interval=interval)
        if nifty.empty:
            return {"metrics": self._metrics([], INITIAL_CAPITAL), "trades": [],
                    "monthly": {}, "equity_curve": []}

        nifty = nifty[nifty.index.dayofweek < 5]
        nifty = self._compute_indicators(nifty)

        trades: List[Dict] = []
        total_pnl = 0.0
        wins = losses = 0
        balance = INITIAL_CAPITAL
        daily_pnl = 0.0
        daily_date = None
        hit_daily_loss = False
        active_pos = None

        for idx, row in nifty.iterrows():
            date_str = idx.strftime("%Y-%m-%d")
            if date_str != daily_date:
                daily_date = date_str
                daily_pnl = 0.0
                hit_daily_loss = False

            log_session_start(self.algo_id, self.name, date_str, mode="backtest")

            open_px  = float(row["Open"])
            high_px  = float(row["High"])
            low_px   = float(row["Low"])
            close_px = float(row["Close"])
            target   = float(row["target_score"]) if pd.notna(row["target_score"]) else 0.0
            score    = float(row["S"]) if pd.notna(row["S"]) else 0.0
            vol_adj  = float(row["vol_adj"]) if pd.notna(row["vol_adj"]) else 1.0

            log_market_snapshot(self.algo_id, open_px, {
                "open": open_px, "high": high_px, "low": low_px,
                "close": close_px, "S": round(score, 3), "vol_adj": round(vol_adj, 3),
                "target_score": round(target, 3),
            })

            # ── Manage active position ─────────────────────────────────────
            if active_pos is not None:
                pos = active_pos
                pos["days_held"] += 1
                dte_x = max(0.1, pos["entry_dte"] - pos["days_held"])
                opt_type = pos["option_type"]

                sl_px = pos["entry_px"] * (1.0 - SL_PCT)
                tgt_px = pos["entry_px"] * (1.0 + SL_PCT * RR_RATIO)

                opt_at_high = bs_price(high_px, pos["strike"], dte_x, BASE_IV, opt_type)
                opt_at_low  = bs_price(low_px,  pos["strike"], dte_x, BASE_IV, opt_type)
                exit_px = None
                exit_r  = None

                if opt_at_high >= tgt_px:
                    exit_px = tgt_px
                    exit_r  = "TARGET_EXIT"
                elif opt_at_low <= sl_px:
                    exit_px = sl_px
                    exit_r  = "SL_EXIT"
                elif pos["days_held"] >= MAX_HOLD_DAYS:
                    exit_px = bs_price(close_px, pos["strike"], dte_x, BASE_IV, opt_type)
                    exit_r  = "MAX_HOLD_EXIT"
                else:
                    log_signal_check(
                        self.algo_id, "AGG_HOLD", eligible=False,
                        reason=f"Holding {opt_type} day {pos['days_held']}/{MAX_HOLD_DAYS}",
                        context={"entry_px": pos["entry_px"], "target_score": round(target, 3)},
                        timestamp="09:20:00"
                    )
                    continue

                if exit_px is not None:
                    pnl_val = (exit_px - pos["entry_px"]) * LOT_SIZE * pos["qty"] - TX_COST_SINGLE * pos["qty"]
                    won = pnl_val > 0

                    log_trade_exit(
                        self.algo_id, pos["tid"], f"{date_str} 15:25:00", round(exit_px, 2),
                        exit_r, round(pnl_val, 2),
                        round(pnl_val / (pos["entry_px"] * LOT_SIZE * pos["qty"]) * 100, 2) if pos["entry_px"] > 0 else 0,
                        context={"close": close_px, "high": high_px, "low": low_px,
                                 "days_held": pos["days_held"], "target_score": round(target, 3)}
                    )

                    trades.append({
                        "trade_id": pos["tid"], "algo_id": self.algo_id, "date": pos["entry_date"],
                        "symbol": "NIFTY", "strike": pos["strike"],
                        "option_type": opt_type, "signal_name": f"AGG_{opt_type}",
                        "entry_time": f"{pos['entry_date']} 09:20:00", "entry_price": round(pos["entry_px"], 2),
                        "exit_time": f"{date_str} 15:25:00", "exit_price": round(exit_px, 2),
                        "exit_reason": exit_r, "pnl": round(pnl_val, 2),
                        "lot_size": LOT_SIZE, "status": "closed", "qty": LOT_SIZE * pos["qty"],
                    })

                    total_pnl += pnl_val
                    balance += pnl_val
                    daily_pnl += pnl_val
                    if won: wins += 1
                    else: losses += 1

                    if daily_pnl <= -INITIAL_CAPITAL * MAX_DAILY_LOSS_PCT:
                        hit_daily_loss = True

                    active_pos = None
                    continue

            # ── New entry check ────────────────────────────────────────────
            if hit_daily_loss:
                log_signal_check(
                    self.algo_id, "AGG_SKIP", eligible=False,
                    reason="Daily loss limit hit", context={"daily_pnl": round(daily_pnl, 2)},
                    timestamp="09:20:00"
                )
                continue

            signal = 0
            if target > BUY_THRESHOLD:
                signal = 1
            elif target < -SELL_THRESHOLD:
                signal = -1

            if signal == 0:
                log_signal_check(
                    self.algo_id, "AGG_NONE", eligible=False,
                    reason=f"Target score {round(target, 3)} within thresholds (±{BUY_THRESHOLD}/{SELL_THRESHOLD})",
                    context={"S": round(score, 3), "vol_adj": round(vol_adj, 3)},
                    timestamp="09:20:00"
                )
                continue

            option_type = "CE" if signal == 1 else "PE"
            strike = atm(open_px)
            dte = EXPIRY_DAYS
            entry_px = bs_price(open_px, strike, dte, BASE_IV, option_type)
            pos_capital = balance * POS_SIZE_PCT
            qty = max(1, int(pos_capital / (entry_px * LOT_SIZE)))
            tid = str(uuid.uuid4())[:8]

            log_trade_entry(
                self.algo_id, tid, f"{date_str} 09:20:00", option_type, strike,
                "ATM", round(entry_px, 2), qty * LOT_SIZE,
                context={"target_score": round(target, 3), "S": round(score, 3),
                         "vol_adj": round(vol_adj, 3), "open": open_px, "dte": dte}
            )
            log_signal_check(
                self.algo_id, f"AGG_BUY_{option_type}", eligible=True,
                reason=f"Target score {round(target, 3)} exceeds {'+' if signal==1 else '-'}{BUY_THRESHOLD if signal==1 else SELL_THRESHOLD} threshold",
                context={"open": open_px, "strike": strike, "entry_px": round(entry_px, 2),
                         "qty": qty, "dte": dte, "S": round(score, 3)},
                timestamp="09:20:00"
            )

            active_pos = {
                "tid": tid, "entry_date": date_str, "entry_open": open_px,
                "entry_px": entry_px, "strike": strike, "qty": qty,
                "days_held": 0, "entry_dte": dte, "option_type": option_type,
            }

        log_session_end(self.algo_id, date_str)
        log_backtest_run(self.algo_id, start_date, end_date, len(trades),
                         round(total_pnl, 2), round((total_pnl / INITIAL_CAPITAL) * 100, 2))

        return {
            "metrics": self._metrics(trades, INITIAL_CAPITAL),
            "trades": trades,
            "monthly": self._monthly_breakdown(trades),
            "equity_curve": self._equity_curve(trades),
        }

    def get_live_signal(self, spot: float, indicators: Dict[str, float]) -> Dict[str, Any]:
        target = indicators.get("target_score", 0.0)
        score = indicators.get("S", 0.0)
        vol_adj = indicators.get("vol_adj", 1.0)

        if target > BUY_THRESHOLD:
            opt_type = "CE"
        elif target < -SELL_THRESHOLD:
            opt_type = "PE"
        else:
            return {
                "signal": "NO_TRADE",
                "option_type": None,
                "strike": None,
                "signal_cards": {
                    "Spot": spot, "S": round(score, 3), "Vol_Adj": round(vol_adj, 3),
                    "Target": round(target, 3), "Buy_Thresh": BUY_THRESHOLD, "Sell_Thresh": SELL_THRESHOLD,
                },
            }

        strike = atm(spot)
        entry_px = bs_price(spot, strike, EXPIRY_DAYS, BASE_IV, opt_type)
        return {
            "signal": f"AGG_BUY_{opt_type}",
            "option_type": opt_type,
            "strike": strike,
            "signal_cards": {
                "Spot": spot, "S": round(score, 3), "Vol_Adj": round(vol_adj, 3),
                "Target": round(target, 3), "Entry_Px": round(entry_px, 2), "DTE": EXPIRY_DAYS,
            },
        }
