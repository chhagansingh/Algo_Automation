"""
AlgoTrader — Backtest Routes
POST /api/backtest  → run backtest for one or multiple algos
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, date

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backtest.engine import run_backtest, run_compare
from config import ALGO_IDS
from storage.csv_store import replace_trades_for_date_range, compute_and_save_daily_summary

router = APIRouter()


class BacktestRequest(BaseModel):
    algo_ids:   List[str]
    start_date: str          # "YYYY-MM-DD"
    end_date:   str          # "YYYY-MM-DD"
    interval:   str = "1d"   # "1d", "1h", "30m", "15m", "5m", "1m"


@router.post("/api/backtest")
def run_backtest_api(req: BacktestRequest):
    """
    Run backtest for one or more algos over a date range.
    If single algo → returns single result.
    If multiple algos → returns compare result.
    """
    # Validate
    invalid = [a for a in req.algo_ids if a not in ALGO_IDS]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Unknown algo_ids: {invalid}")
    if not req.algo_ids:
        raise HTTPException(status_code=400, detail="algo_ids cannot be empty")

    try:
        datetime.strptime(req.start_date, "%Y-%m-%d")
        datetime.strptime(req.end_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Dates must be YYYY-MM-DD format")

    if req.start_date > req.end_date:
        raise HTTPException(status_code=400, detail="start_date must be before end_date")

    if len(req.algo_ids) == 1:
        try:
            result = run_backtest(req.algo_ids[0], req.start_date, req.end_date, interval=req.interval)
            _save_trades(req.algo_ids[0], req.start_date, req.end_date, result.get("trades", []))
            return {"mode": "single", "interval": req.interval, "result": result}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    else:
        try:
            result = run_compare(req.algo_ids, req.start_date, req.end_date, interval=req.interval)
            for algo_id in req.algo_ids:
                trades = result.get("results", {}).get(algo_id, {}).get("trades", [])
                _save_trades(algo_id, req.start_date, req.end_date, trades)
            return {"mode": "compare", "interval": req.interval, "result": result}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


def _save_trades(algo_id: str, start: str, end: str, trades: list):
    """Save backtest trades to CSV and rebuild daily summaries."""
    try:
        replace_trades_for_date_range(algo_id, start, end, trades)
        dates = set(t.get("date", "")[:10] for t in trades if t.get("date"))
        for d in dates:
            compute_and_save_daily_summary(algo_id, d)
    except Exception as e:
        print(f"[Backtest] save_trades error for {algo_id}: {e}")
