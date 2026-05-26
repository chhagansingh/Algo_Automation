"""
AlgoTrader — Algo 1: R&D Binary Straddle
Source: R&D/backtest_strategy.py (exact logic, zero changes)

Strategy:
  - Fetch NIFTY daily OHLCV (yfinance ^NSEI)
  - Entry: daily range (High-Low)/Open < 1%  → Sell ATM Straddle
  - P&L: flat WIN = ₹200 per unit | LOSS = -₹200 per unit (original binary)
  - Exit: same day (daily bars)
"""
import uuid
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
from typing import Dict, Any, List

from .base import AlgoBase
from utils.logger import (
    log_session_start, log_session_end, log_market_snapshot,
    log_signal_check, log_trade_entry, log_trade_exit, log_backtest_run
)
from data_sources.yf_fetcher import fetch_nifty_data

# ── Exact constants from backtest_strategy.py ─────────────────────────────────
LOT_SIZE         = 25
INITIAL_CAPITAL  = 200_000


class Algo1RDStraddle(AlgoBase):
    algo_id = "algo1"
    name    = "R&D Straddle"

    def run_backtest(self, start_date: str, end_date: str, interval: str = "1d") -> Dict[str, Any]:
        # ── 1. Fetch data with custom interval ────────────────────────────────
        data = fetch_nifty_data(start_date, end_date, interval=interval)
        if data.empty:
            return {"metrics": self._metrics([], INITIAL_CAPITAL), "trades": [],
                    "monthly": {}, "equity_curve": []}

        data = data[data.index.dayofweek < 5]

        # ── 2. Strategy calculation (exact from backtest_strategy.py) ─────────
        data["Daily Move %"] = ((data["High"] - data["Low"]) / data["Open"]) * 100
        data["Sell Call P/L"] = np.where(data["Daily Move %"] < 1, 100, -100)
        data["Sell Put P/L"]  = np.where(data["Daily Move %"] < 1, 100, -100)
        data["Total P/L"]     = data["Sell Call P/L"] + data["Sell Put P/L"]
        data["Cumulative P/L"] = data["Total P/L"].cumsum()

        # ── 3. Build trades list with full audit logging ───────────────────────
        trades: List[Dict] = []
        total_pnl = 0.0
        wins = 0
        losses = 0
        for idx, row in data.iterrows():
            date_str = idx.strftime("%Y-%m-%d")
            log_session_start(self.algo_id, self.name, date_str, mode="backtest")

            open_px = float(row["Open"])
            high_px = float(row["High"])
            low_px  = float(row["Low"])
            close_px = float(row["Close"])
            daily_move = float(row["Daily Move %"])
            pnl_val  = float(row["Total P/L"])
            won      = pnl_val > 0
            signal   = "STRADDLE_SELL"
            exit_r   = "TARGET_EXIT" if won else "SL_EXIT"
            spot     = open_px
            strike   = round(spot / 50) * 50

            # Log market snapshot before signal check
            log_market_snapshot(self.algo_id, open_px, {
                "open": open_px, "high": high_px, "low": low_px,
                "close": close_px, "daily_range_pct": round(daily_move, 2)
            })

            # Log signal check
            if daily_move < 1.0:
                log_signal_check(
                    self.algo_id, signal, eligible=True,
                    reason=f"daily_range {daily_move:.2f}% < 1% threshold → straddle eligible",
                    context={"open": open_px, "high": high_px, "low": low_px,
                             "close": close_px, "daily_range_pct": daily_move},
                    timestamp="09:20:00"
                )
            else:
                log_signal_check(
                    self.algo_id, signal, eligible=False,
                    reason=f"daily_range {daily_move:.2f}% >= 1% threshold → no trade",
                    context={"open": open_px, "high": high_px, "low": low_px,
                             "close": close_px, "daily_range_pct": daily_move},
                    timestamp="09:20:00"
                )

            # Log trade entry
            log_trade_entry(
                self.algo_id, trade_id=str(uuid.uuid4())[:8], signal=signal,
                spot=spot, strike=strike, option_type="BOTH",
                entry_price=100.0, entry_time=f"{date_str} 09:20:00",
                lot_size=LOT_SIZE,
                context={"daily_range_pct": daily_move, "open": open_px}
            )

            # Log trade exit
            exit_price = 0.0 if won else 200.0
            log_trade_exit(
                self.algo_id, trade_id=str(uuid.uuid4())[:8],
                exit_time=f"{date_str} 15:25:00", exit_price=exit_price,
                exit_reason=exit_r, pnl=pnl_val,
                pnl_pct=round(pnl_val / (100 * 2) * 100, 2),
                context={"close": close_px, "daily_range_pct": daily_move}
            )

            total_pnl += pnl_val
            if won:
                wins += 1
            else:
                losses += 1

            trades.append({
                "trade_id":    str(uuid.uuid4())[:8],
                "algo_id":     "algo1",
                "date":        date_str,
                "symbol":      "NIFTY",
                "strike":      strike,
                "option_type": "BOTH",       # sell both CE + PE
                "signal_name": signal,
                "entry_time":  f"{date_str} 09:20:00",
                "entry_price": 100.0,        # binary model: flat ₹100/unit premium
                "exit_time":   f"{date_str} 15:25:00",
                "exit_price":  exit_price,
                "exit_reason": exit_r,
                "pnl":         round(pnl_val, 2),
                "pnl_pct":     round(pnl_val / (100 * 2) * 100, 2),
                "lot_size":    LOT_SIZE,
                "status":      "closed",
            })

            log_session_end(self.algo_id, 1, pnl_val, status="OK")

        log_backtest_run(
            self.algo_id, start_date, end_date,
            trades=len(trades), win_rate=(wins / len(trades) * 100 if trades else 0),
            pnl=total_pnl
        )

        pnl_list = [t["pnl"] for t in trades]

        # ── 4. Signal cards (last row indicators) ─────────────────────────────
        last = data.iloc[-1]
        signal_cards = {
            "Daily_Range_%":  round(float(last["Daily Move %"]), 2),
            "Trade_Signal":   "SELL" if float(last["Daily Move %"]) < 1.0 else "NO_TRADE",
            "Open":           round(float(last["Open"]), 0),
            "Close":          round(float(last["Close"]), 0),
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
        if daily_range_pct < 1.0:
            strike = round(spot / 50) * 50
            return {
                "signal":       "STRADDLE_SELL",
                "option_type":  "BOTH",
                "strike":       strike,
                "signal_cards": {"Daily_Range_%": daily_range_pct, "Trade_Signal": "SELL"},
            }
        return {
            "signal":       "NO_TRADE",
            "option_type":  None,
            "strike":       None,
            "signal_cards": {"Daily_Range_%": daily_range_pct, "Trade_Signal": "NO_TRADE"},
        }
