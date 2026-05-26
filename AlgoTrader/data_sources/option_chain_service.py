"""
Option Chain Polling Service
Runs a background thread that fetches real NSE option chain every N seconds.
Caches the result so algos, paper runner, and frontend can read instantly.
"""
import json
import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from .nse_fetcher import get_nse_fetcher

logger = logging.getLogger(__name__)

# Cache file for persistence across restarts
CACHE_FILE = Path(__file__).resolve().parent.parent / "data" / "option_chain_cache.json"

DEFAULT_REFRESH_SECONDS = 60  # same as NSE-OCA default


class OptionChainService:
    """
    Background polling service for NSE option chain.
    - Fetches every `refresh_seconds`
    - Stores parsed data in memory + disk cache
    - Thread-safe read access
    """

    def __init__(self, symbol: str = "NIFTY", refresh_seconds: int = DEFAULT_REFRESH_SECONDS):
        self.symbol = symbol
        self.refresh_seconds = refresh_seconds
        self._fetcher = get_nse_fetcher()
        self._latest: Optional[Dict[str, Any]] = None
        self._last_fetch_time: Optional[datetime] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._expiry: str = ""

        # Load previous cache if exists
        self._load_cache()

    def _load_cache(self) -> None:
        if CACHE_FILE.exists():
            try:
                with open(CACHE_FILE, "r") as f:
                    self._latest = json.load(f)
                logger.info("Loaded option chain cache from disk")
            except Exception as e:
                logger.warning("Failed to load cache: %s", e)

    def _save_cache(self) -> None:
        if self._latest:
            try:
                CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
                with open(CACHE_FILE, "w") as f:
                    json.dump(self._latest, f, default=str)
            except Exception as e:
                logger.warning("Failed to save cache: %s", e)

    def _poll_once(self) -> None:
        """Single fetch + parse + cache cycle."""
        try:
            # If no expiry known, fetch it first
            if not self._expiry:
                dates = self._fetcher.fetch_expiry_dates(self.symbol)
                if dates:
                    self._expiry = dates[0]
                    logger.info("Using expiry: %s", self._expiry)
                else:
                    logger.warning("No expiry dates found, retrying next cycle")
                    return

            parsed = self._fetcher.fetch_and_parse(self.symbol, self._expiry)
            if parsed:
                with self._lock:
                    self._latest = parsed
                    self._last_fetch_time = datetime.now()
                self._save_cache()
                logger.info(
                    "Option chain updated | Spot=%s ATM=%s PCR=%s Strikes=%d",
                    parsed.get("spot"),
                    parsed.get("atm_strike"),
                    parsed.get("pcr"),
                    len(parsed.get("strikes", [])),
                )
            else:
                logger.warning("Option chain fetch returned empty")
        except Exception as e:
            logger.error("Option chain poll error: %s", e)

    def _loop(self) -> None:
        """Background polling loop."""
        logger.info("Option chain polling started (every %ds)", self.refresh_seconds)
        while self._running:
            self._poll_once()
            # Sleep in short chunks so stop is responsive
            slept = 0
            while self._running and slept < self.refresh_seconds:
                time.sleep(1)
                slept += 1
        logger.info("Option chain polling stopped")

    # ── Public API ───────────────────────────────────────────────────

    def start(self) -> None:
        """Start background polling thread."""
        if self._running:
            return
        self._running = True
        # Do one immediate fetch before starting thread
        self._poll_once()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop background polling."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None

    def get_latest(self) -> Optional[Dict[str, Any]]:
        """Thread-safe read of latest cached option chain."""
        with self._lock:
            if self._latest is None:
                return None
            # Return a copy to prevent mutation
            import copy
            return copy.deepcopy(self._latest)

    def is_fresh(self, max_age_seconds: int = 120) -> bool:
        """Check if cached data is recent."""
        with self._lock:
            if self._last_fetch_time is None:
                return False
            return (datetime.now() - self._last_fetch_time).seconds <= max_age_seconds

    def get_atm_premiums(self) -> Dict[str, float]:
        """Return ATM CE/PE LTP for quick algo access."""
        data = self.get_latest()
        if not data:
            return {"ce_ltp": 0, "pe_ltp": 0, "spot": 0, "atm_strike": 0}
        return {
            "ce_ltp": data.get("atm_ce", {}).get("ltp", 0),
            "pe_ltp": data.get("atm_pe", {}).get("ltp", 0),
            "ce_iv": data.get("atm_ce", {}).get("iv", 0),
            "pe_iv": data.get("atm_pe", {}).get("iv", 0),
            "spot": data.get("spot", 0),
            "atm_strike": data.get("atm_strike", 0),
            "pcr": data.get("pcr", 0),
        }


# ── Module singleton ───────────────────────────────────────────────
_service: Optional[OptionChainService] = None


def get_option_chain_service(symbol: str = "NIFTY", refresh_seconds: int = DEFAULT_REFRESH_SECONDS) -> OptionChainService:
    global _service
    if _service is None:
        _service = OptionChainService(symbol=symbol, refresh_seconds=refresh_seconds)
    return _service


def start_service(refresh_seconds: int = DEFAULT_REFRESH_SECONDS) -> OptionChainService:
    svc = get_option_chain_service(refresh_seconds=refresh_seconds)
    svc.start()
    return svc


def stop_service() -> None:
    global _service
    if _service:
        _service.stop()
        _service = None
