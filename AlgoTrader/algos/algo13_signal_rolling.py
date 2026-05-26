"""
AlgoTrader — Algo 13: Signal Rolling (Consecutive-Close Momentum)
Source: Stock-Prediction-Models-master/agent/3.signal-rolling-agent.ipynb

Original Strategy:
  - Buy after N consecutive up closes, sell after N consecutive down closes
  - Equity-only, 1 unit per trade

India Adaptation:
  - Buy ATM CE after 3 consecutive up closes on NIFTY
  - Buy ATM PE after 3 consecutive down closes on NIFTY
  - Exit: 50% SL on option premium / 1:2 R:R target / 5-day max hold
  - Black-Scholes pricing with BASE_IV=0.13, 5-day expiry
  - Position: 5% capital per trade (directional)
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

# Signal Rolling parameters (optimized for NIFTY daily)
ROLL_DELAY       = 3          # Consecutive closes required
SL_PCT           = 0.50
RR_RATIO         = 2.0
MAX_HOLD_DAYS    = 5


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


class Algo13SignalRolling(AlgoBase):
    algo_id = "algo13"
    name    = "Signal Rolling Momentum"

    def _generate_signals(self, nifty: pd.DataFrame) -> pd.DataFrame:
        """Generate consecutive-close momentum signals."""
        df = nifty.copy()
        closes = df["Close"].values
        signals = np.zeros(len(closes), dtype=int)
        streak = 0
        direction = 0
        for i in range(1, len(closes)):
            diff = closes[i] - closes[i-1]
            if diff > 0:
                if direction >= 0:
                    direction = 1
                    streak += 1
                else:
                    direction = 1
                    streak = 1
            elif diff < 0:
                if direction <= 0:
                    direction = -1
                    streak += 1
                else:
                    direction = -1
                    streak = 1
            else:
                streak = 0
            if streak >= ROLL_DELAY:
                signals[i] = 1 if direction > 0 else -1
        df["Signal"] = signals
        return df

    def run_backtest(self, start_date: str, end_date: str, interval: str = "1d") -> Dict[str, Any]:
        nifty = fetch_nifty_data(start_date, end_date, interval=interval)
        if nifty.empty:
            return {"metrics": self._metrics([], INITIAL_CAPITAL), "trades": [],
                    "monthly": {}, "equity_curve": []}

        nifty = nifty[nifty.index.dayofweek < 5]
        nifty = self._generate_signals(nifty)

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
            signal   = int(row["Signal"]) if pd.notna(row["Signal"]) else 0

            log_market_snapshot(self.algo_id, open_px, {
                "open": open_px, "high": high_px, "low": low_px,
                "close": close_px, "signal": signal,
            })

            # ── Manage active position ─────────────────────────────────────
            if active_pos is not None:
                pos = active_pos
                pos["days_held"] += 1
                dte_x = max(0.1, pos["entry_dte"] - pos["days_held"])
                opt_type = pos["option_type"]

                sl_px = pos["entry_px"] * (1.0 - SL_PCT)
                tgt_px = pos["entry_px"] * (1.0 + SL_PCT * RR_RATIO)

                # Check exits using high/low for stop/target
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
                        self.algo_id, "ROLL_HOLD", eligible=False,
                        reason=f"Holding {opt_type} day {pos['days_held']}/{MAX_HOLD_DAYS}",
                        context={"entry_px": pos["entry_px"]}, timestamp="09:20:00"
                    )
                    continue

                if exit_px is not None:
                    pnl_val = (exit_px - pos["entry_px"]) * LOT_SIZE * pos["qty"] - TX_COST_SINGLE * pos["qty"]
                    won = pnl_val > 0

                    log_trade_exit(
                        self.algo_id, pos["tid"], f"{date_str} 15:25:00", round(exit_px, 2),
                        exit_r, round(pnl_val, 2),
                        round(pnl_val / (pos["entry_px"] * LOT_SIZE * pos["qty"]) * 100, 2) if pos["entry_px"] > 0 else 0,
                        context={"close": close_px, "high": high_px, "low": low_px, "days_held": pos["days_held"]}
                    )

                    trades.append({
                        "trade_id": pos["tid"], "algo_id": self.algo_id, "date": pos["entry_date"],
                        "symbol": "NIFTY", "strike": pos["strike"],
                        "option_type": opt_type, "signal_name": f"ROLL_{opt_type}",
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
                    self.algo_id, "ROLL_SKIP", eligible=False,
                    reason="Daily loss limit hit", context={"daily_pnl": round(daily_pnl, 2)},
                    timestamp="09:20:00"
                )
                continue

            if signal == 0:
                log_signal_check(
                    self.algo_id, "ROLL_NONE", eligible=False,
                    reason=f"No consecutive {ROLL_DELAY}-day momentum signal",
                    context={"close": close_px}, timestamp="09:20:00"
                )
                continue

            # Signal active → open position
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
                context={"signal": signal, "open": open_px, "dte": dte}
            )
            log_signal_check(
                self.algo_id, f"ROLL_BUY_{option_type}", eligible=True,
                reason=f"{ROLL_DELAY}-day {'up' if signal==1 else 'down'} streak detected",
                context={"open": open_px, "strike": strike, "entry_px": round(entry_px, 2),
                         "qty": qty, "dte": dte}, timestamp="09:20:00"
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
        streak = indicators.get("streak", 0)
        direction = indicators.get("direction", 0)
        if streak >= ROLL_DELAY and direction != 0:
            opt_type = "CE" if direction > 0 else "PE"
            strike = atm(spot)
            entry_px = bs_price(spot, strike, EXPIRY_DAYS, BASE_IV, opt_type)
            return {
                "signal": f"ROLL_BUY_{opt_type}",
                "option_type": opt_type,
                "strike": strike,
                "signal_cards": {
                    "Spot": spot, "Streak": streak, "Direction": "UP" if direction > 0 else "DOWN",
                    "Entry_Px": round(entry_px, 2), "DTE": EXPIRY_DAYS,
                },
            }
        return {
            "signal": "NO_TRADE",
            "option_type": None,
            "strike": None,
            "signal_cards": {"Spot": spot, "Streak": streak, "Direction": direction},
        }
