"""
AlgoTrader — Log Viewer API Routes
GET  /api/logs/{algo_id}/dates       → list available log dates
GET  /api/logs/{algo_id}/{date}.log  → raw log content for a date
"""
import os
from datetime import datetime
from typing import List, Dict, Any

from fastapi import APIRouter, HTTPException

from config import LOGS_DIR, ALGOS, ALGO_IDS

router = APIRouter(prefix="/api/logs", tags=["logs"])


def _algo_log_dir(algo_id: str) -> str:
    return os.path.join(LOGS_DIR, algo_id)


@router.get("/{algo_id}/dates")
def list_log_dates(algo_id: str) -> Dict[str, Any]:
    if algo_id not in ALGO_IDS:
        raise HTTPException(status_code=404, detail="Unknown algo_id")
    log_dir = _algo_log_dir(algo_id)
    if not os.path.isdir(log_dir):
        return {"algo_id": algo_id, "dates": []}
    files = sorted(
        [f.replace(".log", "") for f in os.listdir(log_dir) if f.endswith(".log")],
        reverse=True
    )
    return {"algo_id": algo_id, "dates": files}


@router.get("/{algo_id}/{date_str}.log")
def get_log_content(algo_id: str, date_str: str) -> Dict[str, Any]:
    if algo_id not in ALGO_IDS:
        raise HTTPException(status_code=404, detail="Unknown algo_id")
    # Validate date_str format (YYYY-MM-DD)
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="date_str must be YYYY-MM-DD")

    log_file = os.path.join(_algo_log_dir(algo_id), f"{date_str}.log")
    if not os.path.isfile(log_file):
        return {"algo_id": algo_id, "date": date_str, "lines": [], "exists": False}

    with open(log_file, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()

    return {"algo_id": algo_id, "date": date_str, "lines": lines, "exists": True}
