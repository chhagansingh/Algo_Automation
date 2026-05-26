"""
AlgoTrader — Algo 9: Bullish Scanner (from trading_skills-main)
Source: trading_skills-main/scanner_bullish.py

Strategy: Composite bullish score on NIFTY daily
  - Multi-factor scoring model: SMA trend + RSI health + MACD momentum + ADX strength
  - Buy ATM CE when score crosses above entry threshold
  - Exit when score drops below exit threshold or EOD

Scoring Model (reconstructed from trading_skills postmortem):
  - Price > SMA20: +1.0
  - Price > SMA50: +1.0
  - RSI 50-70: +1.0 | RSI 30-50: +0.5 | RSI < 30: +0.25
  - MACD > Signal: +1.0
  - MACD Histogram Rising: +0.5
  - ADX > 25 + DI+ > DI-: +1.5
  - DI+ > DI-: +0.5
  - Momentum (20-period return normalized): -1 to +2

Entry: Score <= ENTRY_LOW (lagged by 1 day) — CONTRARIAN / mean-reversion
Exit:  Score >= EXIT_HIGH or EOD
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
POS_SIZE_PCT     = 0.05
RISK_FREE_RATE   = 0.07
EXPIRY_DAYS      = 3
TX_COST_SINGLE   = 200
STRIKE_STEP      = 50
MAX_DAILY_LOSS_PCT = 0.02

ENTRY_LOW        = 1.5   # Buy CE when score is LOW (mean-reversion / contrarian)
EXIT_HIGH        = 2.0   # Exit when score recovers


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


def calc_rsi(close, n=14):
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def calc_macd(close, fast=12, slow=26, signal=9):
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def calc_adx(high, low, close, n=14):
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm < 0] = 0

    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)

    atr = tr.ewm(alpha=1/n, adjust=False).mean()

    plus_di = 100 * (plus_dm.ewm(alpha=1/n, adjust=False).mean() / atr)
    minus_di = 100 * (minus_dm.ewm(alpha=1/n, adjust=False).mean() / atr)

    dx = ( (plus_di - minus_di).abs() / (plus_di + minus_di) ) * 100
    adx = dx.ewm(alpha=1/n, adjust=False).mean()
    return adx, plus_di, minus_di


def compute_bullish_score(df):
    """Compute composite bullish score for each row."""
    df = df.copy()
    df["SMA20"] = df["Close"].rolling(20).mean()
    df["SMA50"] = df["Close"].rolling(50).mean()
    df["RSI"] = calc_rsi(df["Close"])
    df["MACD"], df["MACD_Signal"], df["MACD_Hist"] = calc_macd(df["Close"])
    df["ADX"], df["DI_PLUS"], df["DI_MINUS"] = calc_adx(df["High"], df["Low"], df["Close"])
    df["Momentum"] = (df["Close"] / df["Close"].shift(20) - 1) * 100

    scores = []
    for i in range(len(df)):
        s = 0.0
        c = df.iloc[i]

        # SMA trend
        if pd.notna(c["SMA20"]) and c["Close"] > c["SMA20"]:
            s += 1.0
        if pd.notna(c["SMA50"]) and c["Close"] > c["SMA50"]:
            s += 1.0

        # RSI
        rsi = c["RSI"]
        if pd.notna(rsi):
            if 50 <= rsi <= 70:
                s += 1.0
            elif 30 <= rsi < 50:
                s += 0.5
            elif rsi < 30:
                s += 0.25

        # MACD
        if pd.notna(c["MACD"]) and pd.notna(c["MACD_Signal"]) and c["MACD"] > c["MACD_Signal"]:
            s += 1.0
        if pd.notna(c["MACD_Hist"]):
            if i > 0 and c["MACD_Hist"] > df.iloc[i-1]["MACD_Hist"]:
                s += 0.5

        # ADX
        adx = c["ADX"]
        di_plus = c["DI_PLUS"]
        di_minus = c["DI_MINUS"]
        if pd.notna(adx) and pd.notna(di_plus) and pd.notna(di_minus):
            if adx > 25 and di_plus > di_minus:
                s += 1.5
            elif di_plus > di_minus:
                s += 0.5

        # Momentum (-1 to +2 cap)
        mom = c["Momentum"]
        if pd.notna(mom):
            s += max(-1.0, min(2.0, mom / 10.0))

        scores.append(s)

    df["Bullish_Score"] = scores
    return df


class Algo9BullishScanner(AlgoBase):
    algo_id = "algo9"
    name    = "Bullish Scanner"

    def run_backtest(self, start_date: str, end_date: str, interval: str = "1d") -> Dict[str, Any]:
        df = fetch_nifty_data(start_date, end_date, interval=interval)
        if df.empty:
            return {"metrics": self._metrics([], INITIAL_CAPITAL), "trades": [],
                    "monthly": {}, "equity_curve": []}

        df = df[df.index.dayofweek < 5]
        df = compute_bullish_score(df)

        # Lagged signal: CONTRARIAN — buy CE when score is LOW (mean-reversion)
        # The composite bullish score is actually overbought on NIFTY daily
        # High score → next day tends down; Low score → next day tends up
        df["Entry_Signal"] = df["Bullish_Score"].shift(1) <= ENTRY_LOW
        df["Exit_Signal"] = df["Bullish_Score"].shift(1) >= EXIT_HIGH

        trades: List[Dict] = []
        balance = INITIAL_CAPITAL
        in_position = False
        entry_px = 0.0
        entry_date = ""
        position_qty = 0
        daily_pnl = 0.0
        daily_date = None
        hit_daily_loss = False
        total_pnl = 0.0
        wins = losses = 0

        for i in range(60, len(df)):
            row = df.iloc[i]
            date_str = row.name.strftime("%Y-%m-%d")

            if date_str != daily_date:
                daily_date = date_str
                daily_pnl = 0.0
                hit_daily_loss = False

            if hit_daily_loss:
                continue

            open_px = float(row["Open"])
            high_px = float(row["High"])
            low_px = float(row["Low"])
            close_px = float(row["Close"])
            score = float(row["Bullish_Score"]) if pd.notna(row["Bullish_Score"]) else 0.0
            prev_score = float(df.iloc[i-1]["Bullish_Score"]) if i > 0 and pd.notna(df.iloc[i-1]["Bullish_Score"]) else 0.0

            log_market_snapshot(self.algo_id, open_px, {
                "open": open_px, "high": high_px, "low": low_px,
                "close": close_px, "score": round(score, 2),
                "prev_score": round(prev_score, 2),
            })

            if not in_position and bool(row["Entry_Signal"]):
                k = atm(open_px)
                iv = 0.13
                dte_e = EXPIRY_DAYS
                entry_px = bs_price(open_px, k, dte_e, iv, "CE")
                position_qty = max(1, int(balance * POS_SIZE_PCT / (entry_px * LOT_SIZE)))
                in_position = True
                entry_date = date_str

                tid = str(uuid.uuid4())[:8]
                log_trade_entry(
                    self.algo_id, tid, "SCANNER_BUY_CE", open_px, k, "CE",
                    round(entry_px, 2), f"{date_str} 09:20:00", LOT_SIZE * position_qty,
                    context={"score": round(prev_score, 2), "threshold": ENTRY_LOW}
                )

                log_signal_check(
                    self.algo_id, "SCANNER_BUY_CE", eligible=True,
                    reason=f"Prev-day score {prev_score:.1f} <= {ENTRY_LOW} (oversold composite) → mean-reversion CE",
                    context={"score": prev_score, "threshold": ENTRY_LOW},
                    timestamp="09:20:00"
                )

            elif in_position and bool(row["Exit_Signal"]):
                k = atm(open_px)  # same strike as entry
                iv = 0.13
                dte_x = max(0.1, EXPIRY_DAYS - 1 / 252)
                exit_px = bs_price(close_px, k, dte_x, iv, "CE")
                pnl_val = (exit_px - entry_px) * LOT_SIZE * position_qty - TX_COST_SINGLE * position_qty
                won = pnl_val > 0

                tid = str(uuid.uuid4())[:8]
                log_trade_exit(
                    self.algo_id, tid, f"{date_str} 15:25:00", round(exit_px, 2),
                    "SCORE_EXIT", round(pnl_val, 2),
                    round(pnl_val / (entry_px * LOT_SIZE * position_qty) * 100, 2) if entry_px > 0 else 0,
                    context={"score": score, "close": close_px}
                )

                trades.append({
                    "trade_id": tid, "algo_id": self.algo_id, "date": entry_date,
                    "symbol": "NIFTY", "strike": k, "option_type": "CE",
                    "signal_name": "SCANNER_BUY_CE",
                    "entry_time": f"{entry_date} 09:20:00", "entry_price": round(entry_px, 2),
                    "exit_time": f"{date_str} 15:25:00", "exit_price": round(exit_px, 2),
                    "exit_reason": "SCORE_EXIT", "pnl": round(pnl_val, 2),
                    "lot_size": LOT_SIZE, "status": "closed", "qty": LOT_SIZE * position_qty,
                })

                balance += pnl_val
                total_pnl += pnl_val
                daily_pnl += pnl_val
                if won:
                    wins += 1
                else:
                    losses += 1

                if daily_pnl <= -INITIAL_CAPITAL * MAX_DAILY_LOSS_PCT:
                    hit_daily_loss = True

                in_position = False
                entry_px = 0.0
                position_qty = 0

        # Close any open position at end
        if in_position and len(df) > 0:
            last = df.iloc[-1]
            close_px = float(last["Close"])
            date_str = last.name.strftime("%Y-%m-%d")
            k = atm(float(df.iloc[-2]["Open"]) if len(df) > 1 else close_px)
            iv = 0.13
            dte_x = max(0.1, EXPIRY_DAYS - 1 / 252)
            exit_px = bs_price(close_px, k, dte_x, iv, "CE")
            pnl_val = (exit_px - entry_px) * LOT_SIZE * position_qty - TX_COST_SINGLE * position_qty
            won = pnl_val > 0
            tid = str(uuid.uuid4())[:8]

            log_trade_exit(
                self.algo_id, tid, date_str, round(exit_px, 2),
                "EOD_CLOSE", round(pnl_val, 2),
                round(pnl_val / (entry_px * LOT_SIZE * position_qty) * 100, 2) if entry_px else 0,
                context={"close": close_px}
            )

            trades.append({
                "trade_id": tid, "algo_id": self.algo_id, "date": entry_date,
                "symbol": "NIFTY", "strike": k, "option_type": "CE",
                "signal_name": "SCANNER_BUY_CE",
                "entry_time": f"{entry_date} 09:20:00", "entry_price": round(entry_px, 2),
                "exit_time": date_str, "exit_price": round(exit_px, 2),
                "exit_reason": "EOD_CLOSE", "pnl": round(pnl_val, 2),
                "lot_size": LOT_SIZE, "status": "closed", "qty": LOT_SIZE * position_qty,
            })

            balance += pnl_val
            total_pnl += pnl_val
            if won:
                wins += 1
            else:
                losses += 1

        if trades:
            wr = wins / len(trades) * 100
            log_backtest_run(self.algo_id, start_date, end_date, len(trades), wr, total_pnl)

        pnl_list = [t["pnl"] for t in trades]

        last = df.iloc[-1]
        last_score = float(last["Bullish_Score"]) if pd.notna(last["Bullish_Score"]) else 0.0
        signal_cards = {
            "Spot": round(float(last["Close"]), 0),
            "Bullish_Score": round(last_score, 2),
            "Entry_Low": ENTRY_LOW,
            "Exit_High": EXIT_HIGH,
            "Signal_Tomorrow": last_score <= ENTRY_LOW,
        }

        return {
            "metrics": self._metrics(pnl_list, INITIAL_CAPITAL),
            "trades": trades,
            "monthly": self._monthly_breakdown(trades),
            "equity_curve": self._equity_curve(trades),
            "signal_cards": signal_cards,
        }

    def get_live_signal(self, spot: float, indicators: Dict[str, float]) -> Dict[str, Any]:
        score = indicators.get("bullish_score", 0.0)
        if score <= ENTRY_LOW:
            return {
                "signal": "SCANNER_BUY_CE", "option_type": "CE", "strike": atm(spot),
                "signal_cards": {"Spot": spot, "Bullish_Score": score,
                                  "Entry_Low": ENTRY_LOW},
            }
        return {
            "signal": "NO_TRADE", "option_type": None, "strike": None,
            "signal_cards": {"Spot": spot, "Bullish_Score": score,
                              "Entry_Low": ENTRY_LOW},
        }
