"""
Dhan.co API Fetcher — Intraday Candle Data & Option Chain with Greeks

Endpoints:
  1. Candle data: https://openweb-ticks.dhan.co/getData
     Params: EXCH, SEG, INST, SEC_ID, START, END, INTERVAL (5/15/30/60)
  2. Option chain: https://scanx.dhan.co/scanx/optchain
     Headers: Auth: <JWT token>
     Body: {"data": {"Seg": 0, "Sid": 13, "Exp": -1}}

Usage:
  from data_sources.dhan_fetcher import get_dhan_fetcher
  fetcher = get_dhan_fetcher()
  candles = fetcher.get_candles(interval="5", start_ts=1777141801, end_ts=1778178601)
  oc = fetcher.get_option_chain()
"""
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

import requests

logger = logging.getLogger(__name__)

DHAN_CANDLE_URL = "https://openweb-ticks.dhan.co/getData"
DHAN_OPTCHAIN_URL = "https://scanx.dhan.co/scanx/optchain"

# NIFTY 50 SEC_ID on Dhan
NIFTY_SEC_ID = 13

DEFAULT_TIMEOUT = 15
MAX_RETRIES = 2
RETRY_DELAY = 2


class DhanFetcher:
    """
    Fetches intraday candle data and option chain from Dhan.co APIs.
    Requires a valid Auth token (JWT) for option chain endpoint.
    """

    def __init__(self, auth_token: Optional[str] = None):
        self.auth_token = auth_token
        self._session = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})

    # ── Token management ───────────────────────────────────────────

    def set_auth_token(self, token: str) -> None:
        """Update the Dhan Auth token (JWT). Called from settings page."""
        self.auth_token = token.strip() if token else None
        if self.auth_token:
            self._session.headers["Auth"] = self.auth_token
            logger.info("Dhan Auth token updated")
        else:
            self._session.headers.pop("Auth", None)
            logger.warning("Dhan Auth token cleared")

    def has_auth(self) -> bool:
        return bool(self.auth_token)

    # ── Candle data ────────────────────────────────────────────────

    def get_candles(
        self,
        interval: str = "5",
        start_ts: Optional[int] = None,
        end_ts: Optional[int] = None,
        sec_id: int = NIFTY_SEC_ID,
        exch: str = "IDX",
        seg: str = "I",
        inst: str = "IDX",
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Fetch OHLCV candles from Dhan openweb ticks endpoint.

        Args:
            interval: Candle interval in minutes ("5", "15", "30", "60")
            start_ts: Unix timestamp (seconds) for start
            end_ts:   Unix timestamp (seconds) for end
            sec_id:   Security ID (13 = NIFTY 50)

        Returns:
            List of candle dicts: [{open, high, low, close, volume, timestamp}, ...]
            or None on failure.
        """
        if start_ts is None:
            # Default: last trading day
            end_dt = datetime.now()
            start_dt = end_dt - timedelta(days=1)
            start_ts = int(start_dt.timestamp())
            end_ts = int(end_dt.timestamp())

        payload = {
            "EXCH": exch,
            "SEG": seg,
            "INST": inst,
            "SEC_ID": sec_id,
            "START": start_ts,
            "END": end_ts,
            "INTERVAL": interval,
            "DELAY": False,
            "DELAYBY": 0,
        }

        for attempt in range(MAX_RETRIES):
            try:
                r = self._session.post(
                    DHAN_CANDLE_URL,
                    headers={"Content-Type": "application/json"},
                    json=payload,
                    timeout=DEFAULT_TIMEOUT,
                )
                if r.status_code == 200:
                    data = r.json()
                    candles = self._parse_candles(data)
                    logger.info(
                        "Dhan candles fetched | interval=%s | count=%d",
                        interval, len(candles) if candles else 0,
                    )
                    return candles
                elif r.status_code == 429:
                    logger.warning("Dhan rate limited, retrying...")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.warning("Dhan candle HTTP %s: %s", r.status_code, r.text[:200])
            except Exception as e:
                logger.warning("Dhan candle error (attempt %d/%d): %s", attempt + 1, MAX_RETRIES, e)
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)

        return None

    def _parse_candles(self, raw: Any) -> List[Dict[str, Any]]:
        """Parse Dhan candle response. Format varies — handle list, dict, nested dicts."""
        if raw is None:
            return []

        # Try to extract the list of candles from various formats
        data_list = None
        if isinstance(raw, list):
            data_list = raw
        elif isinstance(raw, dict):
            # Common response wrappers: { "data": [...] }, { "candles": [...] }, { "response": [...] }
            for key in ("data", "candles", "response", "ticks", "results", "records"):
                if key in raw and isinstance(raw[key], list):
                    data_list = raw[key]
                    break
            # If no known key, check if the dict itself contains candle-like keys
            if data_list is None and any(k in raw for k in ("open", "high", "low", "close")):
                data_list = [raw]

        if not data_list:
            logger.warning("Unexpected Dhan candle format: keys=%s", list(raw.keys()) if isinstance(raw, dict) else type(raw))
            return []

        candles = []
        for c in data_list:
            if not isinstance(c, dict):
                continue
            # Dhan may use different field names
            ts = c.get("date") or c.get("timestamp") or c.get("tradingDate") or c.get("start_Time")
            o = c.get("open") or c.get("Open") or c.get("o")
            h = c.get("high") or c.get("High") or c.get("h")
            lo = c.get("low") or c.get("Low") or c.get("l")
            cl = c.get("close") or c.get("Close") or c.get("c")
            vol = c.get("volume") or c.get("Volume") or c.get("v") or c.get("totalTradedVolume")
            try:
                candles.append({
                    "timestamp": ts,
                    "open": float(o) if o is not None else 0.0,
                    "high": float(h) if h is not None else 0.0,
                    "low": float(lo) if lo is not None else 0.0,
                    "close": float(cl) if cl is not None else 0.0,
                    "volume": int(vol) if vol is not None else 0,
                })
            except (ValueError, TypeError):
                continue
        return candles

    def get_candles_df(
        self,
        interval: str = "5",
        start_ts: Optional[int] = None,
        end_ts: Optional[int] = None,
        sec_id: int = NIFTY_SEC_ID,
    ) -> Optional[Any]:
        """Return candles as a pandas DataFrame with DatetimeIndex."""
        try:
            import pandas as pd
        except ImportError:
            logger.error("pandas not installed — cannot return DataFrame")
            return None

        candles = self.get_candles(interval, start_ts, end_ts, sec_id)
        if not candles:
            return None

        df = pd.DataFrame(candles)
        if "timestamp" in df.columns and df["timestamp"].notna().any():
            df["datetime"] = pd.to_datetime(df["timestamp"], unit="s", errors="coerce")
            df.set_index("datetime", inplace=True)
        return df

    # ── Option Chain ───────────────────────────────────────────────

    def get_option_chain(
        self,
        seg: int = 0,
        sid: int = NIFTY_SEC_ID,
        exp: int = -1,
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch option chain from Dhan ScanX with Greeks.
        Requires valid Auth token (JWT) in header.

        Args:
            seg: Segment (0 = Cash/F&O)
            sid: Security ID (13 = NIFTY)
            exp: Expiry index (-1 = all, 0 = nearest, etc.)

        Returns:
            Parsed option chain dict with strikes, Greeks, LTP, OI, IV.
        """
        if not self.has_auth():
            logger.warning("Dhan Auth token missing — cannot fetch option chain")
            return None

        payload = {"data": {"Seg": seg, "Sid": sid, "Exp": exp}}

        for attempt in range(MAX_RETRIES):
            try:
                r = self._session.post(
                    DHAN_OPTCHAIN_URL,
                    headers={"Content-Type": "application/json", "Auth": self.auth_token},
                    json=payload,
                    timeout=DEFAULT_TIMEOUT,
                )
                if r.status_code == 200:
                    data = r.json()
                    parsed = self._parse_option_chain(data)
                    logger.info(
                        "Dhan option chain fetched | strikes=%d | spot=%s",
                        len(parsed.get("strikes", [])),
                        parsed.get("spot"),
                    )
                    return parsed
                elif r.status_code == 401:
                    logger.error("Dhan Auth token expired or invalid (401)")
                    return None
                elif r.status_code == 429:
                    logger.warning("Dhan rate limited, retrying...")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.warning("Dhan optchain HTTP %s: %s", r.status_code, r.text[:200])
            except Exception as e:
                logger.warning("Dhan optchain error (attempt %d/%d): %s", attempt + 1, MAX_RETRIES, e)
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)

        return None

    def _parse_option_chain(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Dhan ScanX option chain response into standard format."""
        data = raw.get("data", raw)

        # Spot price
        spot = data.get("spotPrice", data.get("spot", data.get("underlyingPrice", 0)))

        # Strikes list
        strikes_raw = data.get("strikes", data.get("strikePrices", data.get("data", [])))
        strikes = []
        atm_strike = 0
        min_diff = float("inf")

        for s in strikes_raw:
            if isinstance(s, dict):
                strike = s.get("strike", s.get("strikePrice", 0))
                ce = s.get("ce", s.get("CE", {}))
                pe = s.get("pe", s.get("PE", {}))
            else:
                continue

            strike_val = float(strike)
            diff = abs(strike_val - spot)
            if diff < min_diff:
                min_diff = diff
                atm_strike = strike_val

            strikes.append({
                "strike": strike_val,
                "ce": {
                    "ltp": ce.get("ltp", ce.get("lastPrice", 0)),
                    "bid": ce.get("bid", ce.get("bidPrice", 0)),
                    "ask": ce.get("ask", ce.get("askPrice", 0)),
                    "oi": int(ce.get("oi", ce.get("openInterest", 0))),
                    "iv": ce.get("iv", ce.get("impliedVolatility", 0)),
                    "delta": ce.get("delta", 0),
                    "gamma": ce.get("gamma", 0),
                    "theta": ce.get("theta", 0),
                    "vega": ce.get("vega", 0),
                },
                "pe": {
                    "ltp": pe.get("ltp", pe.get("lastPrice", 0)),
                    "bid": pe.get("bid", pe.get("bidPrice", 0)),
                    "ask": pe.get("ask", pe.get("askPrice", 0)),
                    "oi": int(pe.get("oi", pe.get("openInterest", 0))),
                    "iv": pe.get("iv", pe.get("impliedVolatility", 0)),
                    "delta": pe.get("delta", 0),
                    "gamma": pe.get("gamma", 0),
                    "theta": pe.get("theta", 0),
                    "vega": pe.get("vega", 0),
                },
            })

        # Find ATM CE/PE
        atm_ce = next((s["ce"] for s in strikes if s["strike"] == atm_strike), {})
        atm_pe = next((s["pe"] for s in strikes if s["strike"] == atm_strike), {})

        # PCR
        total_ce_oi = sum(s["ce"]["oi"] for s in strikes)
        total_pe_oi = sum(s["pe"]["oi"] for s in strikes)
        pcr = total_pe_oi / total_ce_oi if total_ce_oi else 0

        return {
            "spot": spot,
            "atm_strike": atm_strike,
            "strikes": strikes,
            "atm_ce": atm_ce,
            "atm_pe": atm_pe,
            "pcr": round(pcr, 2),
            "total_ce_oi": total_ce_oi,
            "total_pe_oi": total_pe_oi,
            "timestamp": datetime.now().isoformat(),
            "source": "dhan",
        }

    def get_atm_premiums(self) -> Dict[str, Any]:
        """Quick helper: return ATM CE/PE LTP + IV from Dhan option chain."""
        oc = self.get_option_chain()
        if not oc:
            return {"ce_ltp": 0, "pe_ltp": 0, "spot": 0, "atm_strike": 0}
        return {
            "spot": oc.get("spot"),
            "atm_strike": oc.get("atm_strike"),
            "ce_ltp": oc.get("atm_ce", {}).get("ltp"),
            "pe_ltp": oc.get("atm_pe", {}).get("ltp"),
            "ce_iv": oc.get("atm_ce", {}).get("iv"),
            "pe_iv": oc.get("atm_pe", {}).get("iv"),
            "pcr": oc.get("pcr"),
            "timestamp": oc.get("timestamp"),
        }


# ── Module singleton ───────────────────────────────────────────────────
_dhan_fetcher: Optional[DhanFetcher] = None


def get_dhan_fetcher() -> DhanFetcher:
    global _dhan_fetcher
    if _dhan_fetcher is None:
        _dhan_fetcher = DhanFetcher()
    return _dhan_fetcher
