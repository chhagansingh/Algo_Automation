"""
AlgoTrader — CSV Storage Layer
All read/write operations for trades, paper positions, daily summary.
"""
import os
import uuid
import pandas as pd
from datetime import datetime, date
from typing import Optional, List, Dict, Any

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import CSV_TRADES, CSV_PAPER_OPEN, CSV_DAILY_SUMMARY

# ── Column schemas ─────────────────────────────────────────────────────────────
TRADES_COLS = [
    "trade_id", "algo_id", "date", "symbol", "strike", "option_type",
    "signal_name", "entry_time", "entry_price", "exit_time", "exit_price",
    "exit_reason", "pnl", "pnl_pct", "lot_size", "status",
]

PAPER_OPEN_COLS = [
    "trade_id", "algo_id", "open_time", "symbol", "strike", "option_type",
    "signal_name", "entry_price", "current_ltp", "unrealized_pnl", "lot_size",
]

DAILY_SUMMARY_COLS = [
    "date", "algo_id", "total_pnl", "trades_count", "wins", "losses",
]


def _ensure_dir(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)


def _init_csv(path: str, cols: list):
    """Create CSV with headers if it doesn't exist."""
    _ensure_dir(path)
    if not os.path.exists(path):
        pd.DataFrame(columns=cols).to_csv(path, index=False)


def init_all_csvs():
    """Initialize all CSV files with correct headers (idempotent)."""
    for algo_id, path in CSV_TRADES.items():
        _init_csv(path, TRADES_COLS)
    for algo_id, path in CSV_PAPER_OPEN.items():
        _init_csv(path, PAPER_OPEN_COLS)
    _init_csv(CSV_DAILY_SUMMARY, DAILY_SUMMARY_COLS)


# ── Trades ─────────────────────────────────────────────────────────────────────
def read_trades(algo_id: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
    """Read closed trades for an algo, optionally filtered by date range."""
    path = CSV_TRADES[algo_id]
    _init_csv(path, TRADES_COLS)
    df = pd.read_csv(path)
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"], errors='coerce')
    if start_date:
        df = df[df["date"] >= pd.to_datetime(start_date)]
    if end_date:
        df = df[df["date"] <= pd.to_datetime(end_date)]
    return df.reset_index(drop=True)


def write_trade(trade: Dict[str, Any]):
    """Append a single closed trade to its algo's trades CSV."""
    algo_id = trade["algo_id"]
    path = CSV_TRADES[algo_id]
    _init_csv(path, TRADES_COLS)
    if "trade_id" not in trade or not trade["trade_id"]:
        trade["trade_id"] = str(uuid.uuid4())[:8]
    row = pd.DataFrame([{col: trade.get(col, "") for col in TRADES_COLS}])
    row.to_csv(path, mode="a", header=False, index=False)


def write_trades_bulk(algo_id: str, trades: List[Dict[str, Any]]):
    """Write a list of trades (from backtest) — replaces existing for that algo+date range if needed."""
    if not trades:
        return
    path = CSV_TRADES[algo_id]
    _ensure_dir(path)
    df = pd.DataFrame(trades)
    for col in TRADES_COLS:
        if col not in df.columns:
            df[col] = ""
    df = df[TRADES_COLS]
    # Append to existing
    existing = pd.read_csv(path) if os.path.exists(path) else pd.DataFrame(columns=TRADES_COLS)
    combined = pd.concat([existing, df], ignore_index=True)
    combined.to_csv(path, index=False)


def replace_trades_for_date_range(algo_id: str, start_date: str, end_date: str, trades: List[Dict[str, Any]]):
    """Replace trades in a date range (for backtest save — removes old, writes new)."""
    path = CSV_TRADES[algo_id]
    _init_csv(path, TRADES_COLS)
    existing = pd.read_csv(path)
    if not existing.empty:
        existing["date"] = pd.to_datetime(existing["date"], errors='coerce')
        mask = (existing["date"] >= pd.to_datetime(start_date)) & (existing["date"] <= pd.to_datetime(end_date))
        existing = existing[~mask]
    new_rows = pd.DataFrame(trades)
    for col in TRADES_COLS:
        if col not in new_rows.columns:
            new_rows[col] = ""
    combined = pd.concat([existing, new_rows[TRADES_COLS]], ignore_index=True)
    combined.to_csv(path, index=False)


# ── Paper open positions ────────────────────────────────────────────────────────
def read_open_positions(algo_id: str) -> pd.DataFrame:
    path = CSV_PAPER_OPEN[algo_id]
    _init_csv(path, PAPER_OPEN_COLS)
    return pd.read_csv(path)


def write_open_position(position: Dict[str, Any]):
    algo_id = position["algo_id"]
    path = CSV_PAPER_OPEN[algo_id]
    _init_csv(path, PAPER_OPEN_COLS)
    if "trade_id" not in position or not position["trade_id"]:
        position["trade_id"] = str(uuid.uuid4())[:8]
    row = pd.DataFrame([{col: position.get(col, "") for col in PAPER_OPEN_COLS}])
    row.to_csv(path, mode="a", header=False, index=False)


def close_open_position(algo_id: str, trade_id: str, exit_price: float, exit_time: str, exit_reason: str) -> Optional[Dict]:
    """Move an open position to closed trades, remove from open CSV."""
    path = CSV_PAPER_OPEN[algo_id]
    _init_csv(path, PAPER_OPEN_COLS)
    df = pd.read_csv(path)
    row = df[df["trade_id"] == trade_id]
    if row.empty:
        return None
    r = row.iloc[0].to_dict()
    # Remove from open
    df = df[df["trade_id"] != trade_id]
    df.to_csv(path, index=False)
    # Build closed trade record
    entry_price = float(r.get("entry_price", 0))
    lot_size = int(r.get("lot_size", 25))
    pnl = (exit_price - entry_price) * lot_size
    pnl_pct = (pnl / (entry_price * lot_size) * 100) if entry_price > 0 else 0
    trade = {
        "trade_id": r["trade_id"],
        "algo_id": algo_id,
        "date": r["open_time"][:10],
        "symbol": r.get("symbol", "NIFTY"),
        "strike": r.get("strike", ""),
        "option_type": r.get("option_type", ""),
        "signal_name": r.get("signal_name", ""),
        "entry_time": r.get("open_time", ""),
        "entry_price": entry_price,
        "exit_time": exit_time,
        "exit_price": exit_price,
        "exit_reason": exit_reason,
        "pnl": round(pnl, 2),
        "pnl_pct": round(pnl_pct, 2),
        "lot_size": lot_size,
        "status": "closed",
    }
    write_trade(trade)
    return trade


def clear_open_positions(algo_id: str):
    """Clear all open positions for an algo (e.g. when paper trading stops)."""
    path = CSV_PAPER_OPEN[algo_id]
    pd.DataFrame(columns=PAPER_OPEN_COLS).to_csv(path, index=False)


# ── Daily summary ──────────────────────────────────────────────────────────────
def read_daily_summary(algo_id: Optional[str] = None, year: Optional[int] = None, month: Optional[int] = None) -> pd.DataFrame:
    _init_csv(CSV_DAILY_SUMMARY, DAILY_SUMMARY_COLS)
    df = pd.read_csv(CSV_DAILY_SUMMARY)
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"], errors='coerce')
    if algo_id:
        df = df[df["algo_id"] == algo_id]
    if year:
        df = df[df["date"].dt.year == year]
    if month:
        df = df[df["date"].dt.month == month]
    return df.reset_index(drop=True)


def compute_and_save_daily_summary(algo_id: str, trade_date: str):
    """Compute daily summary from trades CSV for a given date and upsert."""
    trades = read_trades(algo_id, start_date=trade_date, end_date=trade_date)
    total_pnl = trades["pnl"].sum() if not trades.empty else 0
    count = len(trades)
    wins = int((trades["pnl"] > 0).sum()) if not trades.empty else 0
    losses = int((trades["pnl"] < 0).sum()) if not trades.empty else 0

    _init_csv(CSV_DAILY_SUMMARY, DAILY_SUMMARY_COLS)
    df = pd.read_csv(CSV_DAILY_SUMMARY)
    # Remove old entry for same date+algo
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"], errors='coerce')
        df = df[~((df["date"] == pd.to_datetime(trade_date)) & (df["algo_id"] == algo_id))]
    new_row = pd.DataFrame([{
        "date": trade_date, "algo_id": algo_id,
        "total_pnl": round(total_pnl, 2),
        "trades_count": count, "wins": wins, "losses": losses,
    }])
    combined = pd.concat([df, new_row], ignore_index=True)
    combined.to_csv(CSV_DAILY_SUMMARY, index=False)


# ── Aggregate helpers ───────────────────────────────────────────────────────────
def get_pnl_summary(algo_id: str) -> Dict[str, float]:
    """Return P&L for Today / 1M / 3M / 6M / 1Y."""
    trades = read_trades(algo_id)
    if trades.empty:
        return {"today": 0, "one_month": 0, "three_month": 0, "six_month": 0, "one_year": 0}
    trades["date"] = pd.to_datetime(trades["date"])
    now = pd.Timestamp.now()
    def pnl_since(days):
        cutoff = now - pd.Timedelta(days=days)
        return float(trades[trades["date"] >= cutoff]["pnl"].sum())
    today = date.today().isoformat()
    today_pnl = float(trades[trades["date"].dt.date == date.today()]["pnl"].sum())
    return {
        "today":       round(today_pnl, 2),
        "one_month":   round(pnl_since(30), 2),
        "three_month": round(pnl_since(90), 2),
        "six_month":   round(pnl_since(180), 2),
        "one_year":    round(pnl_since(365), 2),
    }


def get_calendar_data(algo_id: str, year: int, month: int) -> Dict[str, float]:
    """Return {date_str: pnl} for each trading day in the month."""
    trades = read_trades(algo_id)
    if trades.empty:
        return {}
    trades["date"] = pd.to_datetime(trades["date"])
    mask = (trades["date"].dt.year == year) & (trades["date"].dt.month == month)
    monthly = trades[mask].groupby(trades["date"].dt.strftime("%Y-%m-%d"))["pnl"].sum()
    return {k: round(float(v), 2) for k, v in monthly.items()}
