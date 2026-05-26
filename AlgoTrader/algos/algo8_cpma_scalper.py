"""
AlgoTrader — Algo 8: CPMA Scalper
Custom strategy: EMA(20) vs CPMA(21) crossover on NIFTY underlying

Rules:
  - EMA(20) > CPMA(21) → BUY (LONG)
  - EMA(20) < CPMA(21) → SELL (SHORT)
  - SL = 0.5% from entry
  - Target = 1.0% from entry
  - Max hold = 5 bars
  - Quantity = 50 (2 lots NIFTY)
  - Lagged by 1 bar to avoid look-ahead bias
  - Entry at Open, check SL/Target against bar High/Low

CPMA Logic (from TradingView Pine Script):
  1. 8 price-type averages: close EMA, HL2 SMA, open EMA, high SMA, low EMA,
     OHLC4 SMA, HLC3 EMA, HLCC4 SMA
  2. Raw_CPMA = average of the 8
  3. CPMA[i] = CPMA[i-1] + (Close[i] - CPMA[i-1]) / (length * (Close[i]/CPMA[i-1])^4)
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

# ── Constants ────────────────────────────────────────────────────────────────
LOT_SIZE         = 25
INITIAL_CAPITAL  = 200_000
EMA_PERIOD       = 20
CPMA_PERIOD      = 21
BASE_QUANTITY    = 25          # 1 lot NIFTY (halved from 50)
SL_PCT           = 0.005       # 0.5% stop loss
TARGET_PCT       = 0.01        # 1.0% target
MAX_HOLD_BARS    = 5
DAILY_LOSS_LIMIT = 5_000       # Max ₹5K loss per day → stop trading
MAX_CONSEC_LOSS  = 3           # After 3 consecutive losses, halve size
DD_CIRCUIT_PCT   = 0.15        # 15% drawdown → halve size
DD_HALT_PCT      = 0.25        # 25% drawdown → stop trading


def calc_cpma(data: pd.DataFrame, length: int = 21) -> pd.Series:
    """Conceptive Price Moving Average (CPMA) from TradingView Pine Script."""
    close = data["Close"]
    open_px = data["Open"]
    high = data["High"]
    low = data["Low"]

    hl2 = (high + low) / 2
    hlc3 = (high + low + close) / 3
    hlcc4 = (high + low + 2 * close) / 4
    ohlc4 = (open_px + high + low + close) / 4

    price_avg = close.ewm(span=length, adjust=False).mean()
    hl2_avg = hl2.rolling(window=length, min_periods=length).mean()
    open_avg = open_px.ewm(span=length, adjust=False).mean()
    high_avg = high.rolling(window=length, min_periods=length).mean()
    low_avg = low.ewm(span=length, adjust=False).mean()
    ohlc4_avg = ohlc4.rolling(window=length, min_periods=length).mean()
    hlc3_avg = hlc3.ewm(span=length, adjust=False).mean()
    hlcc4_avg = hlcc4.rolling(window=length, min_periods=length).mean()

    raw_cpma = (price_avg + hl2_avg + open_avg + high_avg +
                low_avg + ohlc4_avg + hlc3_avg + hlcc4_avg) / 8

    cpma = pd.Series(index=data.index, dtype=float)
    valid_start = raw_cpma.first_valid_index()
    if valid_start is None:
        return cpma

    start_idx = data.index.get_loc(valid_start)
    cpma.iloc[start_idx] = raw_cpma.iloc[start_idx]

    for i in range(start_idx + 1, len(data)):
        prev = cpma.iloc[i - 1]
        curr_close = close.iloc[i]
        if prev == 0 or pd.isna(prev):
            cpma.iloc[i] = raw_cpma.iloc[i]
            continue
        ratio = curr_close / prev
        alpha = 1.0 / (length * (ratio ** 4))
        cpma.iloc[i] = prev + (curr_close - prev) * alpha

    return cpma


class Algo8CPMAScalper(AlgoBase):
    algo_id = "algo8"
    name    = "CPMA Scalper"

    def run_backtest(self, start_date: str, end_date: str, interval: str = "1d") -> Dict[str, Any]:
        data = fetch_nifty_data(start_date, end_date, interval=interval)
        if data.empty:
            return {"metrics": self._metrics([], INITIAL_CAPITAL), "trades": [],
                    "monthly": {}, "equity_curve": []}

        if interval in ("1d", "1D"):
            data = data[data.index.dayofweek < 5]

        # ── Indicators ──────────────────────────────────────────────────
        data["EMA"] = data["Close"].ewm(span=EMA_PERIOD, adjust=False).mean()
        data["CPMA"] = calc_cpma(data, CPMA_PERIOD)

        # Lagged signal
        data["EMA_Known"] = data["EMA"].shift(1)
        data["CPMA_Known"] = data["CPMA"].shift(1)

        # ── Backtest loop ─────────────────────────────────────────────
        trades: List[Dict] = []
        total_pnl = 0.0
        wins = losses = 0
        balance = INITIAL_CAPITAL
        peak_balance = INITIAL_CAPITAL
        in_position = False
        position_type = None
        entry_px = 0.0
        entry_date = ""
        hold_bars = 0
        consec_losses = 0
        daily_pnl = 0.0
        prev_day = ""
        qty = BASE_QUANTITY
        skip_trade = False

        for idx, row in data.iterrows():
            date_str = idx.strftime("%Y-%m-%d %H:%M" if " " in str(idx) else "%Y-%m-%d")
            day_only = date_str.split()[0]
            ema_known = row["EMA_Known"]
            cpma_known = row["CPMA_Known"]

            if pd.isna(ema_known) or pd.isna(cpma_known):
                continue

            ema_known = float(ema_known)
            cpma_known = float(cpma_known)
            open_px = float(row["Open"])
            high_px = float(row["High"])
            low_px = float(row["Low"])
            close_px = float(row["Close"])
            strike = round(open_px / 50) * 50

            # ── Daily reset & risk mgmt ─────────────────────────────
            if day_only != prev_day:
                daily_pnl = 0.0
                prev_day = day_only
                skip_trade = False

            # Peak balance tracking
            if balance > peak_balance:
                peak_balance = balance

            drawdown_pct = (peak_balance - balance) / peak_balance

            # Dynamic qty based on drawdown
            if drawdown_pct >= DD_HALT_PCT:
                qty = 0  # halt
            elif drawdown_pct >= DD_CIRCUIT_PCT:
                qty = max(1, BASE_QUANTITY // 2)
            else:
                qty = BASE_QUANTITY

            # Consecutive loss cooldown
            if consec_losses >= MAX_CONSEC_LOSS:
                qty = max(1, qty // 2)

            # Daily loss limit
            if daily_pnl <= -DAILY_LOSS_LIMIT:
                skip_trade = True

            # Target position
            if ema_known > cpma_known:
                target = "LONG"
            elif ema_known < cpma_known:
                target = "SHORT"
            else:
                target = "FLAT"

            log_session_start(self.algo_id, self.name, date_str, mode="backtest")
            log_market_snapshot(self.algo_id, open_px, {
                "open": open_px, "high": high_px, "low": low_px,
                "close": close_px, "ema": round(ema_known, 2), "cpma": round(cpma_known, 2),
            })

            exit_now = False
            exit_reason = ""
            exit_px = 0.0

            # ── Check exit for existing position ────────────────────
            if in_position:
                hold_bars += 1
                sl_px = entry_px * (1 - SL_PCT) if position_type == "LONG" else entry_px * (1 + SL_PCT)
                tgt_px = entry_px * (1 + TARGET_PCT) if position_type == "LONG" else entry_px * (1 - TARGET_PCT)

                if position_type == "LONG":
                    if low_px <= sl_px:
                        exit_now = True; exit_reason = "SL_EXIT"; exit_px = sl_px
                    elif high_px >= tgt_px:
                        exit_now = True; exit_reason = "TARGET_EXIT"; exit_px = tgt_px
                    elif target == "SHORT":
                        exit_now = True; exit_reason = "SIGNAL_FLIP"; exit_px = open_px
                else:  # SHORT
                    if high_px >= sl_px:
                        exit_now = True; exit_reason = "SL_EXIT"; exit_px = sl_px
                    elif low_px <= tgt_px:
                        exit_now = True; exit_reason = "TARGET_EXIT"; exit_px = tgt_px
                    elif target == "LONG":
                        exit_now = True; exit_reason = "SIGNAL_FLIP"; exit_px = open_px

                if hold_bars >= MAX_HOLD_BARS and not exit_now:
                    exit_now = True; exit_reason = "MAX_HOLD"; exit_px = close_px

                if exit_now:
                    if position_type == "LONG":
                        pnl_val = (exit_px - entry_px) * qty
                    else:
                        pnl_val = (entry_px - exit_px) * qty

                    won = pnl_val > 0
                    tid = str(uuid.uuid4())[:8]

                    log_trade_exit(
                        self.algo_id, tid, date_str, exit_px,
                        exit_reason, pnl_val,
                        round(pnl_val / (entry_px * qty) * 100, 2) if entry_px else 0,
                        context={"ema": round(ema_known, 2), "cpma": round(cpma_known, 2),
                                 "hold_bars": hold_bars, "qty": qty}
                    )

                    trades.append({
                        "trade_id": tid, "algo_id": self.algo_id, "date": entry_date,
                        "symbol": "NIFTY", "strike": round(entry_px / 50) * 50,
                        "option_type": "CE" if position_type == "LONG" else "PE",
                        "signal_name": f"CPMA_{position_type}",
                        "entry_time": entry_date, "entry_price": round(entry_px, 2),
                        "exit_time": date_str, "exit_price": round(exit_px, 2),
                        "exit_reason": exit_reason, "pnl": round(pnl_val, 2),
                        "lot_size": LOT_SIZE, "status": "closed", "qty": qty,
                    })

                    total_pnl += pnl_val
                    balance += pnl_val
                    daily_pnl += pnl_val
                    if won:
                        wins += 1
                        consec_losses = 0
                    else:
                        losses += 1
                        consec_losses += 1

                    in_position = False
                    position_type = None
                    hold_bars = 0
                    log_session_end(self.algo_id, 1, pnl_val, status="OK")

            # ── Enter new position ────────────────────────────────────
            if not in_position and target != "FLAT" and not skip_trade and qty > 0:
                entry_px = open_px
                in_position = True
                position_type = target
                entry_date = date_str
                hold_bars = 0

                tid = str(uuid.uuid4())[:8]
                sig_name = "CPMA_BUY" if target == "LONG" else "CPMA_SELL"
                opt_type = "CE" if target == "LONG" else "PE"
                reason = (
                    f"EMA({round(ema_known,1)}) > CPMA({round(cpma_known,1)}) → bullish"
                    if target == "LONG" else
                    f"EMA({round(ema_known,1)}) < CPMA({round(cpma_known,1)}) → bearish"
                )

                log_signal_check(
                    self.algo_id, sig_name, eligible=True,
                    reason=reason,
                    context={"ema": round(ema_known, 2), "cpma": round(cpma_known, 2),
                             "entry": entry_px, "qty": qty, "dd_pct": round(drawdown_pct*100,1)},
                    timestamp="09:20:00"
                )
                log_trade_entry(
                    self.algo_id, tid, sig_name, open_px, strike, opt_type,
                    entry_px, date_str, qty,
                    context={"ema": round(ema_known, 2), "cpma": round(cpma_known, 2),
                             "dd_pct": round(drawdown_pct*100,1), "consec_loss": consec_losses}
                )

            if not in_position and target == "FLAT":
                log_signal_check(
                    self.algo_id, "CPMA_NO_TRADE", eligible=False,
                    reason=(f"EMA({round(ema_known,1)}) ≈ CPMA({round(cpma_known,1)}) → no signal"),
                    context={"ema": round(ema_known, 2), "cpma": round(cpma_known, 2)},
                    timestamp="09:20:00"
                )
                log_session_end(self.algo_id, 0, 0.0, status="NO_TRADE")
            elif in_position and not exit_now:
                log_signal_check(
                    self.algo_id, "CPMA_HOLD", eligible=True,
                    reason=(f"Holding {position_type} — SL/Target not hit"),
                    context={"ema": round(ema_known, 2), "cpma": round(cpma_known, 2),
                             "hold_bars": hold_bars},
                    timestamp="09:20:00"
                )
                log_session_end(self.algo_id, 0, 0.0, status="HOLD")

        # Close any open position at end
        if in_position and len(data) > 0:
            last = data.iloc[-1]
            close_px = float(last["Close"])
            date_str = last.name.strftime("%Y-%m-%d %H:%M" if " " in str(last.name) else "%Y-%m-%d")

            if position_type == "LONG":
                pnl_val = (close_px - entry_px) * qty
            else:
                pnl_val = (entry_px - close_px) * qty

            won = pnl_val > 0
            tid = str(uuid.uuid4())[:8]

            log_trade_exit(
                self.algo_id, tid, date_str, close_px,
                "EOD_CLOSE", pnl_val,
                round(pnl_val / (entry_px * qty) * 100, 2) if entry_px else 0,
                context={"close": close_px}
            )

            trades.append({
                "trade_id": tid, "algo_id": self.algo_id, "date": entry_date,
                "symbol": "NIFTY", "strike": round(entry_px / 50) * 50,
                "option_type": "CE" if position_type == "LONG" else "PE",
                "signal_name": f"CPMA_{position_type}",
                "entry_time": entry_date, "entry_price": round(entry_px, 2),
                "exit_time": date_str, "exit_price": round(close_px, 2),
                "exit_reason": "EOD_CLOSE", "pnl": round(pnl_val, 2),
                "lot_size": LOT_SIZE, "status": "closed", "qty": qty,
            })

            total_pnl += pnl_val
            daily_pnl += pnl_val
            if won:
                wins += 1
                consec_losses = 0
            else:
                losses += 1
                consec_losses += 1

        if trades:
            wr = wins / len(trades) * 100
            log_backtest_run(self.algo_id, start_date, end_date, len(trades), wr, total_pnl)

        pnl_list = [t["pnl"] for t in trades]

        last = data.iloc[-1]
        ema_last = float(last["EMA"]) if pd.notna(last["EMA"]) else 0
        cpma_last = float(last["CPMA"]) if pd.notna(last["CPMA"]) else 0
        signal_cards = {
            "Spot": round(float(last["Close"]), 0),
            "EMA": round(ema_last, 1),
            "CPMA": round(cpma_last, 1),
            "EMA_Period": EMA_PERIOD,
            "CPMA_Period": CPMA_PERIOD,
        }

        return {
            "metrics": self._metrics(pnl_list, INITIAL_CAPITAL),
            "trades": trades,
            "monthly": self._monthly_breakdown(trades),
            "equity_curve": self._equity_curve(trades),
            "signal_cards": signal_cards,
        }

    def get_live_signal(self, spot: float, indicators: Dict[str, float]) -> Dict[str, Any]:
        ema = indicators.get("ema", 0.0)
        cpma = indicators.get("cpma", 0.0)

        if ema > cpma:
            strike = round(spot / 50) * 50
            return {
                "signal": "CPMA_BUY", "option_type": "CE", "strike": strike,
                "signal_cards": {
                    "Spot": spot, "EMA": round(ema, 1), "CPMA": round(cpma, 1),
                    "EMA_Period": EMA_PERIOD, "CPMA_Period": CPMA_PERIOD,
                },
            }
        elif ema < cpma:
            strike = round(spot / 50) * 50
            return {
                "signal": "CPMA_SELL", "option_type": "PE", "strike": strike,
                "signal_cards": {
                    "Spot": spot, "EMA": round(ema, 1), "CPMA": round(cpma, 1),
                    "EMA_Period": EMA_PERIOD, "CPMA_Period": CPMA_PERIOD,
                },
            }

        return {
            "signal": "NO_TRADE", "option_type": None, "strike": None,
            "signal_cards": {
                "Spot": spot, "EMA": round(ema, 1), "CPMA": round(cpma, 1),
                "EMA_Period": EMA_PERIOD, "CPMA_Period": CPMA_PERIOD,
            },
        }
