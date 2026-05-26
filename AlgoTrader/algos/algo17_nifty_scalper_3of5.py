"""
AlgoTrader — Algo 17: NIFTY Scalper (3/5 Confluence)
Source: nifty_scalper-main (AngelOne SmartAPI production scalper)

Same as algo16 but uses 3/5 confluence (more aggressive).
See algo16 for full documentation.
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
TX_COST_SINGLE   = 20
RISK_FREE_RATE   = 0.07
STRIKE_STEP      = 50
BASE_IV          = 0.13

# Scalper parameters
TARGET_PCT       = 0.02
SL_PCT           = 0.05
MAX_TRADES_DAY   = 5
SLIPPAGE_PCT     = 0.0
MIN_ENTRY_PREM   = 5.0

# Indicator parameters
EMA_FAST         = 9
EMA_SLOW         = 21
RSI_PERIOD       = 7
ST_PERIOD        = 7
ST_MULT          = 3.0


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


def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def _rsi(series: pd.Series, period: int = 7) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/period, adjust=False).mean()
    rs = gain / (loss + 1e-9)
    return 100 - (100 / (1 + rs))


def _vwap(df: pd.DataFrame) -> pd.Series:
    d = df.copy()
    d["date"] = d.index.date if hasattr(d.index, 'date') else d.index.floor('D')
    d["tp"] = (d["high"] + d["low"] + d["close"]) / 3
    d["tpv"] = d["tp"] * d["volume"]
    d["ctpv"] = d.groupby("date")["tpv"].cumsum()
    d["cvol"] = d.groupby("date")["volume"].cumsum()
    return d["ctpv"] / d["cvol"].replace(0, np.nan)


def _supertrend(df: pd.DataFrame, period: int = 7, multiplier: float = 3.0):
    hl2 = (df["high"] + df["low"]) / 2
    prev_c = df["close"].shift(1)
    tr = pd.concat([df["high"]-df["low"], (df["high"]-prev_c).abs(), (df["low"]-prev_c).abs()], axis=1).max(axis=1)
    atr_ = tr.ewm(span=period, adjust=False).mean()
    ub = hl2 + multiplier * atr_
    lb = hl2 - multiplier * atr_
    st = pd.Series(np.nan, index=df.index)
    dir_ = pd.Series(1, index=df.index, dtype=int)
    st.iloc[0] = lb.iloc[0]
    for i in range(1, len(df)):
        p_st, p_dir = st.iloc[i-1], dir_.iloc[i-1]
        cur_ub = ub.iloc[i]
        cur_lb = lb.iloc[i]
        cur_ub = min(cur_ub, st.iloc[i-1]) if p_dir == -1 else cur_ub
        cur_lb = max(cur_lb, st.iloc[i-1]) if p_dir == 1 else cur_lb
        close = df["close"].iloc[i]
        if close > cur_ub:
            st.iloc[i], dir_.iloc[i] = cur_lb, 1
        elif close < cur_lb:
            st.iloc[i], dir_.iloc[i] = cur_ub, -1
        else:
            st.iloc[i], dir_.iloc[i] = p_st, p_dir
    return st, dir_


def _compute_signals(df: pd.DataFrame, vix_series: pd.Series) -> pd.DataFrame:
    sig_df = pd.DataFrame(index=df.index)
    vwap_line = _vwap(df)
    close = df["close"]

    sig_df["vwap"] = np.where(close > vwap_line * 1.0005, 1, np.where(close < vwap_line * 0.9995, -1, 0))

    fast = _ema(close, EMA_FAST)
    slow = _ema(close, EMA_SLOW)
    sig_df["ema"] = np.where(fast > slow, 1, np.where(fast < slow, -1, 0))

    _, st_dir = _supertrend(df, period=ST_PERIOD, multiplier=ST_MULT)
    sig_df["supertrend"] = st_dir.fillna(0)

    r = _rsi(close, RSI_PERIOD)
    rp = r.shift(1)
    sig_df["rsi"] = np.where((r > 50) & (r > rp), 1, np.where((r < 50) & (r < rp), -1, 0))

    sig_df["vix"] = 0
    if hasattr(vix_series.index, 'date'):
        vix_daily = vix_series.groupby(vix_series.index.date).last()
        vix_chg = vix_daily.pct_change() * 100
        for date, chg in vix_chg.items():
            mask = pd.to_datetime(df.index).date == date
            if chg <= 0.5:
                sig_df.loc[mask, "vix"] = 1
            elif chg >= 1.0:
                sig_df.loc[mask, "vix"] = -1
    else:
        vix_chg = vix_series.pct_change() * 100
        sig_df["vix"] = np.where(vix_chg <= 0.5, 1, np.where(vix_chg >= 1.0, -1, 0))

    bull = (sig_df == 1).sum(axis=1)
    bear = (sig_df == -1).sum(axis=1)
    sig_df["entry"] = np.where(bull >= 3, 1, np.where(bear >= 3, -1, 0))
    sig_df["bull_count"] = bull
    sig_df["bear_count"] = bear

    return sig_df


class Algo17NiftyScalper35(AlgoBase):
    algo_id = "algo17"
    name    = "NIFTY Scalper (3/5)"

    def run_backtest(self, start_date: str, end_date: str, interval: str = "5m") -> Dict[str, Any]:
        nifty = fetch_nifty_data(start_date, end_date, interval="5m")
        if nifty.empty:
            return {"metrics": self._metrics([], INITIAL_CAPITAL), "trades": [],
                    "monthly": {}, "equity_curve": []}

        import yfinance as yf
        vix_df = yf.download("^INDIAVIX", start=start_date, end=end_date, progress=False)
        if isinstance(vix_df.columns, pd.MultiIndex):
            vix_df.columns = [c[0] for c in vix_df.columns]
        vix_series = vix_df["Close"].dropna() if not vix_df.empty else pd.Series(dtype=float)

        df = nifty.copy()
        df.columns = [c.lower() for c in df.columns]

        sig_df = _compute_signals(df, vix_series)

        trades: List[Dict] = []
        total_pnl = 0.0
        wins = losses = 0
        balance = INITIAL_CAPITAL
        daily_pnl = 0.0
        daily_date = None
        hit_daily_loss = False
        active_pos = None
        trades_today = 0

        session_ends = set(df.groupby(df.index.date if hasattr(df.index, 'date') else df.index.floor('D')).tail(1).index)

        for i in range(len(df) - 1):
            sig = int(sig_df["entry"].iloc[i])
            current_time = df.index[i]
            next_time = df.index[i + 1]
            today = current_time.date() if hasattr(current_time, 'date') else current_time.floor('D')
            is_eod_next = next_time in session_ends

            if str(today) != str(daily_date):
                daily_date = str(today)
                daily_pnl = 0.0
                hit_daily_loss = False
                trades_today = 0

            if active_pos is not None:
                pos = active_pos
                bar_idx = i + 1
                if bar_idx <= pos["entry_bar"]:
                    continue
                spot = float(df["close"].iloc[bar_idx])
                bars_held = bar_idx - pos["entry_bar"]
                tte_days = max(1.0/252.0, 1.0/252.0 - bars_held / 252.0)
                opt_type = pos["option_type"]

                curr_prem = bs_price(spot, pos["strike"], tte_days, BASE_IV, opt_type)
                exit_prem = curr_prem * (1 - SLIPPAGE_PCT)

                exit_px = None
                exit_r = None

                if exit_prem >= pos["target_px"]:
                    exit_px = exit_prem
                    exit_r = "TARGET_EXIT"
                elif exit_prem <= pos["sl_px"]:
                    exit_px = exit_prem
                    exit_r = "SL_EXIT"
                elif is_eod_next:
                    exit_px = exit_prem
                    exit_r = "EOD_EXIT"

                if exit_px is not None:
                    pnl_val = (exit_px - pos["entry_px"]) * LOT_SIZE * pos["qty"] - TX_COST_SINGLE * pos["qty"]
                    won = pnl_val > 0

                    log_trade_exit(
                        self.algo_id, pos["tid"], str(next_time), round(exit_px, 2),
                        exit_r, round(pnl_val, 2),
                        round(pnl_val / (pos["entry_px"] * LOT_SIZE * pos["qty"]) * 100, 2) if pos["entry_px"] > 0 else 0,
                        context={"close": spot, "bars_held": bars_held}
                    )

                    trades.append({
                        "trade_id": pos["tid"], "algo_id": self.algo_id, "date": pos["entry_date"],
                        "symbol": "NIFTY", "strike": pos["strike"],
                        "option_type": opt_type, "signal_name": f"SCALP_{opt_type}",
                        "entry_time": str(pos["entry_time"]), "entry_price": round(pos["entry_px"], 2),
                        "exit_time": str(next_time), "exit_price": round(exit_px, 2),
                        "exit_reason": exit_r, "pnl": round(pnl_val, 2),
                        "lot_size": LOT_SIZE, "status": "closed", "qty": LOT_SIZE * pos["qty"],
                    })

                    total_pnl += pnl_val
                    balance += pnl_val
                    daily_pnl += pnl_val
                    if won:
                        wins += 1
                    else:
                        losses += 1

                    if daily_pnl <= -INITIAL_CAPITAL * MAX_DAILY_LOSS_PCT:
                        hit_daily_loss = True

                    active_pos = None
                    continue

            if hit_daily_loss:
                log_signal_check(
                    self.algo_id, "SCALP_SKIP", eligible=False,
                    reason="Daily loss limit hit", context={"daily_pnl": round(daily_pnl, 2)},
                    timestamp=str(current_time)
                )
                continue

            if sig == 0:
                continue

            if trades_today >= MAX_TRADES_DAY:
                log_signal_check(
                    self.algo_id, "SCALP_SKIP", eligible=False,
                    reason="Max trades/day reached", context={"trades_today": trades_today},
                    timestamp=str(current_time)
                )
                continue

            next_open = float(df["open"].iloc[i + 1])
            option_type = "CE" if sig == 1 else "PE"
            strike = atm(next_open)
            tte_days = 1.0 / 252.0
            entry_px_raw = bs_price(next_open, strike, tte_days, BASE_IV, option_type)
            entry_px = entry_px_raw * (1 + SLIPPAGE_PCT)

            if entry_px < MIN_ENTRY_PREM:
                log_signal_check(
                    self.algo_id, "SCALP_SKIP", eligible=False,
                    reason=f"Option price too low (₹{entry_px:.2f}) — avoid deep OTM",
                    context={"entry_px": round(entry_px, 2), "min": MIN_ENTRY_PREM},
                    timestamp=str(next_time)
                )
                continue

            pos_capital = balance * POS_SIZE_PCT
            qty = max(1, int(pos_capital / (entry_px * LOT_SIZE)))
            tid = str(uuid.uuid4())[:8]

            log_trade_entry(
                self.algo_id, tid, f"SCALP_BUY_{option_type}", next_open, strike,
                option_type, round(entry_px, 2), str(next_time), LOT_SIZE,
                context={"signal": sig, "open": next_open, "bull_count": int(sig_df["bull_count"].iloc[i]),
                         "bear_count": int(sig_df["bear_count"].iloc[i]), "qty": qty}
            )
            log_signal_check(
                self.algo_id, f"SCALP_BUY_{option_type}", eligible=True,
                reason=f"3/5 indicators aligned {'bullish' if sig==1 else 'bearish'}",
                context={"open": next_open, "strike": strike, "entry_px": round(entry_px, 2),
                         "qty": qty, "tte": tte_days}, timestamp=str(next_time)
            )

            active_pos = {
                "tid": tid, "entry_date": str(today), "entry_time": next_time,
                "entry_open": next_open, "entry_px": entry_px, "strike": strike, "qty": qty,
                "entry_bar": i + 1, "option_type": option_type,
                "target_px": entry_px * (1 + TARGET_PCT),
                "sl_px": entry_px * (1 - SL_PCT),
            }
            trades_today += 1

        wr_val = (wins / len(trades) * 100) if trades else 0.0
        log_session_end(self.algo_id, len(trades), round(total_pnl, 2))
        log_backtest_run(self.algo_id, start_date, end_date, len(trades),
                         round(wr_val, 2), round(total_pnl, 2))

        return {
            "metrics": self._metrics([t["pnl"] for t in trades], INITIAL_CAPITAL),
            "trades": trades,
            "monthly": self._monthly_breakdown(trades),
            "equity_curve": self._equity_curve(trades),
        }

    def get_live_signal(self, spot: float, indicators: Dict[str, float]) -> Dict[str, Any]:
        signals = [
            indicators.get("vwap_signal", 0),
            indicators.get("ema_signal", 0),
            indicators.get("supertrend_signal", 0),
            indicators.get("rsi_signal", 0),
            indicators.get("vix_signal", 0),
        ]
        bull_count = sum(1 for s in signals if s == 1)
        bear_count = sum(1 for s in signals if s == -1)

        if bull_count >= 3:
            opt_type = "CE"
        elif bear_count >= 3:
            opt_type = "PE"
        else:
            return {
                "signal": "NO_TRADE",
                "option_type": None,
                "strike": None,
                "signal_cards": {
                    "Spot": spot, "Bull_Count": bull_count, "Bear_Count": bear_count,
                    "VWAP": signals[0], "EMA": signals[1], "ST": signals[2], "RSI": signals[3], "VIX": signals[4],
                }
            }

        strike = atm(spot)
        entry_px = bs_price(spot, strike, 1.0, BASE_IV, opt_type)
        return {
            "signal": f"SCALP_BUY_{opt_type}",
            "option_type": opt_type,
            "strike": strike,
            "signal_cards": {
                "Spot": spot, "Bull_Count": bull_count, "Bear_Count": bear_count,
                "VWAP": signals[0], "EMA": signals[1], "ST": signals[2], "RSI": signals[3], "VIX": signals[4],
                "Strike": strike, "Entry_Px": round(entry_px, 2), "TTE": "0DTE",
            }
        }
