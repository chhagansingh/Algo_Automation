"""
AlgoTrader — Algo 12: NIFTY Dip Recovery
Source: lumibot-dev/tests/backtest/acceptance_strategies/AAPL Deep Dip Calls (Copy 4).py

Original Strategy (US):
  - Buy 20% OTM LEAPS calls on GOOG after a 25% decline from running high
  - Hold for ~1 year
  - 50% stop-loss on option premium

India Adaptation:
  - Buy ATM CE on NIFTY after a 3% drop from 20-day running high
  - Hold for up to 5 days or until 2% spot recovery from entry
  - 40% stop-loss on option premium
  - Black-Scholes pricing with BASE_IV=0.13, 7-day expiry
  - Position size: 5% of capital per trade
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

# ── Adapted constants ────────────────────────────────────────────────────────
LOT_SIZE         = 25
INITIAL_CAPITAL  = 200_000
POS_SIZE_PCT     = 0.05        # 5% of capital per trade (directional)
MAX_DAILY_LOSS_PCT = 0.02      # Stop trading after 2% daily loss
TX_COST_SINGLE   = 200
RISK_FREE_RATE   = 0.07
EXPIRY_DAYS      = 7           # Weekly expiry proxy
STRIKE_STEP      = 50
BASE_IV          = 0.13

# Dip recovery parameters (optimized for NIFTY daily backtest)
DRAWDOWN_PCT     = 0.02        # 2% drop from 20-day high triggers entry
RECOVERY_PCT     = 0.04        # 4% spot gain from entry triggers exit
MAX_HOLD_DAYS    = 5           # Max hold 5 days
SL_PCT           = 0.50        # 50% stop-loss on option premium


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


class Algo12DipRecovery(AlgoBase):
    algo_id = "algo12"
    name    = "NIFTY Dip Recovery"

    def run_backtest(self, start_date: str, end_date: str, interval: str = "1d") -> Dict[str, Any]:
        nifty = fetch_nifty_data(start_date, end_date, interval=interval)
        if nifty.empty:
            return {"metrics": self._metrics([], INITIAL_CAPITAL), "trades": [],
                    "monthly": {}, "equity_curve": []}

        nifty = nifty[nifty.index.dayofweek < 5]

        # ── Running 20-day high (look-ahead safe: uses shift) ────────────────
        nifty["Rolling_High"] = nifty["High"].rolling(window=20).max().shift(1)
        nifty["Drawdown_Pct"] = (nifty["Rolling_High"] - nifty["Open"]) / nifty["Rolling_High"]
        nifty["Dip_Signal"] = nifty["Drawdown_Pct"] >= DRAWDOWN_PCT

        # ── Backtest loop with position tracking ─────────────────────────────
        trades: List[Dict] = []
        total_pnl = 0.0
        wins = losses = 0
        balance = INITIAL_CAPITAL
        daily_pnl = 0.0
        daily_date = None
        hit_daily_loss = False

        # Active position tracking (for multi-day holds)
        active_pos = None  # {entry_date, entry_open, entry_px, strike, qty, days_held, entry_dte}

        for idx, row in nifty.iterrows():
            date_str = idx.strftime("%Y-%m-%d")

            # Daily loss limit reset
            if date_str != daily_date:
                daily_date = date_str
                daily_pnl = 0.0
                hit_daily_loss = False

            log_session_start(self.algo_id, self.name, date_str, mode="backtest")

            open_px  = float(row["Open"])
            high_px  = float(row["High"])
            low_px   = float(row["Low"])
            close_px = float(row["Close"])
            roll_high = float(row["Rolling_High"]) if pd.notna(row["Rolling_High"]) else open_px
            dd_pct   = float(row["Drawdown_Pct"]) if pd.notna(row["Drawdown_Pct"]) else 0.0
            dip_sig  = bool(row["Dip_Signal"]) if pd.notna(row["Dip_Signal"]) else False

            log_market_snapshot(self.algo_id, open_px, {
                "open": open_px, "high": high_px, "low": low_px,
                "close": close_px, "roll_high": round(roll_high, 2),
                "drawdown_pct": round(dd_pct * 100, 2),
            })

            # ── Manage active position ─────────────────────────────────────
            if active_pos is not None:
                pos = active_pos
                pos["days_held"] += 1
                dte_x = max(0.1, pos["entry_dte"] - pos["days_held"])

                # Check exits
                recovery_target = pos["entry_open"] * (1.0 + RECOVERY_PCT)
                exit_px = None
                exit_r = None

                # 1) Recovery exit: spot gained 2% from entry
                if high_px >= recovery_target:
                    exit_px = bs_price(recovery_target, pos["strike"], dte_x, BASE_IV, "CE")
                    exit_r = "RECOVERY_EXIT"
                else:
                    # 2) SL on option premium
                    sl_px = pos["entry_px"] * (1.0 - SL_PCT)
                    # Approximate option price at low
                    opt_at_low = bs_price(low_px, pos["strike"], dte_x, BASE_IV, "CE")
                    if opt_at_low <= sl_px:
                        exit_px = opt_at_low
                        exit_r = "SL_EXIT"
                    else:
                        # 3) Max hold days
                        if pos["days_held"] >= MAX_HOLD_DAYS:
                            exit_px = bs_price(close_px, pos["strike"], dte_x, BASE_IV, "CE")
                            exit_r = "MAX_HOLD_EXIT"
                        else:
                            # Still holding — skip new entries
                            log_signal_check(
                                self.algo_id, "DIP_HOLD", eligible=False,
                                reason=f"Holding dip position day {pos['days_held']}/{MAX_HOLD_DAYS}",
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
                        "option_type": "CE", "signal_name": "DIP_BUY_CE",
                        "entry_time": f"{pos['entry_date']} 09:20:00", "entry_price": round(pos["entry_px"], 2),
                        "exit_time": f"{date_str} 15:25:00", "exit_price": round(exit_px, 2),
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
                    continue  # No new entry on same day we exit

            # ── New entry check ────────────────────────────────────────────
            if dip_sig and not hit_daily_loss and active_pos is None:
                k = atm(open_px)
                dte_e = EXPIRY_DAYS
                entry_px = bs_price(open_px, k, dte_e, BASE_IV, "CE")
                qty = max(1, int(balance * POS_SIZE_PCT / (entry_px * LOT_SIZE)))
                tid = str(uuid.uuid4())[:8]

                log_signal_check(
                    self.algo_id, "DIP_BUY_CE", eligible=True,
                    reason=(f"Open {open_px:.0f} is {dd_pct*100:.1f}% below 20-day high {roll_high:.0f} "
                            f"→ buy ATM CE recovery"),
                    context={"entry_px": round(entry_px, 2), "qty": qty, "strike": k}, timestamp="09:20:00"
                )

                log_trade_entry(
                    self.algo_id, tid, "DIP_BUY_CE", open_px, k, "CE",
                    round(entry_px, 2), f"{date_str} 09:20:00", LOT_SIZE * qty,
                    context={"iv": BASE_IV, "capital_pct": POS_SIZE_PCT, "dte": dte_e}
                )

                active_pos = {
                    "tid": tid,
                    "entry_date": date_str,
                    "entry_open": open_px,
                    "entry_px": entry_px,
                    "strike": k,
                    "qty": qty,
                    "days_held": 0,
                    "entry_dte": dte_e,
                }
            else:
                reason = "Daily loss limit hit" if hit_daily_loss else (
                    f"Drawdown {dd_pct*100:.1f}% < {DRAWDOWN_PCT*100:.1f}% threshold" if not dip_sig else "Already in position"
                )
                log_signal_check(
                    self.algo_id, "DIP_BUY_CE", eligible=False,
                    reason=reason, context={"roll_high": roll_high, "drawdown_pct": dd_pct}, timestamp="09:20:00"
                )

            log_session_end(self.algo_id, 1 if active_pos is not None else 0, daily_pnl, status="OK")

        # Close any remaining open position at last available price
        if active_pos is not None and not trades.empty:
            # Already handled in loop; if last day is open, we skip (no future data)
            pass

        metrics = self._metrics([t["pnl"] for t in trades], INITIAL_CAPITAL)
        log_backtest_run(self.algo_id, start_date, end_date,
                         metrics["total_trades"], metrics["win_rate"], metrics["final_pnl"])

        return {
            "metrics": metrics,
            "trades": trades,
            "monthly": self._monthly_breakdown(trades),
            "equity_curve": self._equity_curve(trades),
        }

    def get_live_signal(self, spot: float, indicators: Dict[str, float]) -> Dict[str, Any]:
        roll_high = indicators.get("rolling_high", spot)
        dd_pct = (roll_high - spot) / roll_high if roll_high > 0 else 0.0
        in_dip = dd_pct >= DRAWDOWN_PCT
        strike = atm(spot)

        if in_dip:
            dte = EXPIRY_DAYS
            entry_px = bs_price(spot, strike, dte, BASE_IV, "CE")
            return {
                "signal": "DIP_BUY_CE",
                "option_type": "CE",
                "strike": strike,
                "signal_cards": {
                    "Spot": round(spot, 2),
                    "Roll_High": round(roll_high, 2),
                    "Drawdown_%": round(dd_pct * 100, 1),
                    "Trigger_%": DRAWDOWN_PCT * 100,
                    "Entry_Px": round(entry_px, 2),
                    "DTE": dte,
                },
            }

        return {
            "signal": "NO_TRADE",
            "option_type": None,
            "strike": None,
            "signal_cards": {
                "Spot": round(spot, 2),
                "Roll_High": round(roll_high, 2),
                "Drawdown_%": round(dd_pct * 100, 1),
                "Trigger_%": DRAWDOWN_PCT * 100,
                "Reason": "No significant dip",
            },
        }
