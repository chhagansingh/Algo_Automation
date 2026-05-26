"""
AlgoTrader — Live Option Chain API Routes
GET /api/option-chain/{symbol}   → live NSE option chain + PCR + Max Pain + IV
GET /api/market-data/{symbol}    → spot + VIX + PCR summary
GET /api/option-chain/atmpremium/{symbol} → quick ATM CE/PE premiums for algos
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data_sources.nse_fetcher import get_nse_fetcher
from data_sources.option_chain_service import get_option_chain_service

router = APIRouter(prefix="/api", tags=["option_chain"])


@router.get("/option-chain/{symbol}")
def get_option_chain(symbol: str) -> Dict[str, Any]:
    """Fetch live option chain from NSE. Returns strikes, PCR, Max Pain, IV."""
    symbol = symbol.upper()
    if symbol not in ("NIFTY", "BANKNIFTY"):
        raise HTTPException(status_code=400, detail="symbol must be NIFTY or BANKNIFTY")

    svc = get_option_chain_service()
    data = svc.get_latest()

    # If cache empty or stale, do an immediate fetch
    if not data or not svc.is_fresh(max_age_seconds=120):
        fetcher = get_nse_fetcher()
        parsed = fetcher.fetch_and_parse(symbol)
        if not parsed:
            raise HTTPException(status_code=503, detail="NSE option chain fetch failed. Try again.")
        data = parsed

    strikes = data.get("strikes", [])
    return {
        "symbol": symbol,
        "spot": data.get("spot"),
        "atm_strike": data.get("atm_strike"),
        "expiry": data.get("expiry"),
        "timestamp": data.get("timestamp"),
        "pcr_oi": data.get("pcr"),
        "max_pain": data.get("max_pain_strike"),
        "total_ce_oi": data.get("total_ce_oi"),
        "total_pe_oi": data.get("total_pe_oi"),
        "strikes": [
            {
                "strike": s["strike"],
                "ce_ltp": s["ce"]["ltp"],
                "ce_oi": s["ce"]["oi"],
                "ce_iv": s["ce"]["iv"],
                "pe_ltp": s["pe"]["ltp"],
                "pe_oi": s["pe"]["oi"],
                "pe_iv": s["pe"]["iv"],
            }
            for s in strikes
        ],
    }


@router.get("/market-data/{symbol}")
def get_market_data(symbol: str) -> Dict[str, Any]:
    """Fetch live market snapshot: spot, VIX, PCR, ATM IV."""
    symbol = symbol.upper()
    fetcher = get_nse_fetcher()
    svc = get_option_chain_service()

    spot = fetcher.fetch_nifty_spot()
    data = svc.get_latest()

    # Force refresh if stale
    if not data or not svc.is_fresh(max_age_seconds=120):
        data = fetcher.fetch_and_parse(symbol)

    result = {
        "symbol": symbol,
        "spot": spot,
        "source": "nse",
    }

    if data:
        ce_iv = data.get("atm_ce", {}).get("iv", 0)
        pe_iv = data.get("atm_pe", {}).get("iv", 0)
        avg_iv = (ce_iv + pe_iv) / 2 if ce_iv and pe_iv else ce_iv or pe_iv
        result.update({
            "vix": avg_iv,
            "pcr_oi": data.get("pcr"),
            "max_pain": data.get("max_pain_strike"),
            "atm_strike": data.get("atm_strike"),
            "avg_iv": avg_iv,
            "timestamp": data.get("timestamp"),
        })

    return result


@router.get("/option-chain/atmpremium/{symbol}")
def get_atm_premium(symbol: str) -> Dict[str, Any]:
    """Quick endpoint for algos: returns ATM CE/PE LTP + IV."""
    symbol = symbol.upper()
    svc = get_option_chain_service()
    data = svc.get_latest()

    if not data:
        raise HTTPException(status_code=503, detail="Option chain not available yet.")

    ce = data.get("atm_ce", {})
    pe = data.get("atm_pe", {})
    return {
        "symbol": symbol,
        "spot": data.get("spot"),
        "atm_strike": data.get("atm_strike"),
        "ce_ltp": ce.get("ltp"),
        "pe_ltp": pe.get("ltp"),
        "ce_iv": ce.get("iv"),
        "pe_iv": pe.get("iv"),
        "pcr": data.get("pcr"),
        "timestamp": data.get("timestamp"),
        "fresh": svc.is_fresh(max_age_seconds=120),
    }
