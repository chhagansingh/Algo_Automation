"""
AlgoTrader — Algo 11: Gamma Scalping Proxy (Long Straddle + Delta Hedge)
Source: gamma-scalping-main (Alpaca + QuantLib)

Original Strategy:
  - Buy ATM straddle (long call + long put at same strike)
  - Continuously delta-hedge underlying to stay market-neutral
  - Profit from gamma (volatility) minus theta (time decay)
  - Requires real-time option chain + tick-level rebalancing

India Adaptation (Daily Bars) — PROXY ONLY:
  - Long ATM straddle with 3-day DTE, BS pricing at fixed IV
  - Delta hedge at entry (short underlying proportional to straddle delta)
  - Hold 1 day (entry at open, exit at next-day close)
  - Non-overlapping entries to avoid position stacking
  - Position size: 5% of capital per straddle

CRITICAL LIMITATIONS:
  1. FIXED IV assumption — real options experience IV expansion/contraction
     which this model cannot capture. On big-move days, real IV would expand,
     increasing straddle value MORE than our model shows. On calm days after
     big moves, IV contracts, decreasing value FASTER than our model.
  2. DAILY BARS — true gamma scalping rebalances on every tick (5s heartbeat).
     Our proxy hedges once at entry and holds. The hedge P&L is negligible
     compared to straddle P&L, confirming this is NOT true gamma scalping.
  3. NO OPTION CHAIN DATA — we use Black-Scholes theoretical prices, not
     actual market bid/ask. Slippage, wide spreads, and liquidity gaps are
     completely ignored.
  4. THETA OVERESTIMATE — with fixed IV and decreasing DTE, the model
     applies full theta decay. In reality, IV often rises on the day of a
     big move, partially offsetting theta.

This is best viewed as a "volatility harvesting" strategy, not true gamma
scalping. Live deployment would require NSE option chain historical data +
real-time Greeks engine + intraday (5m/15m) rebalancing.
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
DTE_ENTRY        = 3
POS_SIZE_PCT     = 0.05
IV               = 0.13
TX_PER_LEG       = 200
STRIKE_STEP      = 50
RISK_FREE_RATE   = 0.07


def bs_price(spot, strike, days, sigma, opt="CE", r=RISK_FREE_RATE):
    t = days / 365.0
    if t <= 0 or sigma <= 0:
        return max(0.0, spot - strike) if opt == "CE" else max(0.0, strike - spot)
    d1 = (math.log(spot / strike) + (r + 0.5 * sigma ** 2) * t) / (sigma * math.sqrt(t))
    d2 = d1 - sigma * math.sqrt(t)
    if opt == "CE":
        return max(0.0, spot * norm.cdf(d1) - strike * math.exp(-r * t) * norm.cdf(d2))
    return max(0.0, strike * math.exp(-r * t) * norm.cdf(-d2) - spot * norm.cdf(-d1))


def bs_delta(spot, strike, days, sigma, opt="CE", r=RISK_FREE_RATE):
    t = days / 365.0
    if t <= 0 or sigma <= 0:
        return 1.0 if opt == "CE" else -1.0
    d1 = (math.log(spot / strike) + (r + 0.5 * sigma ** 2) * t) / (sigma * math.sqrt(t))
    if opt == "CE":
        return norm.cdf(d1)
    return norm.cdf(d1) - 1


def atm(spot):
    return round(spot / STRIKE_STEP) * STRIKE_STEP


class Algo11GammaScalping(AlgoBase):
    algo_id = "algo11"
    name    = "Gamma Scalping Proxy"

    def run_backtest(self, start_date: str, end_date: str, interval: str = "1d") -> Dict[str, Any]:
        data = fetch_nifty_data(start_date, end_date, interval=interval)
        if data.empty:
            return {"metrics": self._metrics([], INITIAL_CAPITAL), "trades": [],
                    "monthly": {}, "equity_curve": []}

        data = data[data.index.dayofweek < 5]
        data = data.reset_index()

        # ── Backtest loop ───────────────────────────────────────────────
        # Non-overlapping: enter at open day i, exit at close day i+1, skip day i+2
        trades: List[Dict] = []
        total_pnl = 0.0
        wins = losses = 0
        balance = INITIAL_CAPITAL

        i = 0
        while i < len(data) - 1:
            entry_row = data.iloc[i]
            exit_row = data.iloc[i + 1]

            date_str = entry_row["Date"].strftime("%Y-%m-%d")
            exit_date_str = exit_row["Date"].strftime("%Y-%m-%d")

            open_px  = float(entry_row["Open"])
            close_px = float(exit_row["Close"])
            high_px  = float(entry_row["High"])
            low_px   = float(entry_row["Low"])
            k = atm(open_px)

            # Entry: buy ATM straddle at open
            ce_entry = bs_price(open_px, k, DTE_ENTRY, IV, "CE")
            pe_entry = bs_price(open_px, k, DTE_ENTRY, IV, "PE")
            straddle_entry = ce_entry + pe_entry

            # Delta hedge at entry
            ce_delta = bs_delta(open_px, k, DTE_ENTRY, IV, "CE")
            pe_delta = bs_delta(open_px, k, DTE_ENTRY, IV, "PE")
            straddle_delta = ce_delta + pe_delta

            qty = max(1, int(balance * POS_SIZE_PCT / (straddle_entry * LOT_SIZE)))
            hedge_shares = -round(straddle_delta * LOT_SIZE * qty)

            # Exit: sell straddle at next-day close
            dte_exit = max(0.1, DTE_ENTRY - 1)
            ce_exit = bs_price(close_px, k, dte_exit, IV, "CE")
            pe_exit = bs_price(close_px, k, dte_exit, IV, "PE")
            straddle_exit = ce_exit + pe_exit

            # P&L
            straddle_pnl = (straddle_exit - straddle_entry) * LOT_SIZE * qty
            hedge_pnl = hedge_shares * (open_px - close_px)
            tx_cost = (2 * TX_PER_LEG + abs(hedge_shares) / max(1, LOT_SIZE * qty) * TX_PER_LEG) * qty
            pnl_val = straddle_pnl + hedge_pnl - tx_cost

            won = pnl_val > 0
            tid = str(uuid.uuid4())[:8]

            log_session_start(self.algo_id, self.name, date_str, mode="backtest")
            log_market_snapshot(self.algo_id, open_px, {
                "open": open_px, "high": high_px, "low": low_px,
                "close": close_px, "strike": k,
                "straddle_entry": round(straddle_entry, 2),
                "straddle_delta": round(straddle_delta, 3),
                "hedge_shares": hedge_shares,
            })

            log_signal_check(
                self.algo_id, "LONG_STRADDLE", eligible=True,
                reason=(f"Long ATM straddle @ strike={k}, delta={straddle_delta:.3f}, hedge={hedge_shares} shares"),
                context={"strike": k, "straddle_entry": round(straddle_entry, 2),
                         "ce_delta": round(ce_delta, 3), "pe_delta": round(pe_delta, 3),
                         "hedge_shares": hedge_shares, "qty": qty},
                timestamp="09:20:00"
            )

            log_trade_entry(
                self.algo_id, tid, "LONG_STRADDLE", open_px, k, "BOTH",
                round(straddle_entry, 2), f"{date_str} 09:20:00", LOT_SIZE * qty,
                context={"ce_entry": round(ce_entry, 2), "pe_entry": round(pe_entry, 2),
                         "straddle_delta": round(straddle_delta, 3), "hedge_shares": hedge_shares}
            )

            exit_reason = "EOD_CLOSE"
            log_trade_exit(
                self.algo_id, tid, f"{exit_date_str} 15:25:00", round(straddle_exit, 2),
                exit_reason, round(pnl_val, 2),
                round(pnl_val / (straddle_entry * LOT_SIZE * qty) * 100, 2) if straddle_entry > 0 else 0,
                context={"close": close_px, "straddle_exit": round(straddle_exit, 2),
                         "straddle_pnl": round(straddle_pnl, 2), "hedge_pnl": round(hedge_pnl, 2),
                         "tx_cost": tx_cost}
            )

            trades.append({
                "trade_id": tid, "algo_id": self.algo_id, "date": date_str,
                "symbol": "NIFTY", "strike": k,
                "option_type": "BOTH", "signal_name": "LONG_STRADDLE",
                "entry_time": f"{date_str} 09:20:00", "entry_price": round(straddle_entry, 2),
                "exit_time": f"{exit_date_str} 15:25:00", "exit_price": round(straddle_exit, 2),
                "exit_reason": exit_reason, "pnl": round(pnl_val, 2),
                "lot_size": LOT_SIZE, "status": "closed", "qty": LOT_SIZE * qty,
                "hedge_shares": hedge_shares,
                "straddle_pnl": round(straddle_pnl, 2),
                "hedge_pnl": round(hedge_pnl, 2),
                "tx_cost": tx_cost,
            })

            total_pnl += pnl_val
            balance += pnl_val
            if won:
                wins += 1
            else:
                losses += 1

            log_session_end(self.algo_id, 1, pnl_val, status="OK")

            # Skip next day to avoid overlapping
            i += 2

        if trades:
            wr = wins / len(trades) * 100
            log_backtest_run(self.algo_id, start_date, end_date, len(trades), wr, total_pnl)

        pnl_list = [t["pnl"] for t in trades]

        last = data.iloc[-1]
        signal_cards = {
            "Spot":       round(float(last["Close"]), 0),
            "Strike":     atm(float(last["Close"])),
            "DTE":        DTE_ENTRY,
            "IV":         IV,
            "Pos_Size_%": POS_SIZE_PCT * 100,
        }

        return {
            "metrics":      self._metrics(pnl_list, INITIAL_CAPITAL),
            "trades":       trades,
            "monthly":      self._monthly_breakdown(trades),
            "equity_curve": self._equity_curve(trades),
            "signal_cards": signal_cards,
        }

    def get_live_signal(self, spot: float, indicators: Dict[str, float]) -> Dict[str, Any]:
        k = atm(spot)
        ce_price = bs_price(spot, k, DTE_ENTRY, IV, "CE")
        pe_price = bs_price(spot, k, DTE_ENTRY, IV, "PE")
        straddle_price = ce_price + pe_price
        straddle_delta = bs_delta(spot, k, DTE_ENTRY, IV, "CE") + bs_delta(spot, k, DTE_ENTRY, IV, "PE")

        return {
            "signal":       "LONG_STRADDLE",
            "option_type":  "BOTH",
            "strike":       k,
            "signal_cards": {
                "Spot": spot, "Strike": k, "Straddle_Price": round(straddle_price, 2),
                "Straddle_Delta": round(straddle_delta, 3), "DTE": DTE_ENTRY, "IV": IV,
            },
        }
