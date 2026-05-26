"""
AlgoTrader — Algo 4: Flow NIFTY (Revived)
Source: FlowAlgo-Options-Trader-main (US equity options flow)

Revival Strategy (India-adapted):
  - Original FlowAlgo tracked US options flow (calls/puts) per stock
  - India Adaptation: proxy "unusual activity" via volume + volatility expansion
  - Signal: Prev-day Close > EMA-13 (trend) + ATR% > 0.7 (expansion) + Vol > 1.15x avg (activity)
  - Entry: Buy ATM CE at Open — option leverage magnifies the follow-through
  - Exit: +1% target / -0.5% SL on spot, or EOD
  - Position size: 5% of capital per trade

  NOTE: True options flow (OI change per strike in real-time) would be superior.
  This is a backtestable proxy. Live deployment should use NSE option chain data.
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

# ── Constants ─────────────────────────────────────────────────────────────────
LOT_SIZE         = 25
INITIAL_CAPITAL  = 200_000
POS_SIZE_PCT     = 0.05          # 5% of capital per trade
TARGET_PCT       = 0.01          # +1% spot target
SL_PCT           = 0.005         # -0.5% spot stop loss
EMA_PERIOD       = 13            # EMA-13 trend filter
ATR_THRESH       = 0.70         # ATR% > 0.7 (expansion day)
VOL_THRESH       = 1.15         # Volume > 1.15x 20-day avg
RISK_FREE_RATE   = 0.07
EXPIRY_DAYS      = 3
TX_COST_SINGLE   = 200
STRIKE_STEP      = 50
MAX_DAILY_LOSS_PCT = 0.02


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


class Algo4FlowNifty(AlgoBase):
    algo_id = "algo4"
    name    = "Flow NIFTY (Revived)"

    def run_backtest(self, start_date: str, end_date: str, interval: str = "1d") -> Dict[str, Any]:
        data = fetch_nifty_data(start_date, end_date, interval=interval)
        if data.empty:
            return {"metrics": self._metrics([], INITIAL_CAPITAL), "trades": [],
                    "monthly": {}, "equity_curve": []}

        data = data[data.index.dayofweek < 5]

        # ── Indicators ──────────────────────────────────────────────────────
        data["EMA_13"] = data["Close"].ewm(span=EMA_PERIOD, adjust=False).mean()
        data["Above_EMA"] = data["Close"] > data["EMA_13"]

        # ATR
        data["TR"] = np.maximum(
            data["High"] - data["Low"],
            np.maximum(abs(data["High"] - data["Close"].shift()),
                       abs(data["Low"] - data["Close"].shift()))
        )
        data["ATR14"] = data["TR"].rolling(14).mean()
        data["ATR_PCT"] = data["ATR14"] / data["Close"] * 100

        # Volume
        data["Vol_MA20"] = data["Volume"].rolling(20).mean()
        data["Vol_Ratio"] = data["Volume"] / data["Vol_MA20"]

        # Lagged signal: prev-day conditions decide today's entry
        data["Flow_Signal"] = (
            data["Above_EMA"].shift(1) &
            (data["ATR_PCT"] > ATR_THRESH).shift(1) &
            (data["Vol_Ratio"] > VOL_THRESH).shift(1)
        ).fillna(False)

        # ── Backtest loop ───────────────────────────────────────────────────
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

            log_session_start(self.algo_id, self.name, date_str, mode="backtest")

            open_px  = float(row["Open"])
            high_px  = float(row["High"])
            low_px   = float(row["Low"])
            close_px = float(row["Close"])
            ema_13   = float(row["EMA_13"])
            atr_pct  = float(row["ATR_PCT"]) if pd.notna(row["ATR_PCT"]) else 0.0
            vol_rat  = float(row["Vol_Ratio"]) if pd.notna(row["Vol_Ratio"]) else 0.0
            signal   = bool(row["Flow_Signal"])

            log_market_snapshot(self.algo_id, open_px, {
                "open": open_px, "high": high_px, "low": low_px,
                "close": close_px, "ema_13": round(ema_13, 1),
                "atr_pct": round(atr_pct, 2), "vol_ratio": round(vol_rat, 2),
                "above_ema": bool(row["Above_EMA"]),
            })

            if signal and not hit_daily_loss:
                k = atm(open_px)
                iv = 0.13
                dte_e = EXPIRY_DAYS
                dte_x = max(0.1, dte_e - 1 / 252)
                entry_px = bs_price(open_px, k, dte_e, iv, "CE")

                qty = max(1, int(balance * POS_SIZE_PCT / (entry_px * LOT_SIZE)))

                # Check target and stop on spot
                tgt_spot = open_px * (1 + TARGET_PCT)
                sl_spot = open_px * (1 - SL_PCT)

                if high_px >= tgt_spot:
                    exit_px = bs_price(tgt_spot, k, dte_x, iv, "CE")
                    exit_r = "TARGET_HIT"
                elif low_px <= sl_spot:
                    exit_px = bs_price(sl_spot, k, dte_x, iv, "CE")
                    exit_r = "SL_HIT"
                else:
                    exit_px = bs_price(close_px, k, dte_x, iv, "CE")
                    exit_r = "EOD_EXIT"

                pnl_val = (exit_px - entry_px) * LOT_SIZE * qty - TX_COST_SINGLE * qty
                won = pnl_val > 0
                tid = str(uuid.uuid4())[:8]

                log_signal_check(
                    self.algo_id, "FLOW_BUY_CE", eligible=True,
                    reason=(f"Prev-day signal: Above_EMA + ATR({atr_pct:.2f}%)>{ATR_THRESH} "
                            f"+ Vol({vol_rat:.2f}x)>{VOL_THRESH} → expansion + activity proxy"),
                    context={"ema_13": ema_13, "atr_pct": atr_pct, "vol_ratio": vol_rat,
                             "entry": entry_px, "qty": qty},
                    timestamp="09:20:00"
                )

                log_trade_entry(
                    self.algo_id, tid, "FLOW_BUY_CE", open_px, k, "CE",
                    round(entry_px, 2), f"{date_str} 09:20:00", LOT_SIZE * qty,
                    context={"capital_pct": POS_SIZE_PCT}
                )

                log_trade_exit(
                    self.algo_id, tid, f"{date_str} 15:25:00", round(exit_px, 2),
                    exit_r, round(pnl_val, 2),
                    round(pnl_val / (entry_px * LOT_SIZE * qty) * 100, 2) if entry_px > 0 else 0,
                    context={"close": close_px, "high": high_px, "low": low_px}
                )

                trades.append({
                    "trade_id": tid, "algo_id": self.algo_id, "date": date_str,
                    "symbol": "NIFTY", "strike": k,
                    "option_type": "CE", "signal_name": "FLOW_BUY_CE",
                    "entry_time": f"{date_str} 09:20:00", "entry_price": round(entry_px, 2),
                    "exit_time": f"{date_str} 15:25:00", "exit_price": round(exit_px, 2),
                    "exit_reason": exit_r, "pnl": round(pnl_val, 2),
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

                log_session_end(self.algo_id, 1, pnl_val, status="OK")
            else:
                reason = "No flow signal"
                if signal and hit_daily_loss:
                    reason = "Daily loss limit hit → paused"
                log_signal_check(
                    self.algo_id, "FLOW_BUY_CE", eligible=False,
                    reason=reason,
                    context={"ema_13": ema_13, "atr_pct": atr_pct, "vol_ratio": vol_rat},
                    timestamp="09:20:00"
                )
                log_session_end(self.algo_id, 0, 0.0, status="NO_TRADE")

        if trades:
            wr = wins / len(trades) * 100
            log_backtest_run(self.algo_id, start_date, end_date, len(trades), wr, total_pnl)

        pnl_list = [t["pnl"] for t in trades]

        last = data.iloc[-1]
        signal_cards = {
            "Spot":       round(float(last["Close"]), 0),
            "EMA_13":     round(float(last["EMA_13"]), 1),
            "Above_EMA":  bool(last["Above_EMA"]),
            "ATR_PCT":    round(float(last["ATR_PCT"]), 2) if pd.notna(last["ATR_PCT"]) else 0,
            "Vol_Ratio":  round(float(last["Vol_Ratio"]), 2) if pd.notna(last["Vol_Ratio"]) else 0,
        }

        return {
            "metrics":      self._metrics(pnl_list, INITIAL_CAPITAL),
            "trades":       trades,
            "monthly":      self._monthly_breakdown(trades),
            "equity_curve": self._equity_curve(trades),
            "signal_cards": signal_cards,
        }

    def get_live_signal(self, spot: float, indicators: Dict[str, float]) -> Dict[str, Any]:
        ema_13 = indicators.get("ema_13", 0.0)
        above_ema = spot > ema_13
        signal = above_ema

        if signal:
            strike = atm(spot)
            return {
                "signal":       "FLOW_BUY_CE",
                "option_type":  "CE",
                "strike":       strike,
                "signal_cards": {
                    "Spot": spot, "EMA_13": ema_13,
                    "Above_EMA": above_ema,
                    "Flow_Signal": True,
                },
            }

        return {
            "signal":       "NO_TRADE",
            "option_type":  None,
            "strike":       None,
            "signal_cards": {
                "Spot": spot, "EMA_13": ema_13,
                "Above_EMA": above_ema,
                "Flow_Signal": False,
            },
        }
