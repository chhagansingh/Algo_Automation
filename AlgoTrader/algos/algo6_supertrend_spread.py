"""
AlgoTrader — Algo 6: SuperTrend Directional (Revived)
Source: fully-automated-nifty-options-trading-main

Original Strategy:
  - SuperTrend(period=15, multiplier=14.2) on NIFTY 5min chart
  - ADX filter for trend strength
  - Credit spread: Sell ATM + Buy OTM (risk points away)

Revived Strategy (Daily Bars):
  - SuperTrend(7, 3.0) on NIFTY daily with ADX>20 filter
  - Directional ATM CE/PE based on SuperTrend trend
  - +1% target / -0.5% SL on spot (intraday exits when hit)
  - Position size: 3% of capital per trade
  - Daily loss limit: 1% of capital

NOTE: True credit spread backtest requires intraday option chain data.
This directional proxy is viable but not equivalent to the original spread strategy.
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

# ── Constants ────────────────────────────────────────────────────────────────
LOT_SIZE         = 25
INITIAL_CAPITAL  = 200_000
ST_PERIOD        = 7
ST_MULTIPLIER    = 3.0
POS_SIZE_PCT     = 0.03
TARGET_PCT       = 0.01
SL_PCT           = 0.005
ADX_THRESH       = 20
RISK_FREE_RATE   = 0.07
EXPIRY_DAYS      = 3
TX_COST_SINGLE   = 200
STRIKE_STEP      = 50
MAX_DAILY_LOSS_PCT = 0.01
BASE_IV            = 0.13


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


def calculate_adx(df, n=14):
    plus_dm = df["High"].diff()
    minus_dm = -df["Low"].diff()
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm < 0] = 0
    tr = pd.concat([
        df["High"] - df["Low"],
        (df["High"] - df["Close"].shift()).abs(),
        (df["Low"] - df["Close"].shift()).abs()
    ], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/n, adjust=False).mean()
    plus_di = 100 * (plus_dm.ewm(alpha=1/n, adjust=False).mean() / atr)
    minus_di = 100 * (minus_dm.ewm(alpha=1/n, adjust=False).mean() / atr)
    dx = ((plus_di - minus_di).abs() / (plus_di + minus_di)) * 100
    adx = dx.ewm(alpha=1/n, adjust=False).mean()
    return adx


def calculate_supertrend(data: pd.DataFrame, period: int, multiplier: float) -> pd.Series:
    """Calculate SuperTrend indicator. Returns series of 'up'/'down' strings."""
    hl2 = (data["High"] + data["Low"]) / 2
    tr1 = data["High"] - data["Low"]
    tr2 = (data["High"] - data["Close"].shift(1)).abs()
    tr3 = (data["Low"] - data["Close"].shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/period, min_periods=period).mean()
    upperband = hl2 + multiplier * atr
    lowerband = hl2 - multiplier * atr
    st = pd.Series(index=data.index, dtype=float)
    trend = pd.Series(index=data.index, dtype=int)
    for i in range(len(data)):
        if i == 0:
            st.iloc[i] = upperband.iloc[i]
            trend.iloc[i] = 1
        else:
            if trend.iloc[i-1] == 1:
                if data["Close"].iloc[i] > st.iloc[i-1]:
                    st.iloc[i] = max(lowerband.iloc[i], st.iloc[i-1])
                    trend.iloc[i] = 1
                else:
                    st.iloc[i] = upperband.iloc[i]
                    trend.iloc[i] = -1
            else:
                if data["Close"].iloc[i] < st.iloc[i-1]:
                    st.iloc[i] = min(upperband.iloc[i], st.iloc[i-1])
                    trend.iloc[i] = -1
                else:
                    st.iloc[i] = lowerband.iloc[i]
                    trend.iloc[i] = 1
    return pd.Series(np.where(trend == 1, "up", "down"), index=data.index)


class Algo6SuperTrendSpread(AlgoBase):
    algo_id = "algo6"
    name    = "SuperTrend Directional"

    def run_backtest(self, start_date: str, end_date: str, interval: str = "1d") -> Dict[str, Any]:
        data = fetch_nifty_data(start_date, end_date, interval=interval)
        if data.empty:
            return {"metrics": self._metrics([], INITIAL_CAPITAL), "trades": [],
                    "monthly": {}, "equity_curve": []}

        data = data[data.index.dayofweek < 5]

        # ── Indicators ──────────────────────────────────────────────────
        data["SuperTrend"] = calculate_supertrend(data, ST_PERIOD, ST_MULTIPLIER)
        data["ADX"] = calculate_adx(data)
        data["ST_Signal"] = data["SuperTrend"].shift(1)
        data["ADX_Known"] = data["ADX"].shift(1)

        # ── Backtest loop ───────────────────────────────────────────────
        trades: List[Dict] = []
        total_pnl = 0.0
        wins = losses = 0
        balance = INITIAL_CAPITAL
        daily_pnl = 0.0
        daily_date = None
        hit_daily_loss = False

        for idx, row in data.iterrows():
            date_str = idx.strftime("%Y-%m-%d")

            if date_str != daily_date:
                daily_date = date_str
                daily_pnl = 0.0
                hit_daily_loss = False

            if hit_daily_loss:
                continue

            st_sig = row["ST_Signal"]
            adx_val = float(row["ADX_Known"]) if pd.notna(row["ADX_Known"]) else 0.0
            if pd.isna(st_sig) or adx_val < ADX_THRESH:
                continue

            open_px  = float(row["Open"])
            high_px  = float(row["High"])
            low_px   = float(row["Low"])
            close_px = float(row["Close"])
            st_val   = str(row["SuperTrend"])
            k = atm(open_px)
            iv = BASE_IV
            dte_e = EXPIRY_DAYS
            dte_x = max(0.1, dte_e - 1 / 252)
            qty = max(1, int(balance * POS_SIZE_PCT / (bs_price(open_px, k, dte_e, iv, "CE") * LOT_SIZE)))

            tid = str(uuid.uuid4())[:8]
            entry_px = 0.0
            exit_px = 0.0
            exit_reason = "EOD_CLOSE"
            pnl_val = 0.0
            opt_type = None
            sig_name = None

            if st_sig == "up":
                opt_type = "CE"
                sig_name = "ST_BUY_CE"
                entry_px = bs_price(open_px, k, dte_e, iv, "CE")
                tgt_spot = open_px * (1 + TARGET_PCT)
                sl_spot = open_px * (1 - SL_PCT)
                if high_px >= tgt_spot:
                    exit_px = bs_price(tgt_spot, k, dte_x, iv, "CE")
                    exit_reason = "TARGET_HIT"
                elif low_px <= sl_spot:
                    exit_px = bs_price(sl_spot, k, dte_x, iv, "CE")
                    exit_reason = "SL_HIT"
                else:
                    exit_px = bs_price(close_px, k, dte_x, iv, "CE")
                pnl_val = (exit_px - entry_px) * LOT_SIZE * qty - TX_COST_SINGLE * qty
            else:
                opt_type = "PE"
                sig_name = "ST_BUY_PE"
                entry_px = bs_price(open_px, k, dte_e, iv, "PE")
                tgt_spot = open_px * (1 - TARGET_PCT)
                sl_spot = open_px * (1 + SL_PCT)
                if low_px <= tgt_spot:
                    exit_px = bs_price(tgt_spot, k, dte_x, iv, "PE")
                    exit_reason = "TARGET_HIT"
                elif high_px >= sl_spot:
                    exit_px = bs_price(sl_spot, k, dte_x, iv, "PE")
                    exit_reason = "SL_HIT"
                else:
                    exit_px = bs_price(close_px, k, dte_x, iv, "PE")
                pnl_val = (exit_px - entry_px) * LOT_SIZE * qty - TX_COST_SINGLE * qty

            won = pnl_val > 0
            log_signal_check(
                self.algo_id, sig_name, eligible=True,
                reason=(f"SuperTrend={st_val} + ADX={adx_val:.1f} >= {ADX_THRESH} → {opt_type} directional"),
                context={"supertrend": st_val, "adx": adx_val, "entry": entry_px, "qty": qty},
                timestamp="09:20:00"
            )
            log_trade_entry(
                self.algo_id, tid, sig_name, open_px, k, opt_type,
                round(entry_px, 2), f"{date_str} 09:20:00", LOT_SIZE * qty,
                context={"supertrend": st_val, "adx": adx_val, "capital_pct": POS_SIZE_PCT}
            )
            log_trade_exit(
                self.algo_id, tid, f"{date_str} 15:25:00", round(exit_px, 2),
                exit_reason, round(pnl_val, 2),
                round(pnl_val / (entry_px * LOT_SIZE * qty) * 100, 2) if entry_px > 0 else 0,
                context={"close": close_px, "high": high_px, "low": low_px}
            )

            trades.append({
                "trade_id": tid, "algo_id": self.algo_id, "date": date_str,
                "symbol": "NIFTY", "strike": k,
                "option_type": opt_type, "signal_name": sig_name,
                "entry_time": f"{date_str} 09:20:00", "entry_price": round(entry_px, 2),
                "exit_time": f"{date_str} 15:25:00", "exit_price": round(exit_px, 2),
                "exit_reason": exit_reason, "pnl": round(pnl_val, 2),
                "lot_size": LOT_SIZE, "status": "closed", "qty": LOT_SIZE * qty,
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

        if trades:
            wr = wins / len(trades) * 100
            log_backtest_run(self.algo_id, start_date, end_date, len(trades), wr, total_pnl)

        pnl_list = [t["pnl"] for t in trades]

        last = data.iloc[-1]
        signal_cards = {
            "Spot":       round(float(last["Close"]), 0),
            "SuperTrend": str(last["SuperTrend"]),
            "ADX":        round(float(last["ADX"]), 1) if pd.notna(last["ADX"]) else 0,
            "ST_Period":  ST_PERIOD,
            "ST_Multiplier": ST_MULTIPLIER,
        }

        return {
            "metrics":      self._metrics(pnl_list, INITIAL_CAPITAL),
            "trades":       trades,
            "monthly":      self._monthly_breakdown(trades),
            "equity_curve": self._equity_curve(trades),
            "signal_cards": signal_cards,
        }

    def get_live_signal(self, spot: float, indicators: Dict[str, float]) -> Dict[str, Any]:
        st = indicators.get("supertrend", "up")
        adx = indicators.get("adx", 0.0)
        if st == "up" and adx >= ADX_THRESH:
            return {
                "signal": "ST_BUY_CE", "option_type": "CE", "strike": atm(spot),
                "signal_cards": {
                    "Spot": spot, "SuperTrend": st, "ADX": adx,
                    "ST_Period": ST_PERIOD, "ST_Multiplier": ST_MULTIPLIER,
                },
            }
        elif st == "down" and adx >= ADX_THRESH:
            return {
                "signal": "ST_BUY_PE", "option_type": "PE", "strike": atm(spot),
                "signal_cards": {
                    "Spot": spot, "SuperTrend": st, "ADX": adx,
                    "ST_Period": ST_PERIOD, "ST_Multiplier": ST_MULTIPLIER,
                },
            }
        return {
            "signal": "NO_TRADE", "option_type": None, "strike": None,
            "signal_cards": {
                "Spot": spot, "SuperTrend": st, "ADX": adx,
                "ST_Period": ST_PERIOD, "ST_Multiplier": ST_MULTIPLIER,
            },
        }
