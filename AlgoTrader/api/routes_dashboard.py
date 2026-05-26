"""
AlgoTrader — Dashboard Routes
GET /api/dashboard  → master summary for all algos
GET /api/nifty/live → live Nifty price + VIX
"""
from fastapi import APIRouter
from typing import Dict, Any
import yfinance as yf
import pandas as pd
from datetime import datetime

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import ALGOS, ALGO_IDS
from backtest.engine import get_algo_summary
from paper.runner import paper_status

router = APIRouter()


@router.get("/api/dashboard")
def get_dashboard() -> Dict[str, Any]:
    """Master dashboard: summary cards for all 3 algos."""
    summaries = {}
    for algo_id in ALGO_IDS:
        try:
            summaries[algo_id] = get_algo_summary(algo_id)
            summaries[algo_id]["paper_running"] = paper_status(algo_id)
        except Exception as e:
            summaries[algo_id] = {
                "algo_id": algo_id,
                "algo_name": ALGOS[algo_id]["name"],
                "error": str(e),
                "paper_running": False,
            }
    return {"algos": summaries, "timestamp": datetime.now().isoformat()}


@router.get("/api/nifty/live")
def get_nifty_live() -> Dict[str, Any]:
    """Fetch live Nifty price and VIX via yfinance fast_info."""
    try:
        nifty  = yf.Ticker("^NSEI")
        vix    = yf.Ticker("^INDIAVIX")
        nifty_price = nifty.fast_info.get("last_price") or nifty.fast_info.last_price
        vix_price   = vix.fast_info.get("last_price") or vix.fast_info.last_price
        return {
            "nifty": round(float(nifty_price), 2),
            "vix":   round(float(vix_price), 2),
            "time":  datetime.now().strftime("%I:%M:%S %p"),
        }
    except Exception as e:
        return {"nifty": 0.0, "vix": 0.0, "time": "--", "error": str(e)}
