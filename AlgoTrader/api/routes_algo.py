"""
AlgoTrader — Per-Algo Routes
GET /api/algo/{algo_id}/summary   → detail view data
GET /api/algo/{algo_id}/trades    → paginated closed trades
GET /api/algo/{algo_id}/open      → open paper positions
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import pandas as pd
from datetime import date

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import ALGOS
from storage.csv_store import read_trades, read_open_positions, get_pnl_summary
from backtest.engine import get_algo_summary
from algos import get_algo
from paper.runner import paper_status
import yfinance as yf

router = APIRouter()


def _validate_algo(algo_id: str):
    if algo_id not in ALGOS:
        raise HTTPException(status_code=404, detail=f"Algo '{algo_id}' not found")


@router.get("/api/algo/{algo_id}/summary")
def algo_summary(algo_id: str):
    """Full detail for per-algo dashboard page."""
    _validate_algo(algo_id)
    summary = get_algo_summary(algo_id)
    summary["paper_running"] = paper_status(algo_id)
    summary["algo_meta"]     = ALGOS[algo_id]

    # Live signal cards from last backtest or live compute
    try:
        nifty   = yf.Ticker("^NSEI")
        spot    = float(nifty.fast_info.last_price)
        algo    = get_algo(algo_id)
        # Build basic indicators from today's yfinance daily bar
        hist    = nifty.history(period="60d", interval="1d")
        if not hist.empty:
            close   = hist["Close"]
            high    = hist["High"]
            low     = hist["Low"]
            ema5    = float(close.ewm(span=5, adjust=False).mean().iloc[-1])
            ema20   = float(close.ewm(span=20, adjust=False).mean().iloc[-1])
            delta   = close.diff()
            gain    = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
            loss    = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
            rsi     = float(100 - (100 / (1 + gain.iloc[-1] / max(loss.iloc[-1], 0.0001))))
            tr_     = pd.concat([high-low, (high-close.shift()).abs(), (low-close.shift()).abs()], axis=1).max(axis=1)
            atr_pct = float(tr_.rolling(14).mean().iloc[-1] / close.iloc[-1] * 100)
            indicators = {"ema5": ema5, "ema20": ema20, "rsi": rsi,
                          "atr_pct": atr_pct, "adx": 20.0, "regime": "RANGING",
                          "daily_range_pct": float((high.iloc[-1]-low.iloc[-1])/hist["Open"].iloc[-1]*100),
                          "close_move_pct": float(abs(close.iloc[-1]-hist["Open"].iloc[-1])/hist["Open"].iloc[-1]*100)}
            live_signal = algo.get_live_signal(spot, indicators)
            summary["live_signal"] = live_signal
    except Exception as e:
        summary["live_signal"] = {"signal": "UNAVAILABLE", "error": str(e)}

    return summary


@router.get("/api/algo/{algo_id}/trades")
def algo_trades(
    algo_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """Paginated closed trades for an algo."""
    _validate_algo(algo_id)
    df = read_trades(algo_id, start_date=start_date, end_date=end_date)
    total   = len(df)
    # Newest first
    df = df.sort_values("date", ascending=False) if not df.empty else df
    start_i = (page - 1) * page_size
    end_i   = start_i + page_size
    page_df = df.iloc[start_i:end_i]
    return {
        "algo_id":    algo_id,
        "total":      total,
        "page":       page,
        "page_size":  page_size,
        "pages":      (total + page_size - 1) // page_size,
        "trades":     page_df.to_dict("records") if not page_df.empty else [],
    }


@router.get("/api/algo/{algo_id}/open")
def algo_open_positions(algo_id: str):
    """Current open paper trading positions."""
    _validate_algo(algo_id)
    df = read_open_positions(algo_id)
    return {
        "algo_id":    algo_id,
        "positions":  df.to_dict("records") if not df.empty else [],
        "count":      len(df),
    }
