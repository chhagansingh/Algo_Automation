"""
AlgoTrader — Backtest Engine
Runs backtests for one or multiple algos over a date range.
Returns metrics, trades list, monthly breakdown, equity curve.
"""
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from algos import get_algo
from config import ALGOS, ALGO_IDS


def run_backtest(algo_id: str, start_date: str, end_date: str, interval: str = "1d") -> Dict[str, Any]:
    """
    Run backtest for a single algo over [start_date, end_date] with custom interval.
    interval: "1d", "1h", "30m", "15m", "5m", "1m"
    Returns full result dict with metrics, trades, monthly breakdown, equity curve.
    """
    if algo_id not in ALGOS:
        raise ValueError(f"Unknown algo_id: {algo_id}")

    algo   = get_algo(algo_id)
    result = algo.run_backtest(start_date, end_date, interval=interval)

    # Add run metadata
    result["algo_id"]     = algo_id
    result["algo_name"]   = ALGOS[algo_id]["name"]
    result["start_date"]  = start_date
    result["end_date"]    = end_date
    result["interval"]    = interval
    result["run_time"]    = datetime.now().isoformat()

    return result


def run_compare(algo_ids: List[str], start_date: str, end_date: str, interval: str = "1d") -> Dict[str, Any]:
    """
    Run backtest for multiple algos over the same date range with custom interval.
    Returns side-by-side comparison structure.
    """
    results = {}
    for algo_id in algo_ids:
        if algo_id not in ALGOS:
            continue
        results[algo_id] = run_backtest(algo_id, start_date, end_date, interval=interval)

    # Build compare summary table
    compare_table = []
    metrics_keys = [
        "total_trades", "wins", "losses", "win_rate",
        "final_pnl", "roc_pct", "max_drawdown", "sharpe",
        "max_consec_loss", "avg_win", "avg_loss",
    ]
    for key in metrics_keys:
        row = {"metric": _metric_label(key)}
        for algo_id, res in results.items():
            row[algo_id] = res.get("metrics", {}).get(key, 0)
        compare_table.append(row)

    # Combined monthly breakdown (union of all months)
    all_months = set()
    for res in results.values():
        all_months.update(res.get("monthly", {}).keys())
    all_months = sorted(all_months)

    monthly_compare = []
    for month in all_months:
        row = {"month": month}
        for algo_id, res in results.items():
            row[algo_id] = res.get("monthly", {}).get(month, 0)
        monthly_compare.append(row)

    # Equity curves per algo (for Chart.js multi-line)
    equity_curves = {}
    for algo_id, res in results.items():
        equity_curves[algo_id] = res.get("equity_curve", [])

    return {
        "algo_ids":       algo_ids,
        "start_date":     start_date,
        "end_date":       end_date,
        "interval":       interval,
        "run_time":       datetime.now().isoformat(),
        "results":        results,
        "compare_table":  compare_table,
        "monthly_compare": monthly_compare,
        "equity_curves":  equity_curves,
    }


def _metric_label(key: str) -> str:
    labels = {
        "total_trades":    "Total Trades",
        "wins":            "Wins",
        "losses":          "Losses",
        "win_rate":        "Win Rate (%)",
        "final_pnl":       "Final P&L (₹)",
        "roc_pct":         "ROC (%)",
        "max_drawdown":    "Max Drawdown (₹)",
        "sharpe":          "Sharpe Ratio",
        "max_consec_loss": "Max Consec. Losses",
        "avg_win":         "Avg Win (₹)",
        "avg_loss":        "Avg Loss (₹)",
    }
    return labels.get(key, key)


def get_algo_summary(algo_id: str) -> Dict[str, Any]:
    """
    Return a quick summary for the dashboard card (no backtest run —
    reads from stored trades CSV for historical, and returns live signal cards).
    """
    from storage.csv_store import get_pnl_summary, read_open_positions, read_trades
    import pandas as pd
    from datetime import date

    pnl_summary  = get_pnl_summary(algo_id)
    open_pos_df  = read_open_positions(algo_id)
    trades_df    = read_trades(algo_id)

    open_positions = open_pos_df.to_dict("records") if not open_pos_df.empty else []
    today_str      = date.today().isoformat()

    # Today's closed trades
    today_trades = []
    if not trades_df.empty:
        trades_df["date"] = pd.to_datetime(trades_df["date"])
        today_trades = trades_df[trades_df["date"].dt.date == date.today()].to_dict("records")

    return {
        "algo_id":        algo_id,
        "algo_name":      ALGOS[algo_id]["name"],
        "short_name":     ALGOS[algo_id].get("short_name", ALGOS[algo_id]["name"]),
        "tag":            ALGOS[algo_id].get("tag", ""),
        "subtitle":       ALGOS[algo_id]["subtitle"],
        "pnl_summary":    pnl_summary,
        "open_positions": open_positions,
        "today_trades":   today_trades,
        "positions_count": len(open_positions),
    }
