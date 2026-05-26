"""
BacktestWrapper — Run imported algo through AlgoTrader engine and compare with existing algos.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from typing import Dict, Any, List
from backtest.engine import run_compare
from config import ALGOS


def compare_imported(
    imported_algo_id: str,
    start_date: str,
    end_date: str,
    interval: str = "1d",
    baseline_algos: List[str] = None
) -> Dict[str, Any]:
    """
    Backtest the newly imported algo alongside baseline algos (algo1, algo2, algo3).

    Parameters
    ----------
    imported_algo_id : str
        The algo_id of the newly imported algorithm.
    start_date, end_date : YYYY-MM-DD
    interval : str
        "1d", "1h", "15m", "5m"
    baseline_algos : list
        Algo IDs to compare against. Default = ["algo1", "algo2", "algo3"]

    Returns
    -------
    dict with comparison table, monthly breakdown, and recommendations.
    """
    if baseline_algos is None:
        baseline_algos = ["algo1", "algo2", "algo3"]

    all_algos = baseline_algos + [imported_algo_id]
    all_algos = [a for a in all_algos if a in ALGOS]

    if imported_algo_id not in ALGOS:
        print(f"ERROR: '{imported_algo_id}' not found in config.py ALGOS. Please register it first.")
        return {}

    print(f"\n{'='*70}")
    print(f"COMPARING: {imported_algo_id} vs Baseline Algos")
    print(f"Period: {start_date} to {end_date} | Interval: {interval}")
    print(f"{'='*70}")

    result = run_compare(all_algos, start_date, end_date, interval=interval)

    # Build recommendation
    imported_res = result["results"].get(imported_algo_id, {})
    imported_metrics = imported_res.get("metrics", {})

    recommendations = []

    if imported_metrics.get("win_rate", 0) > 70:
        recommendations.append("High win rate — check for overfitting or binary model.")
    if imported_metrics.get("final_pnl", 0) > 500_000:
        recommendations.append("Very high P&L — verify position sizing and lot size.")
    if imported_metrics.get("max_drawdown", 0) < -100_000:
        recommendations.append("Large drawdown — consider adding stop loss.")
    if imported_metrics.get("sharpe", 0) < 0:
        recommendations.append("Negative Sharpe — strategy underperforms risk-free rate.")
    if not recommendations:
        recommendations.append("Metrics look reasonable. Proceed to paper trading for live validation.")

    print(f"\n{'Recommendations':}")
    for r in recommendations:
        print(f"  • {r}")

    return {
        "imported_algo_id": imported_algo_id,
        "baseline_algos": baseline_algos,
        "start_date": start_date,
        "end_date": end_date,
        "interval": interval,
        "comparison": result,
        "recommendations": recommendations,
    }


def quick_compare_last_month(imported_algo_id: str) -> Dict[str, Any]:
    """Convenience: compare imported algo against baseline for last 30 days."""
    today = datetime.now()
    start = (today - timedelta(days=30)).strftime("%Y-%m-%d")
    end = today.strftime("%Y-%m-%d")
    return compare_imported(imported_algo_id, start, end, interval="1d")


def quick_compare_last_year(imported_algo_id: str) -> Dict[str, Any]:
    """Convenience: compare for last 365 days."""
    today = datetime.now()
    start = (today - timedelta(days=365)).strftime("%Y-%m-%d")
    end = today.strftime("%Y-%m-%d")
    return compare_imported(imported_algo_id, start, end, interval="1d")
