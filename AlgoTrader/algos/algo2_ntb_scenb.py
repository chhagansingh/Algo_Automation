"""
AlgoTrader — Algo 2: NiftyTradeBot ScenB
Source: nifty_tradebot-main/backtest_may2025.py — Scenario B (exact logic, zero changes)

Strategy (ScenB — realistic close-move filter):
  - Entry: daily range < 1%  → eligible
  - Win condition: close move < 0.7% from open (directional risk filtered)
  - WIN  P/L = (TARGET_PER_LEG * 2 * LOT_SIZE) - TRANSACTION_COST = ₹3,800
  - LOSS P/L = -(STOP_PER_LEG * 2 * LOT_SIZE) - TRANSACTION_COST  = -₹10,200
"""
import uuid
import pandas as pd
import numpy as np
import yfinance as yf
from typing import Dict, Any, List

from .base import AlgoBase
from utils.logger import (
    log_session_start, log_session_end, log_market_snapshot,
    log_signal_check, log_trade_entry, log_trade_exit, log_backtest_run
)
from data_sources.yf_fetcher import fetch_nifty_data

# ── Exact constants from nifty_tradebot backtest_may2025.py ───────────────────
MOVEMENT_THRESHOLD = 1.0
LOT_SIZE           = 25
PREMIUM_PER_LEG    = 120
TARGET_PER_LEG     = 80
STOP_PER_LEG       = 200
TRANSACTION_COST   = 200
INITIAL_CAPITAL    = 200_000

WIN_PNL  = (TARGET_PER_LEG * 2 * LOT_SIZE) - TRANSACTION_COST   # ₹3,800
LOSS_PNL = -(STOP_PER_LEG * 2 * LOT_SIZE) - TRANSACTION_COST    # -₹10,200


class Algo2NTBScenB(AlgoBase):
    algo_id = "algo2"
    name    = "NiftyTradeBot ScenB"

    def run_backtest(self, start_date: str, end_date: str, interval: str = "1d") -> Dict[str, Any]:
        # ── 1. Fetch data with custom interval ────────────────────────────────
        data = fetch_nifty_data(start_date, end_date, interval=interval)
        if data.empty:
            return {"metrics": self._metrics([], INITIAL_CAPITAL), "trades": [],
                    "monthly": {}, "equity_curve": []}

        data = data[data.index.dayofweek < 5]

        # ── 2. Strategy calculations (exact from ntb backtest_may2025.py) ─────
        data["Daily_Move_Pct"] = ((data["High"] - data["Low"]) / data["Open"]) * 100
        data["Close_Move_Pct"] = abs((data["Close"] - data["Open"]) / data["Open"]) * 100
        data["Trade_Taken"]    = data["Daily_Move_Pct"] < MOVEMENT_THRESHOLD

        # ScenB: win only if close move < 0.7%
        data["PnL_Revised"] = np.where(
            ~data["Trade_Taken"], 0,
            np.where(data["Close_Move_Pct"] < 0.7, WIN_PNL, LOSS_PNL)
        )

        # ── 3. Build trades list with full audit logging ─────────────────────────
        trades: List[Dict] = []
        total_pnl = 0.0
        for idx, row in data.iterrows():
            date_str = idx.strftime("%Y-%m-%d")
            log_session_start(self.algo_id, self.name, date_str, mode="backtest")

            open_px  = float(row["Open"])
            high_px  = float(row["High"])
            low_px   = float(row["Low"])
            close_px = float(row["Close"])
            daily_move = float(row["Daily_Move_Pct"])
            close_move = float(row["Close_Move_Pct"])
            trade_taken = bool(row["Trade_Taken"])

            # Log market snapshot
            log_market_snapshot(self.algo_id, open_px, {
                "open": open_px, "high": high_px, "low": low_px,
                "close": close_px, "daily_range_pct": round(daily_move, 2),
                "close_move_pct": round(close_move, 2)
            })

            if not trade_taken:
                log_signal_check(
                    self.algo_id, "SHORT_STRADDLE", eligible=False,
                    reason=f"daily_range {daily_move:.2f}% >= {MOVEMENT_THRESHOLD}% → no trade",
                    context={"daily_range_pct": daily_move, "close_move_pct": close_move,
                             "open": open_px, "high": high_px, "low": low_px},
                    timestamp="09:20:00"
                )
                log_session_end(self.algo_id, 0, 0.0, status="NO_TRADE")
                continue

            # Trade eligible — log signal pass
            pnl_val = float(row["PnL_Revised"])
            won     = pnl_val > 0
            spot    = open_px
            strike  = round(spot / 50) * 50
            exit_px = (PREMIUM_PER_LEG - TARGET_PER_LEG) if won else (PREMIUM_PER_LEG + STOP_PER_LEG)
            exit_r  = "THRESHOLD_EXIT" if won else "CLOSE_MOVE_EXIT"

            log_signal_check(
                self.algo_id, "SHORT_STRADDLE", eligible=True,
                reason=f"daily_range {daily_move:.2f}% < {MOVEMENT_THRESHOLD}% → trade eligible; "
                       f"close_move {close_move:.2f}% {'< 0.7% → WIN' if won else '>= 0.7% → LOSS'}",
                context={"daily_range_pct": daily_move, "close_move_pct": close_move,
                         "open": open_px, "high": high_px, "low": low_px, "close": close_px},
                timestamp="09:20:00"
            )

            tid = str(uuid.uuid4())[:8]
            log_trade_entry(
                self.algo_id, tid, "SHORT_STRADDLE", spot, strike, "BOTH",
                PREMIUM_PER_LEG, f"{date_str} 09:20:00", LOT_SIZE,
                context={"daily_range_pct": daily_move, "close_move_pct": close_move,
                         "expected_pnl": "WIN ₹3,800" if won else "LOSS -₹10,200"}
            )
            log_trade_exit(
                self.algo_id, tid, f"{date_str} 15:25:00", exit_px,
                exit_r, pnl_val,
                round(pnl_val / (PREMIUM_PER_LEG * 2 * LOT_SIZE) * 100, 2),
                context={"close": close_px, "close_move_pct": close_move}
            )

            trades.append({
                "trade_id":    tid,
                "algo_id":     "algo2",
                "date":        date_str,
                "symbol":      "NIFTY",
                "strike":      strike,
                "option_type": "BOTH",
                "signal_name": "SHORT_STRADDLE",
                "entry_time":  f"{date_str} 09:20:00",
                "entry_price": PREMIUM_PER_LEG,
                "exit_time":   f"{date_str} 15:25:00",
                "exit_price":  exit_px,
                "exit_reason": exit_r,
                "pnl":         round(pnl_val, 2),
                "pnl_pct":     round(pnl_val / (PREMIUM_PER_LEG * 2 * LOT_SIZE) * 100, 2),
                "lot_size":    LOT_SIZE,
                "status":      "closed",
                "daily_range_pct": round(daily_move, 2),
                "close_move_pct":  round(close_move, 2),
            })
            total_pnl += pnl_val
            log_session_end(self.algo_id, 1, pnl_val, status="OK")

        pnl_list = [t["pnl"] for t in trades]
        if trades:
            wr = sum(1 for p in pnl_list if p > 0) / len(trades) * 100
            log_backtest_run(self.algo_id, start_date, end_date, len(trades), wr, total_pnl)

        # ── 4. Signal cards (latest bar) ──────────────────────────────────────
        last = data.iloc[-1]
        signal_cards = {
            "Daily_Range_%":   round(float(last["Daily_Move_Pct"]), 2),
            "Close_Move_%":    round(float(last["Close_Move_Pct"]), 2),
            "Trade_Eligible":  "YES" if last["Trade_Taken"] else "NO",
            "WIN_PnL":         f"₹{WIN_PNL:,}",
            "LOSS_PnL":        f"₹{LOSS_PNL:,}",
        }

        return {
            "metrics":      self._metrics(pnl_list, INITIAL_CAPITAL),
            "trades":       trades,
            "monthly":      self._monthly_breakdown(trades),
            "equity_curve": self._equity_curve(trades),
            "signal_cards": signal_cards,
        }

    def get_live_signal(self, spot: float, indicators: Dict[str, float]) -> Dict[str, Any]:
        daily_range_pct = indicators.get("daily_range_pct", 0.0)
        close_move_pct  = indicators.get("close_move_pct", 0.0)
        if daily_range_pct < MOVEMENT_THRESHOLD:
            strike = round(spot / 50) * 50
            expected_win = close_move_pct < 0.7
            return {
                "signal":       "SHORT_STRADDLE",
                "option_type":  "BOTH",
                "strike":       strike,
                "signal_cards": {
                    "Daily_Range_%": daily_range_pct,
                    "Close_Move_%":  close_move_pct,
                    "Trade_Eligible": "YES",
                },
            }
        return {
            "signal":       "NO_TRADE",
            "option_type":  None,
            "strike":       None,
            "signal_cards": {
                "Daily_Range_%": daily_range_pct,
                "Close_Move_%":  close_move_pct,
                "Trade_Eligible": "NO",
            },
        }
