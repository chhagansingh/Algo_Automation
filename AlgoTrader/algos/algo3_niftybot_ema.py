"""
AlgoTrader — Algo 3: EMA Crossover (Fixed)
Source: Nifty-Bot-main/backtest_may2025.py

Strategy: EMA 5/20 Crossover + RSI Filter — Directional Buy CE/PE
  - EMA5 > EMA20 and RSI > 55 → Buy CE (bullish)
  - EMA5 < EMA20 and RSI < 45 → Buy PE (bearish)

FIXES vs original:
  A. All signals lagged by 1 bar (prev Close/EMA/RSI decide current entry)
  B. Entry at current-bar Open (no look-ahead)
  C. BS option pricing with realistic position sizing
  D. Iron Condor & Short Straddle REMOVED — not viable on daily bars
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
INITIAL_CAPITAL  = 200_000
NIFTY_LOT_SIZE   = 25
STRIKE_STEP      = 50
RISK_FREE_RATE   = 0.07
BASE_IV          = 0.13
EXPIRY_DAYS      = 3
TX_COST_SINGLE   = 200
POS_SIZE_PCT     = 0.05
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


def calc_ema(series, n):
    return series.ewm(span=n, adjust=False).mean()


def calc_rsi(close, n=14):
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def calc_adx(df, n=14):
    plus_dm = df["High"].diff()
    minus_dm = -df["Low"].diff()
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm < 0] = 0
    tr = pd.concat([
        df["High"] - df["Low"],
        (df["High"] - df["Close"].shift()).abs(),
        (df["Low"] - df["Close"].shift()).abs()
    ], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/n, adjust=False).mean()
    plus_di = 100 * (plus_dm.ewm(alpha=1/n, adjust=False).mean() / atr)
    minus_di = 100 * (minus_dm.ewm(alpha=1/n, adjust=False).mean() / atr)
    dx = ((plus_di - minus_di).abs() / (plus_di + minus_di)) * 100
    adx = dx.ewm(alpha=1/n, adjust=False).mean()
    return adx, plus_di, minus_di


def calc_macd(close, fast=12, slow=26, signal=9):
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def compute_scanner_score(df):
    """Compute composite bullish score (from trading_skills scanner)."""
    df = df.copy()
    df["SMA20"] = df["Close"].rolling(20).mean()
    df["SMA50"] = df["Close"].rolling(50).mean()
    df["RSI_S"] = calc_rsi(df["Close"])
    df["MACD_L"], df["MACD_S"], df["MACD_H"] = calc_macd(df["Close"])
    df["ADX"], df["DI_PLUS"], df["DI_MINUS"] = calc_adx(df)
    df["Momentum"] = (df["Close"] / df["Close"].shift(20) - 1) * 100

    scores = []
    for i in range(len(df)):
        s = 0.0
        c = df.iloc[i]
        if pd.notna(c["SMA20"]) and c["Close"] > c["SMA20"]: s += 1.0
        if pd.notna(c["SMA50"]) and c["Close"] > c["SMA50"]: s += 1.0
        rsi = c["RSI_S"]
        if pd.notna(rsi):
            if 50 <= rsi <= 70: s += 1.0
            elif 30 <= rsi < 50: s += 0.5
            elif rsi < 30: s += 0.25
        if pd.notna(c["MACD_L"]) and pd.notna(c["MACD_S"]) and c["MACD_L"] > c["MACD_S"]: s += 1.0
        if pd.notna(c["MACD_H"]) and i > 0 and c["MACD_H"] > df.iloc[i-1]["MACD_H"]: s += 0.5
        adx = c["ADX"]
        if pd.notna(adx) and adx > 25 and c["DI_PLUS"] > c["DI_MINUS"]: s += 1.5
        elif pd.notna(c["DI_PLUS"]) and c["DI_PLUS"] > c["DI_MINUS"]: s += 0.5
        mom = c["Momentum"]
        if pd.notna(mom): s += max(-1.0, min(2.0, mom / 10.0))
        scores.append(s)
    df["Scanner_Score"] = scores
    return df


class Algo3NiftyBotEMA(AlgoBase):
    algo_id = "algo3"
    name    = "EMA Crossover (Fixed)"

    def run_backtest(self, start_date: str, end_date: str, interval: str = "1d") -> Dict[str, Any]:
        df = fetch_nifty_data(start_date, end_date, interval=interval)
        if df.empty:
            return {"metrics": self._metrics([], INITIAL_CAPITAL), "trades": [],
                    "monthly": {}, "equity_curve": []}

        if interval in ("1d", "1D"):
            df = df[df.index.dayofweek < 5]

        # ── Indicators ──────────────────────────────────────────────────
        df["EMA5"]  = calc_ema(df["Close"], 5)
        df["EMA20"] = calc_ema(df["Close"], 20)
        df["RSI"]   = calc_rsi(df["Close"])
        df = compute_scanner_score(df)

        # ── Backtest loop ───────────────────────────────────────────────
        trades: List[Dict] = []
        balance = INITIAL_CAPITAL
        daily_pnl = 0.0
        daily_date = None
        hit_daily_loss = False

        for i in range(60, len(df)):
            prev = df.iloc[i - 1]
            curr = df.iloc[i]
            date_str = curr.name.strftime("%Y-%m-%d")

            # Daily loss limit reset
            if date_str != daily_date:
                daily_date = date_str
                daily_pnl = 0.0
                hit_daily_loss = False

            prev_rsi = float(prev["RSI"]) if pd.notna(prev["RSI"]) else None
            prev_ema5 = float(prev["EMA5"]) if pd.notna(prev["EMA5"]) else None
            prev_ema20 = float(prev["EMA20"]) if pd.notna(prev["EMA20"]) else None
            prev_score = float(prev["Scanner_Score"]) if pd.notna(prev["Scanner_Score"]) else 999

            if prev_rsi is None or prev_ema5 is None:
                continue

            # Skip if daily loss already hit
            if hit_daily_loss:
                continue

            # Scanner filter: skip when composite score is too high (overbullish)
            # The scanner score is contrarian on NIFTY daily
            if prev_score >= 3.5:
                continue

            spot_entry = float(curr["Open"])
            spot_exit  = float(curr["Close"])
            k = atm(spot_entry)
            iv = BASE_IV
            dte_e = EXPIRY_DAYS
            dte_x = max(0.1, dte_e - 1 / 252)
            qty = max(1, int(balance * POS_SIZE_PCT / spot_entry / NIFTY_LOT_SIZE))

            opt_type = None
            signal = None
            entry_px = 0.0
            exit_px = 0.0
            pnl_lot = 0.0

            # Bullish: Close > EMA5 > EMA20 and RSI > 60 (tightened from 55)
            if float(prev["Close"]) > prev_ema5 > prev_ema20 and prev_rsi > 60:
                opt_type = "CE"
                entry_px = bs_price(spot_entry, k, dte_e, iv, "CE")
                exit_px = bs_price(spot_exit, k, dte_x, iv, "CE")
                pnl_lot = (exit_px - entry_px) * NIFTY_LOT_SIZE * qty - TX_COST_SINGLE * qty
                signal = "EMA_BUY_CE"

            # Bearish: Close < EMA5 < EMA20 and RSI < 40 (tightened from 45)
            elif float(prev["Close"]) < prev_ema5 < prev_ema20 and prev_rsi < 40:
                opt_type = "PE"
                entry_px = bs_price(spot_entry, k, dte_e, iv, "PE")
                exit_px = bs_price(spot_exit, k, dte_x, iv, "PE")
                pnl_lot = (exit_px - entry_px) * NIFTY_LOT_SIZE * qty - TX_COST_SINGLE * qty
                signal = "EMA_BUY_PE"

            if signal:
                won = pnl_lot > 0
                tid = str(uuid.uuid4())[:8]

                log_trade_entry(
                    self.algo_id, tid, signal, spot_entry, k, opt_type,
                    round(entry_px, 2), f"{date_str} 09:20:00", NIFTY_LOT_SIZE * qty,
                    context={"bs_entry": round(entry_px, 2), "iv": iv}
                )
                log_trade_exit(
                    self.algo_id, tid, f"{date_str} 15:25:00", round(exit_px, 2),
                    "TARGET_EXIT" if won else "SL_EXIT", round(pnl_lot, 2),
                    round(pnl_lot / (entry_px * NIFTY_LOT_SIZE * qty) * 100, 2) if entry_px > 0 else 0,
                    context={"bs_exit": round(exit_px, 2), "close": spot_exit}
                )

                trades.append({
                    "trade_id": tid, "algo_id": "algo3", "date": date_str,
                    "symbol": "NIFTY", "strike": k, "option_type": opt_type,
                    "signal_name": signal, "entry_time": f"{date_str} 09:20:00",
                    "entry_price": round(entry_px, 2), "exit_time": f"{date_str} 15:25:00",
                    "exit_price": round(exit_px, 2),
                    "exit_reason": "TARGET_EXIT" if won else "SL_EXIT",
                    "pnl": round(pnl_lot, 2), "lot_size": NIFTY_LOT_SIZE,
                    "status": "closed", "qty": NIFTY_LOT_SIZE * qty,
                    "sub_strategy": "EMA_CROSSOVER",
                    "ema5": round(prev_ema5, 1), "ema20": round(prev_ema20, 1),
                    "rsi": round(prev_rsi, 1),
                })
                balance += pnl_lot
                daily_pnl += pnl_lot

                if daily_pnl <= -INITIAL_CAPITAL * MAX_DAILY_LOSS_PCT:
                    hit_daily_loss = True

        # ── Metrics ─────────────────────────────────────────────────────
        pnl_list = [t["pnl"] for t in trades]
        if pnl_list:
            wins = sum(1 for p in pnl_list if p > 0)
            wr = wins / len(pnl_list) * 100
            log_backtest_run(self.algo_id, start_date, end_date, len(trades), wr, sum(pnl_list))

        last = df.iloc[-1]
        ema5_last = float(last["EMA5"]) if pd.notna(last["EMA5"]) else 0
        ema20_last = float(last["EMA20"]) if pd.notna(last["EMA20"]) else 0
        rsi_last = float(last["RSI"]) if pd.notna(last["RSI"]) else 0

        signal_cards = {
            "Spot": round(float(last["Close"]), 0),
            "EMA5": round(ema5_last, 1), "EMA20": round(ema20_last, 1),
            "RSI": round(rsi_last, 1),
        }

        return {
            "metrics": self._metrics(pnl_list, INITIAL_CAPITAL),
            "trades": trades,
            "monthly": self._monthly_breakdown(trades),
            "equity_curve": self._equity_curve(trades),
            "signal_cards": signal_cards,
        }

    def get_live_signal(self, spot: float, indicators: Dict[str, float]) -> Dict[str, Any]:
        ema5 = indicators.get("ema5", 0.0)
        ema20 = indicators.get("ema20", 0.0)
        rsi = indicators.get("rsi", 50.0)

        if ema5 > ema20 and rsi > 55:
            return {
                "signal": "EMA_BUY_CE", "option_type": "CE", "strike": atm(spot),
                "signal_cards": {"Spot": spot, "EMA5": ema5, "EMA20": ema20, "RSI": rsi},
            }
        elif ema5 < ema20 and rsi < 45:
            return {
                "signal": "EMA_BUY_PE", "option_type": "PE", "strike": atm(spot),
                "signal_cards": {"Spot": spot, "EMA5": ema5, "EMA20": ema20, "RSI": rsi},
            }

        return {
            "signal": "NO_TRADE", "option_type": None, "strike": None,
            "signal_cards": {"Spot": spot, "EMA5": ema5, "EMA20": ema20, "RSI": rsi},
        }
