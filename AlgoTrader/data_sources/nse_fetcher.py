"""
NSE India Real-Time Option Chain Fetcher
Uses the exact cookie-based session method from NSE-OCA analyzer.

Proven endpoints:
  - Landing page: https://www.nseindia.com/option-chain  (gets cookies)
  - Option Chain: https://www.nseindia.com/api/option-chain-v3?type=Indices&symbol={}&expiry={}
  - Contract info: https://www.nseindia.com/api/option-chain-contract-info?symbol={}
  - Symbol list: https://www.nseindia.com/api/underlying-information
"""
import json
import logging
import threading
import time
from datetime import datetime
from typing import Optional, Dict, Any, List

import requests

logger = logging.getLogger(__name__)

NSE_BASE = "https://www.nseindia.com"
HEADERS = {
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/130.0.0.0 Safari/537.36"
    ),
    "accept-language": "en,gu;q=0.9,hi;q=0.8",
    "accept-encoding": "gzip, deflate",
    "accept": "application/json, text/plain, */*",
    "referer": "https://www.nseindia.com/option-chain",
}

REQUEST_TIMEOUT = 15
MAX_RETRIES = 3
RETRY_DELAY = 3


class NSEOptionChainFetcher:
    """Fetches real option chain data from NSE India with cookie management."""

    def __init__(self):
        self._session: Optional[requests.Session] = None
        self._cookies: Dict[str, str] = {}
        self._last_refresh: Optional[datetime] = None
        self._lock = threading.Lock()
        # Cached data
        self._cached_chain: Optional[Dict[str, Any]] = None
        self._cached_atm: Optional[Dict[str, Any]] = None
        self._cached_meta: Optional[Dict[str, Any]] = None
        self._cache_time: Optional[datetime] = None

    # ── Session management ───────────────────────────────────────────

    def _refresh_session(self) -> bool:
        """Hit /option-chain landing page to get fresh cookies."""
        self._session = requests.Session()
        try:
            r = self._session.get(f"{NSE_BASE}/option-chain", headers=HEADERS, timeout=REQUEST_TIMEOUT)
            if r.status_code == 200:
                self._cookies = dict(r.cookies)
                self._last_refresh = datetime.now()
                logger.info("NSE session refreshed, cookies obtained")
                return True
        except Exception as e:
            logger.warning("NSE session refresh failed: %s", e)
        self._session = None
        return False

    def _ensure_session(self) -> bool:
        if self._session is None:
            return self._refresh_session()
        # Re-auth every 8 minutes to avoid 401
        if self._last_refresh and (datetime.now() - self._last_refresh).seconds > 480:
            return self._refresh_session()
        return True

    def _get(self, endpoint: str, context: str = "") -> Optional[requests.Response]:
        """GET with retry and session reset on 401."""
        if not self._ensure_session():
            return None
        url = f"{NSE_BASE}{endpoint}"
        for attempt in range(MAX_RETRIES):
            try:
                r = self._session.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT, cookies=self._cookies)
                if r.status_code == 401 and attempt < MAX_RETRIES - 1:
                    logger.warning("NSE 401 on %s, resetting session...", context)
                    self._refresh_session()
                    time.sleep(RETRY_DELAY)
                    continue
                if r.status_code == 200:
                    return r
                logger.warning("NSE %s HTTP %s", context, r.status_code)
            except Exception as e:
                logger.warning("NSE %s error (attempt %d/%d): %s", context, attempt + 1, MAX_RETRIES, e)
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
        return None

    # ── Option Chain ─────────────────────────────────────────────────

    def fetch_expiry_dates(self, symbol: str = "NIFTY") -> List[str]:
        """Return list of expiry dates like ['26-May-2026', ...]."""
        r = self._get(f"/api/option-chain-contract-info?symbol={symbol}", context="expiry_dates")
        if not r:
            return []
        try:
            data = r.json()
            dates = data.get("expiryDates") or data.get("records", {}).get("expiryDates", [])
            return dates if dates else []
        except Exception as e:
            logger.warning("Failed to parse expiry dates: %s", e)
            return []

    def fetch_option_chain(self, symbol: str = "NIFTY", expiry: str = "") -> Optional[Dict[str, Any]]:
        """
        Fetch full option chain for given symbol + expiry.
        If expiry is empty, uses the nearest expiry.
        """
        if not expiry:
            dates = self.fetch_expiry_dates(symbol)
            if not dates:
                logger.error("No expiry dates found for %s", symbol)
                return None
            expiry = dates[0]

        endpoint = f"/api/option-chain-v3?type=Indices&symbol={symbol}&expiry={expiry}"
        r = self._get(endpoint, context="option_chain")
        if not r:
            return None
        try:
            data = r.json()
            return data
        except Exception as e:
            logger.warning("Failed to parse option chain: %s", e)
            return None

    def parse_option_chain(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse raw NSE option chain into structured format:
        {
            spot: float,
            expiry: str,
            timestamp: str,
            strikes: [...],
            atm_strike: float,
            atm_ce: {...},
            atm_pe: {...},
            pcr: float,
            max_pain: float,
            total_ce_oi: int,
            total_pe_oi: int,
        }
        """
        records = raw_data.get("records", {})
        data_list = records.get("data", [])
        if not data_list:
            return {}

        # Spot price
        spot = 0.0
        for rec in data_list:
            ce = rec.get("CE", {})
            if ce and ce.get("underlyingValue", 0):
                spot = float(ce["underlyingValue"])
                break
            pe = rec.get("PE", {})
            if pe and pe.get("underlyingValue", 0):
                spot = float(pe["underlyingValue"])
                break

        strikes = []
        call_oi_map = {}
        put_oi_map = {}
        ce_oi_total = 0
        pe_oi_total = 0
        max_pain_val = 0.0
        max_pain_strike = 0.0

        for rec in data_list:
            sp = rec.get("strikePrice", 0)
            ce = rec.get("CE", {}) or {}
            pe = rec.get("PE", {}) or {}

            ce_oi = ce.get("openInterest", 0) or 0
            pe_oi = pe.get("openInterest", 0) or 0
            ce_oi_total += ce_oi
            pe_oi_total += pe_oi
            call_oi_map[sp] = ce_oi
            put_oi_map[sp] = pe_oi

            # Max pain = minimum loss for option writers
            # Simplified: max_pain strike = where (CE OI + PE OI) is highest
            pain = ce_oi + pe_oi
            if pain > max_pain_val:
                max_pain_val = pain
                max_pain_strike = sp

            strikes.append({
                "strike": sp,
                "ce": {
                    "ltp": ce.get("lastPrice", 0),
                    "bid": ce.get("bidPrice1", 0),
                    "ask": ce.get("askPrice1", 0),
                    "oi": ce_oi,
                    "oi_change": ce.get("changeinOpenInterest", 0),
                    "volume": ce.get("totalTradedVolume", 0),
                    "iv": ce.get("impliedVolatility", 0),
                    "delta": ce.get("delta", 0),
                },
                "pe": {
                    "ltp": pe.get("lastPrice", 0),
                    "bid": pe.get("bidPrice1", 0),
                    "ask": pe.get("askPrice1", 0),
                    "oi": pe_oi,
                    "oi_change": pe.get("changeinOpenInterest", 0),
                    "volume": pe.get("totalTradedVolume", 0),
                    "iv": pe.get("impliedVolatility", 0),
                    "delta": pe.get("delta", 0),
                },
            })

        # ATM strike
        atm_strike = min(strikes, key=lambda s: abs(s["strike"] - spot))["strike"] if strikes else 0
        atm_ce = next((s["ce"] for s in strikes if s["strike"] == atm_strike), {})
        atm_pe = next((s["pe"] for s in strikes if s["strike"] == atm_strike), {})

        pcr = round(pe_oi_total / ce_oi_total, 2) if ce_oi_total else 0

        return {
            "spot": spot,
            "expiry": records.get("expiryDates", [""])[0] if records.get("expiryDates") else "",
            "timestamp": records.get("timestamp", ""),
            "strikes": strikes,
            "atm_strike": atm_strike,
            "atm_ce": atm_ce,
            "atm_pe": atm_pe,
            "pcr": pcr,
            "max_pain_strike": max_pain_strike,
            "total_ce_oi": ce_oi_total,
            "total_pe_oi": pe_oi_total,
            "source": "nse_live",
        }

    # ── Spot / VIX helpers ───────────────────────────────────────────

    def fetch_nifty_spot(self) -> Optional[float]:
        """Fetch current Nifty spot via nsepython or direct API."""
        # Try nsepython first
        try:
            from nsepython import nse_get_index_quote
            q = nse_get_index_quote("NIFTY 50")
            if q and "last" in q:
                return float(q["last"].replace(",", ""))
        except Exception:
            pass
        # Fallback: extract from option chain
        cached = self.get_cached()
        if cached and cached.get("spot"):
            return float(cached["spot"])
        return None

    def fetch_vix(self) -> Optional[float]:
        """Fetch India VIX. Uses nsepython as primary."""
        try:
            from nsepython import indiavix
            v = indiavix()
            if v:
                return float(v)
        except Exception:
            pass
        # Fallback: ATM IV from cached chain
        cached = self.get_cached()
        if cached:
            ce_iv = cached.get("atm_ce", {}).get("iv", 0)
            pe_iv = cached.get("atm_pe", {}).get("iv", 0)
            avg = (ce_iv + pe_iv) / 2 if ce_iv and pe_iv else ce_iv or pe_iv
            if avg:
                return avg
        return None

    def fetch_all_indices(self) -> Optional[Dict[str, Any]]:
        return self._get("/api/allIndices", context="all_indices")

    def fetch_nifty_quote(self) -> Optional[Dict[str, Any]]:
        return self._get("/api/quotes?index=NIFTY%2050", context="nifty_quote")

    def fetch_fii_dii(self) -> Optional[Dict[str, Any]]:
        return self._get("/api/fiidiiTradeReact", context="fii_dii")

    def fetch_nifty_futures(self) -> Optional[Dict[str, Any]]:
        return self._get("/api/quote-derivative?symbol=NIFTY", context="nifty_futures")

    # ── Cached fetch ─────────────────────────────────────────────────

    def fetch_and_parse(self, symbol: str = "NIFTY", expiry: str = "") -> Optional[Dict[str, Any]]:
        """Fetch + parse + cache in one call."""
        raw = self.fetch_option_chain(symbol, expiry)
        if not raw:
            return None
        parsed = self.parse_option_chain(raw)
        with self._lock:
            self._cached_chain = raw
            self._cached_meta = parsed
            self._cache_time = datetime.now()
        return parsed

    def get_cached(self) -> Optional[Dict[str, Any]]:
        """Return last cached parsed data."""
        with self._lock:
            return self._cached_meta

    def get_cached_raw(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._cached_chain


# ── Module singleton ───────────────────────────────────────────────
_nse_fetcher: Optional[NSEOptionChainFetcher] = None


def get_nse_fetcher() -> NSEOptionChainFetcher:
    global _nse_fetcher
    if _nse_fetcher is None:
        _nse_fetcher = NSEOptionChainFetcher()
    return _nse_fetcher
