"""
AlgoTrader — Paper Trading Routes
POST /api/paper/{algo_id}/start  → start paper trading for an algo
POST /api/paper/{algo_id}/stop   → stop paper trading for an algo
GET  /api/paper/status           → status of all paper runners
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Any

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import ALGOS, ALGO_IDS
from paper.runner import start_paper, stop_paper, paper_status, get_all_status

router = APIRouter()


@router.post("/api/paper/{algo_id}/start")
def start_paper_trading(algo_id: str, background_tasks: BackgroundTasks):
    if algo_id not in ALGOS:
        raise HTTPException(status_code=404, detail=f"Algo '{algo_id}' not found")
    if paper_status(algo_id):
        return {"status": "already_running", "algo_id": algo_id}
    background_tasks.add_task(start_paper, algo_id)
    return {"status": "started", "algo_id": algo_id, "algo_name": ALGOS[algo_id]["name"]}


@router.post("/api/paper/{algo_id}/stop")
def stop_paper_trading(algo_id: str):
    if algo_id not in ALGOS:
        raise HTTPException(status_code=404, detail=f"Algo '{algo_id}' not found")
    stop_paper(algo_id)
    return {"status": "stopped", "algo_id": algo_id}


@router.get("/api/paper/status")
def all_paper_status() -> Dict[str, Any]:
    return {"runners": get_all_status()}
