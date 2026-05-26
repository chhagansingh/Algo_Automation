"""
AlgoTrader — Settings Routes
GET  /api/settings                → all settings
POST /api/settings/dhan-token     → update Dhan Auth token
GET  /api/settings/dhan-token   → current token (masked)
POST /api/settings/algo/{id}      → update algo capital / enabled / reset
GET  /api/settings/algo/{id}     → algo settings
POST /api/settings/algo/{id}/reset → reset algo (clear positions + P&L)
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import ALGOS
from utils.settings_store import (
    get_settings, get_dhan_token, set_dhan_token,
    get_algo_settings, set_algo_settings, reset_algo, clear_reset_flag,
    is_algo_reset_pending,
)
from data_sources.dhan_fetcher import get_dhan_fetcher

router = APIRouter()


class DhanTokenPayload(BaseModel):
    token: str


class AlgoSettingsPayload(BaseModel):
    capital: Optional[int] = None
    enabled: Optional[bool] = None
    reset: Optional[bool] = None


@router.get("/api/settings")
def get_all_settings():
    """Return all settings (token is masked)."""
    s = get_settings()
    token = s.get("dhan_auth_token", "")
    masked = token[:6] + "..." + token[-4:] if len(token) > 10 else "(not set)"
    return {
        "dhan_token_masked": masked,
        "dhan_token_set": bool(token),
        "algos": s.get("algos", {}),
    }


@router.post("/api/settings/dhan-token")
def update_dhan_token(payload: DhanTokenPayload):
    """Save Dhan Auth token and sync to fetcher."""
    token = payload.token.strip()
    set_dhan_token(token)
    fetcher = get_dhan_fetcher()
    fetcher.set_auth_token(token)
    return {
        "status": "saved",
        "token_masked": token[:6] + "..." + token[-4:] if len(token) > 10 else "(not set)",
    }


@router.get("/api/settings/dhan-token")
def read_dhan_token():
    """Return masked token + test connectivity."""
    token = get_dhan_token()
    masked = token[:6] + "..." + token[-4:] if len(token) > 10 else "(not set)"

    # Quick connectivity test
    test_result = {"token_set": bool(token), "candles": None, "option_chain": None}
    if token:
        fetcher = get_dhan_fetcher()
        fetcher.set_auth_token(token)
        # Try option chain (most likely to fail if token bad)
        oc = fetcher.get_option_chain()
        test_result["option_chain"] = "OK" if oc else "FAILED"
        test_result["option_chain_strikes"] = len(oc.get("strikes", [])) if oc else 0

    return {
        "token_masked": masked,
        "test": test_result,
    }


@router.get("/api/settings/algo/{algo_id}")
def read_algo_settings(algo_id: str):
    if algo_id not in ALGOS:
        raise HTTPException(status_code=404, detail=f"Algo '{algo_id}' not found")
    return {
        "algo_id": algo_id,
        "settings": get_algo_settings(algo_id),
    }


@router.post("/api/settings/algo/{algo_id}")
def update_algo_settings(algo_id: str, payload: AlgoSettingsPayload):
    if algo_id not in ALGOS:
        raise HTTPException(status_code=404, detail=f"Algo '{algo_id}' not found")

    updated = set_algo_settings(
        algo_id,
        capital=payload.capital,
        enabled=payload.enabled,
        reset=payload.reset,
    )
    return {"status": "saved", "algo_id": algo_id, "settings": updated}


@router.post("/api/settings/algo/{algo_id}/reset")
def reset_algo_endpoint(algo_id: str):
    """Reset an algo: clear all open positions and P&L."""
    if algo_id not in ALGOS:
        raise HTTPException(status_code=404, detail=f"Algo '{algo_id}' not found")

    reset_algo(algo_id)
    return {
        "status": "reset_requested",
        "algo_id": algo_id,
        "message": f"Algo {algo_id} marked for reset. Positions will be cleared on next paper interval.",
    }


@router.get("/api/dhan/candles")
def get_dhan_candles(
    interval: str = "5",
    start: Optional[int] = None,
    end: Optional[int] = None,
):
    """Fetch Dhan candle data. Interval: 5, 15, 30, 60 (minutes)."""
    fetcher = get_dhan_fetcher()
    candles = fetcher.get_candles(interval=interval, start_ts=start, end_ts=end)
    if candles is None:
        return {"error": "Failed to fetch candles from Dhan. Check token and connectivity."}
    return {"candles": candles, "count": len(candles), "interval": interval}


@router.get("/api/dhan/option-chain")
def get_dhan_option_chain():
    """Fetch Dhan option chain with Greeks."""
    fetcher = get_dhan_fetcher()
    oc = fetcher.get_option_chain()
    if oc is None:
        return {"error": "Failed to fetch option chain from Dhan. Check Auth token."}
    return oc
