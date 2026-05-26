"""
AlgoTrader — Algo 5: VIX Mean-Reversion (India-adapted)
Source: Options-Trading-Strategies-in-Python-master/VIX_Strategy.py

Original Strategy (US):
  - Buy S&P 500 futures when VIX >= 22
  - Target: +5% gain | Stop: -5% loss

India Adaptation (Revived):
  - Buy ATM CE when prev-day India VIX >= 19 (fear-spike mean-reversion)
  - Target: +2% spot gain | Stop: -2% spot loss
  - Entry at next-day Open (lagged signal to avoid look-ahead bias)
  - BS option pricing with IV = India VIX / 100
  - Position size: 5% of capital per trade
  - Daily loss limit: 2% of capital
"""
import uuid
import math
import pandas as pd
import numpy as np
import yfinance as yf
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
VIX_THRESHOLD    = 19.0        # India VIX threshold (lowered from 20 for more signals)
TARGET_GAIN_PCT  = 0.02        # +2% target (tightened from 5%)
STOP_LOSS_PCT    = 0.02        # -2% stop loss (tightened from 5%)
POS_SIZE_PCT     = 0.05        # 5% of capital per trade (halved from 10%)
MAX_DAILY_LOSS_PCT = 0.02      # Stop trading after 2% daily loss
RISK_FREE_RATE   = 0.07
EXPIRY_DAYS      = 3
TX_COST_SINGLE   = 200
STRIKE_STEP      = 50


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


def fetch_india_vix(start_date: str, end_date: str) -> pd.DataFrame:
    """Fetch India VIX historical data from yfinance."""
    data = yf.download("^INDIAVIX", start=start_date, end=end_date, progress=False)
    if data.empty:
        return pd.DataFrame()
    # yfinance returns multi-index columns, flatten
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    data = data[['Open', 'High', 'Low', 'Close']]
    data.index = pd.to_datetime(data.index)
    return data


class Algo5VIXReversion(AlgoBase):
    algo_id = "algo5"
    name    = "VIX Reversion"

    def run_backtest(self, start_date: str, end_date: str, interval: str = "1d") -> Dict[str, Any]:
        # Fetch NIFTY and India VIX data
        nifty = fetch_nifty_data(start_date, end_date, interval=interval)
        vix = fetch_india_vix(start_date, end_date)

        if nifty.empty or vix.empty:
            return {"metrics": self._metrics([], INITIAL_CAPITAL), "trades": [],
                    "monthly": {}, "equity_curve": []}

        nifty = nifty[nifty.index.dayofweek < 5]

        # Align VIX with NIFTY dates
        vix = vix.reindex(nifty.index, method='ffill')

        # ── Generate signal: VIX >= threshold (lagged by 1 day) ───────────
        # We use PREVIOUS day's VIX to decide TODAY's entry
        nifty["VIX"] = vix["Close"]
        nifty["VIX_Signal"] = nifty["VIX"].shift(1) >= VIX_THRESHOLD

        # ── Backtest loop ───────────────────────────────────────────────────
        trades: List[Dict] = []
        total_pnl = 0.0
        wins = losses = 0
        balance = INITIAL_CAPITAL
        daily_pnl = 0.0
        daily_date = None
        hit_daily_loss = False

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
            vix_val  = float(row["VIX"]) if pd.notna(row["VIX"]) else 0.0
            signal   = bool(row["VIX_Signal"]) if pd.notna(row["VIX_Signal"]) else False
            strike   = round(open_px / 50) * 50

            log_market_snapshot(self.algo_id, open_px, {
                "open": open_px, "high": high_px, "low": low_px,
                "close": close_px, "vix": round(vix_val, 2),
                "vix_threshold": VIX_THRESHOLD,
            })

            if signal and not hit_daily_loss:
                # ATM CE on fear spike: buy when VIX is elevated, capture mean-reversion
                k = atm(open_px)
                iv = max(0.10, vix_val / 100.0)  # Realistic IV from India VIX
                dte_e = EXPIRY_DAYS
                dte_x = max(0.1, dte_e - 1 / 252)

                entry_px = bs_price(open_px, k, dte_e, iv, "CE")

                # Position size: 5% of capital, in lots
                qty = max(1, int(balance * POS_SIZE_PCT / (entry_px * LOT_SIZE)))

                # Check target and stop against intraday high/low (spot levels)
                target_spot = open_px * (1 + TARGET_GAIN_PCT)
                stop_spot = open_px * (1 - STOP_LOSS_PCT)

                # Determine exit: did we hit target, stop, or EOD?
                if high_px >= target_spot:
                    exit_px = bs_price(target_spot, k, dte_x, iv, "CE")
                    exit_r = "TARGET_EXIT"
                elif low_px <= stop_spot:
                    exit_px = bs_price(stop_spot, k, dte_x, iv, "CE")
                    exit_r = "SL_EXIT"
                else:
                    exit_px = bs_price(close_px, k, dte_x, iv, "CE")
                    exit_r = "EOD_EXIT"

                pnl_val = (exit_px - entry_px) * LOT_SIZE * qty - TX_COST_SINGLE * qty
                won = pnl_val > 0
                tid = str(uuid.uuid4())[:8]

                log_signal_check(
                    self.algo_id, "VIX_BUY_CE", eligible=True,
                    reason=(f"Prev-day India VIX ({vix_val:.1f}) >= {VIX_THRESHOLD} "
                            f"→ fear spike, buy ATM CE mean-reversion"),
                    context={"vix": vix_val, "entry": entry_px, "iv": iv,
                             "target_spot": target_spot, "stop_spot": stop_spot, "qty": qty},
                    timestamp="09:20:00"
                )

                log_trade_entry(
                    self.algo_id, tid, "VIX_BUY_CE", open_px, k, "CE",
                    round(entry_px, 2), f"{date_str} 09:20:00", LOT_SIZE * qty,
                    context={"vix": vix_val, "iv": iv, "capital_pct": POS_SIZE_PCT}
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
                    "option_type": "CE", "signal_name": "VIX_BUY_CE",
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
                reason = (f"VIX ({vix_val:.1f}) < {VIX_THRESHOLD} → no fear spike"
                          if not signal else "Daily loss limit hit → paused")
                log_signal_check(
                    self.algo_id, "VIX_BUY_CE", eligible=False,
                    reason=reason,
                    context={"vix": vix_val, "threshold": VIX_THRESHOLD},
                    timestamp="09:20:00"
                )
                log_session_end(self.algo_id, 0, 0.0, status="NO_TRADE")

        if trades:
            wr = wins / len(trades) * 100
            log_backtest_run(self.algo_id, start_date, end_date, len(trades), wr, total_pnl)

        pnl_list = [t["pnl"] for t in trades]

        last = nifty.iloc[-1]
        vix_signal_tomorrow = bool(nifty["VIX_Signal"].iloc[-1]) if len(nifty) > 0 else False
        signal_cards = {
            "Spot":       round(float(last["Close"]), 0),
            "VIX":        round(float(last["VIX"]), 2) if pd.notna(last["VIX"]) else 0,
            "VIX_Thresh": VIX_THRESHOLD,
            "VIX_Signal_Tomorrow": vix_signal_tomorrow,
        }

        return {
            "metrics":      self._metrics(pnl_list, INITIAL_CAPITAL),
            "trades":       trades,
            "monthly":      self._monthly_breakdown(trades),
            "equity_curve": self._equity_curve(trades),
            "signal_cards": signal_cards,
        }

    def get_live_signal(self, spot: float, indicators: Dict[str, float]) -> Dict[str, Any]:
        vix = indicators.get("vix", 0.0)
        signal = vix >= VIX_THRESHOLD

        if signal:
            strike = atm(spot)
            return {
                "signal":       "VIX_BUY_CE",
                "option_type":  "CE",
                "strike":       strike,
                "signal_cards": {
                    "Spot": spot, "VIX": vix,
                    "VIX_Thresh": VIX_THRESHOLD,
                    "VIX_Signal": True,
                },
            }

        return {
            "signal":       "NO_TRADE",
            "option_type":  None,
            "strike":       None,
            "signal_cards": {
                "Spot": spot, "VIX": vix,
                "VIX_Thresh": VIX_THRESHOLD,
                "VIX_Signal": False,
            },
        }
