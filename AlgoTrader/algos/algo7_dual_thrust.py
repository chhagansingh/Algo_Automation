"""
AlgoTrader — Algo 7: Dual Thrust (India-adapted)
Source: quant-trading-master/Dual Thrust backtest.py

Original Strategy (by Michael Chalek):
  - Opening range breakout on futures/FX
  - Uses previous N-day range to set upper/lower thresholds
  - Buy when price exceeds Upper = Open + K1 * Range
  - Sell when price falls below Lower = Open - K2 * Range
  - Clear all positions at end of day

India Adaptation (Daily Bars):
  - NIFTY daily data
  - Range = max(prev N-day High - prev N-day Close min,
                prev N-day Close max - prev N-day Low)
  - Upper threshold = today's Open + K * Range (lagged by 1 day)
  - Lower threshold = today's Open - K * Range (lagged by 1 day)
  - Enter LONG if High >= Upper (intraday breakout)
  - Enter SHORT if Low <= Lower (intraday breakdown)
  - EOD exit at Close (daily bars cannot track intraday)
  - Only one position per day

NOTE: True Dual Thrust requires intraday (5m/15m) data to check
threshold breaches during the session. Daily-bar proxy is conservative.
"""
import uuid
import pandas as pd
import numpy as np
from typing import Dict, Any, List

from .base import AlgoBase
from utils.logger import (
    log_session_start, log_session_end, log_market_snapshot,
    log_signal_check, log_trade_entry, log_trade_exit, log_backtest_run
)
from data_sources.yf_fetcher import fetch_nifty_data

# ── Adapted constants (tuned for NIFTY daily) ────────────────────────────────
LOT_SIZE         = 25
INITIAL_CAPITAL  = 200_000
DT_PERIOD        = 4          # Look-back period for range (N days)
DT_MULTIPLIER    = 0.5        # K multiplier for threshold width
POS_SIZE_PCT     = 0.10       # 10% of capital per trade


def calculate_range(data: pd.DataFrame, period: int) -> pd.Series:
    """Calculate Dual Thrust range from previous N days."""
    # range1 = prev N-day High max - prev N-day Close min
    range1 = data["High"].rolling(period).max().shift(1) - data["Close"].rolling(period).min().shift(1)
    # range2 = prev N-day Close max - prev N-day Low min
    range2 = data["Close"].rolling(period).max().shift(1) - data["Low"].rolling(period).min().shift(1)
    # Take the larger of the two
    return pd.Series(np.where(range1 > range2, range1, range2), index=data.index)


class Algo7DualThrust(AlgoBase):
    algo_id = "algo7"
    name    = "Dual Thrust"

    def run_backtest(self, start_date: str, end_date: str, interval: str = "1d") -> Dict[str, Any]:
        data = fetch_nifty_data(start_date, end_date, interval=interval)
        if data.empty:
            return {"metrics": self._metrics([], INITIAL_CAPITAL), "trades": [],
                    "monthly": {}, "equity_curve": []}

        data = data[data.index.dayofweek < 5]

        # ── Calculate Dual Thrust range and thresholds ──────────────────
        data["Range"] = calculate_range(data, DT_PERIOD)
        data["Upper"] = data["Open"] + DT_MULTIPLIER * data["Range"]
        data["Lower"] = data["Open"] - DT_MULTIPLIER * data["Range"]

        # Lag thresholds by 1 day (known at today's open)
        data["Upper_Known"] = data["Upper"].shift(1)
        data["Lower_Known"] = data["Lower"].shift(1)

        # ── Backtest loop ───────────────────────────────────────────────
        trades: List[Dict] = []
        total_pnl = 0.0
        wins = losses = 0
        balance = INITIAL_CAPITAL
        in_position = False
        position_type = None  # "LONG" or "SHORT"
        entry_px = 0.0
        entry_date = ""
        qty = 0

        for idx, row in data.iterrows():
            date_str = idx.strftime("%Y-%m-%d")
            upper = row["Upper_Known"]
            lower = row["Lower_Known"]

            if pd.isna(upper) or pd.isna(lower):
                continue

            open_px  = float(row["Open"])
            high_px  = float(row["High"])
            low_px   = float(row["Low"])
            close_px = float(row["Close"])
            strike   = round(open_px / 50) * 50

            log_session_start(self.algo_id, self.name, date_str, mode="backtest")
            log_market_snapshot(self.algo_id, open_px, {
                "open": open_px, "high": high_px, "low": low_px,
                "close": close_px,
                "upper": round(float(upper), 2), "lower": round(float(lower), 2),
            })

            # Determine signal: did price break upper or lower?
            long_sig  = high_px >= upper
            short_sig = low_px <= lower

            # If already in position, exit at EOD
            if in_position:
                if position_type == "LONG":
                    pnl_val = (close_px - entry_px) * qty
                else:
                    pnl_val = (entry_px - close_px) * qty

                won = pnl_val > 0
                tid = str(uuid.uuid4())[:8]

                log_trade_exit(
                    self.algo_id, tid, f"{date_str} 15:25:00", close_px,
                    "EOD_EXIT", pnl_val,
                    round(pnl_val / (entry_px * qty) * 100, 2) if entry_px else 0,
                    context={"close": close_px, "upper": round(float(upper), 2),
                             "lower": round(float(lower), 2)}
                )

                trades.append({
                    "trade_id": tid, "algo_id": self.algo_id, "date": entry_date,
                    "symbol": "NIFTY", "strike": round(entry_px / 50) * 50,
                    "option_type": "CE" if position_type == "LONG" else "PE",
                    "signal_name": f"DT_{position_type}",
                    "entry_time": f"{entry_date} 09:20:00", "entry_price": round(entry_px, 2),
                    "exit_time": f"{date_str} 15:25:00", "exit_price": round(close_px, 2),
                    "exit_reason": "EOD_EXIT", "pnl": round(pnl_val, 2),
                    "lot_size": LOT_SIZE, "status": "closed", "qty": qty,
                })

                total_pnl += pnl_val
                balance += pnl_val
                if won:
                    wins += 1
                else:
                    losses += 1

                in_position = False
                position_type = None
                log_session_end(self.algo_id, 1, pnl_val, status="OK")

            # Enter new position (only if not already in one)
            if not in_position:
                if long_sig:
                    pos_value = balance * POS_SIZE_PCT
                    qty = max(1, int(pos_value / open_px))
                    entry_px = open_px
                    in_position = True
                    position_type = "LONG"
                    entry_date = date_str

                    tid = str(uuid.uuid4())[:8]
                    log_signal_check(
                        self.algo_id, "DT_BUY", eligible=True,
                        reason=(f"High({high_px:.1f}) >= Upper({upper:.1f}) → breakout LONG"),
                        context={"upper": round(float(upper), 2), "entry": entry_px, "qty": qty},
                        timestamp="09:20:00"
                    )
                    log_trade_entry(
                        self.algo_id, tid, "DT_BUY", open_px, strike, "CE",
                        entry_px, f"{date_str} 09:20:00", qty,
                        context={"upper": round(float(upper), 2), "capital_pct": POS_SIZE_PCT}
                    )

                elif short_sig:
                    pos_value = balance * POS_SIZE_PCT
                    qty = max(1, int(pos_value / open_px))
                    entry_px = open_px
                    in_position = True
                    position_type = "SHORT"
                    entry_date = date_str

                    tid = str(uuid.uuid4())[:8]
                    log_signal_check(
                        self.algo_id, "DT_SELL", eligible=True,
                        reason=(f"Low({low_px:.1f}) <= Lower({lower:.1f}) → breakdown SHORT"),
                        context={"lower": round(float(lower), 2), "entry": entry_px, "qty": qty},
                        timestamp="09:20:00"
                    )
                    log_trade_entry(
                        self.algo_id, tid, "DT_SELL", open_px, strike, "PE",
                        entry_px, f"{date_str} 09:20:00", qty,
                        context={"lower": round(float(lower), 2), "capital_pct": POS_SIZE_PCT}
                    )

            if not in_position and not long_sig and not short_sig:
                log_signal_check(
                    self.algo_id, "DT_NO_TRADE", eligible=False,
                    reason=(f"Price between Upper({upper:.1f}) and Lower({lower:.1f}) → no breakout"),
                    context={"upper": round(float(upper), 2), "lower": round(float(lower), 2)},
                    timestamp="09:20:00"
                )
                log_session_end(self.algo_id, 0, 0.0, status="NO_TRADE")

        # Close any open position at end
        if in_position and len(data) > 0:
            last = data.iloc[-1]
            close_px = float(last["Close"])
            date_str = last.name.strftime("%Y-%m-%d")

            if position_type == "LONG":
                pnl_val = (close_px - entry_px) * qty
            else:
                pnl_val = (entry_px - close_px) * qty

            won = pnl_val > 0
            tid = str(uuid.uuid4())[:8]

            log_trade_exit(
                self.algo_id, tid, f"{date_str} 15:25:00", close_px,
                "EOD_CLOSE", pnl_val,
                round(pnl_val / (entry_px * qty) * 100, 2) if entry_px else 0,
                context={"close": close_px}
            )

            trades.append({
                "trade_id": tid, "algo_id": self.algo_id, "date": entry_date,
                "symbol": "NIFTY", "strike": round(entry_px / 50) * 50,
                "option_type": "CE" if position_type == "LONG" else "PE",
                "signal_name": f"DT_{position_type}",
                "entry_time": f"{entry_date} 09:20:00", "entry_price": round(entry_px, 2),
                "exit_time": f"{date_str} 15:25:00", "exit_price": round(close_px, 2),
                "exit_reason": "EOD_CLOSE", "pnl": round(pnl_val, 2),
                "lot_size": LOT_SIZE, "status": "closed", "qty": qty,
            })

            total_pnl += pnl_val
            if won:
                wins += 1
            else:
                losses += 1

        if trades:
            wr = wins / len(trades) * 100
            log_backtest_run(self.algo_id, start_date, end_date, len(trades), wr, total_pnl)

        pnl_list = [t["pnl"] for t in trades]

        last = data.iloc[-1]
        upper_last = float(last["Upper"]) if pd.notna(last["Upper"]) else 0
        lower_last = float(last["Lower"]) if pd.notna(last["Lower"]) else 0
        signal_cards = {
            "Spot":       round(float(last["Close"]), 0),
            "Upper":      round(upper_last, 1),
            "Lower":      round(lower_last, 1),
            "DT_Period":  DT_PERIOD,
            "DT_K":       DT_MULTIPLIER,
        }

        return {
            "metrics":      self._metrics(pnl_list, INITIAL_CAPITAL),
            "trades":       trades,
            "monthly":      self._monthly_breakdown(trades),
            "equity_curve": self._equity_curve(trades),
            "signal_cards": signal_cards,
        }

    def get_live_signal(self, spot: float, indicators: Dict[str, float]) -> Dict[str, Any]:
        upper = indicators.get("dt_upper", 0.0)
        lower = indicators.get("dt_lower", 0.0)
        high  = indicators.get("high", spot)
        low   = indicators.get("low", spot)

        if high >= upper and upper > 0:
            strike = round(spot / 50) * 50
            return {
                "signal":       "DT_BUY",
                "option_type":  "CE",
                "strike":       strike,
                "signal_cards": {
                    "Spot": spot, "Upper": round(upper, 1), "Lower": round(lower, 1),
                    "DT_Period": DT_PERIOD, "DT_K": DT_MULTIPLIER,
                },
            }
        elif low <= lower and lower > 0:
            strike = round(spot / 50) * 50
            return {
                "signal":       "DT_SELL",
                "option_type":  "PE",
                "strike":       strike,
                "signal_cards": {
                    "Spot": spot, "Upper": round(upper, 1), "Lower": round(lower, 1),
                    "DT_Period": DT_PERIOD, "DT_K": DT_MULTIPLIER,
                },
            }

        return {
            "signal":       "NO_TRADE",
            "option_type":  None,
            "strike":       None,
            "signal_cards": {
                "Spot": spot, "Upper": round(upper, 1), "Lower": round(lower, 1),
                "DT_Period": DT_PERIOD, "DT_K": DT_MULTIPLIER,
            },
        }
