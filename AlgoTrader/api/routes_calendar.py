"""
AlgoTrader — Calendar Routes
GET /api/calendar/{algo_id}/{year}/{month}  → daily P&L for calendar view
GET /api/calendar/all/{year}/{month}        → all algos combined for master calendar
GET /api/calendar/{algo_id}/date/{date_str} → all trades for a specific date
"""
from fastapi import APIRouter, HTTPException
from typing import Optional
import pandas as pd
from datetime import date as dt_date

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import ALGOS, ALGO_IDS
from storage.csv_store import get_calendar_data, read_trades

router = APIRouter()


@router.get("/api/calendar/all/{year}/{month}")
def calendar_all_monthly(year: int, month: int):
    """Daily P&L for all algos combined — for master dashboard calendar."""
    combined: dict = {}
    per_algo: dict = {}
    for algo_id in ALGO_IDS:
        daily = get_calendar_data(algo_id, year, month)
        per_algo[algo_id] = daily
        for date_str, pnl in daily.items():
            combined[date_str] = round(combined.get(date_str, 0) + pnl, 2)
    monthly_total = sum(combined.values())
    return {
        "year":          year,
        "month":         month,
        "combined_pnl":  combined,
        "per_algo_pnl":  per_algo,
        "monthly_total": round(monthly_total, 2),
    }


@router.get("/api/calendar/{algo_id}/{year}/{month}")
def calendar_monthly(algo_id: str, year: int, month: int):
    """Daily P&L dict for a single algo's calendar view."""
    if algo_id not in ALGOS:
        raise HTTPException(status_code=404, detail=f"Algo '{algo_id}' not found")
    daily_pnl     = get_calendar_data(algo_id, year, month)
    monthly_total = sum(daily_pnl.values())
    monthly_pct   = 0.0
    initial_cap   = ALGOS[algo_id]["initial_capital"]
    if initial_cap:
        monthly_pct = round(monthly_total / initial_cap * 100, 2)
    return {
        "algo_id":       algo_id,
        "year":          year,
        "month":         month,
        "daily_pnl":     daily_pnl,
        "monthly_total": round(monthly_total, 2),
        "monthly_pct":   monthly_pct,
    }


@router.get("/api/trades/date/{algo_id}/{date_str}")
def trades_for_date(algo_id: str, date_str: str):
    """All trades for a specific date (for right-panel click on calendar)."""
    if algo_id != "all" and algo_id not in ALGOS:
        raise HTTPException(status_code=404, detail=f"Algo '{algo_id}' not found")

    result = []
    query_ids = ALGO_IDS if algo_id == "all" else [algo_id]
    for aid in query_ids:
        df = read_trades(aid, start_date=date_str, end_date=date_str)
        if not df.empty:
            records = df.to_dict("records")
            for r in records:
                r["algo_name"] = ALGOS[aid]["name"]
            result.extend(records)

    day_pnl = sum(t.get("pnl", 0) for t in result)
    return {
        "date":       date_str,
        "algo_id":    algo_id,
        "trades":     result,
        "count":      len(result),
        "day_pnl":    round(day_pnl, 2),
    }
