"""
AlgoTrader — Settings Store (JSON-backed)
Persists user settings across restarts:
  - Dhan Auth token
  - Per-algo capital overrides
  - Per-algo enabled/disabled flags
  - Per-algo reset flag (clears open positions + P&L)

File: data/settings.json
"""
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional

SETTINGS_FILE = Path(__file__).resolve().parent.parent / "data" / "settings.json"

DEFAULT_SETTINGS = {
    "dhan_auth_token": "",
    "algos": {},  # { "algo1": { "capital": 200000, "enabled": true, "reset": false }, ... }
}


def _load() -> Dict[str, Any]:
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return dict(DEFAULT_SETTINGS)


def _save(settings: Dict[str, Any]) -> None:
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)


# ── Public API ───────────────────────────────────────────────────────────────

def get_settings() -> Dict[str, Any]:
    return _load()


def get_dhan_token() -> str:
    return _load().get("dhan_auth_token", "")


def set_dhan_token(token: str) -> None:
    s = _load()
    s["dhan_auth_token"] = token.strip() if token else ""
    _save(s)


def get_algo_settings(algo_id: str) -> Dict[str, Any]:
    s = _load()
    return s.get("algos", {}).get(algo_id, {
        "capital": 200_000,
        "enabled": True,
        "reset": False,
    })


def set_algo_settings(algo_id: str, capital: Optional[int] = None,
                        enabled: Optional[bool] = None,
                        reset: Optional[bool] = None) -> Dict[str, Any]:
    s = _load()
    if "algos" not in s:
        s["algos"] = {}
    if algo_id not in s["algos"]:
        s["algos"][algo_id] = {"capital": 200_000, "enabled": True, "reset": False}

    if capital is not None:
        s["algos"][algo_id]["capital"] = max(0, int(capital))
    if enabled is not None:
        s["algos"][algo_id]["enabled"] = bool(enabled)
    if reset is not None:
        s["algos"][algo_id]["reset"] = bool(reset)

    _save(s)
    return s["algos"][algo_id]


def reset_algo(algo_id: str) -> None:
    """Mark algo for reset. The paper runner checks this flag and clears positions."""
    set_algo_settings(algo_id, reset=True)


def clear_reset_flag(algo_id: str) -> None:
    """Clear reset flag after positions have been cleared."""
    set_algo_settings(algo_id, reset=False)


def is_algo_reset_pending(algo_id: str) -> bool:
    return get_algo_settings(algo_id).get("reset", False)
