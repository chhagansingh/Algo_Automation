"""
AlgoTrader — Base class for all algo wrappers.
Each algo implements run_backtest() and get_live_signal().
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List


class AlgoBase(ABC):
    algo_id: str = ""
    name: str = ""

    @abstractmethod
    def run_backtest(self, start_date: str, end_date: str, interval: str = "1d") -> Dict[str, Any]:
        """
        Run backtest for given date range with optional interval.
        Parameters:
          interval: "1d", "1h", "30m", "15m", "5m", "1m" (yfinance intervals)
        Returns:
          {
            "metrics": { total_trades, wins, losses, win_rate, final_pnl,
                         roc_pct, max_drawdown, sharpe, max_consec_loss,
                         avg_win, avg_loss },
            "trades": [ { trade_id, algo_id, date, symbol, strike, option_type,
                          signal_name, entry_time, entry_price, exit_time, exit_price,
                          exit_reason, pnl, pnl_pct, lot_size, status } ],
            "monthly": { "YYYY-MM": pnl, ... },
            "equity_curve": [ { "date": "YYYY-MM-DD", "cumulative_pnl": float } ],
          }
        """
        ...

    @abstractmethod
    def get_live_signal(self, spot: float, indicators: Dict[str, float]) -> Dict[str, Any]:
        """
        Given current spot price and indicator values, return trading signal.
        Returns:
          {
            "signal": "EMA_BUY_CE" | "EMA_BUY_PE" | "SHORT_STRADDLE" | "NO_TRADE" | ...,
            "option_type": "CE" | "PE" | "BOTH" | None,
            "strike": int | None,
            "signal_cards": { card_name: value, ... },
          }
        """
        ...

    def _metrics(self, pnl_list: list, initial_capital: float) -> Dict[str, Any]:
        """Shared metrics calculator — same formula as existing backtests."""
        import numpy as np
        if not pnl_list:
            return {
                "total_trades": 0, "wins": 0, "losses": 0, "win_rate": 0.0,
                "final_pnl": 0.0, "roc_pct": 0.0, "max_drawdown": 0.0,
                "sharpe": 0.0, "max_consec_loss": 0, "avg_win": 0.0, "avg_loss": 0.0,
            }
        arr = np.array(pnl_list, dtype=float)
        cum = np.cumsum(arr)
        wins    = int((arr > 0).sum())
        losses  = int((arr < 0).sum())
        total   = len(arr)
        wr      = wins / total * 100 if total else 0
        final   = float(cum[-1])
        max_dd  = float((np.maximum.accumulate(cum) - cum).max())
        sh      = float((arr.mean() / arr.std() * np.sqrt(252))) if arr.std() > 0 else 0.0
        max_cl  = 0; cur = 0
        for v in arr:
            cur    = cur + 1 if v < 0 else 0
            max_cl = max(max_cl, cur)
        win_arr  = arr[arr > 0]
        loss_arr = arr[arr < 0]
        return {
            "total_trades":    total,
            "wins":            wins,
            "losses":          losses,
            "win_rate":        round(wr, 1),
            "final_pnl":       round(final, 0),
            "roc_pct":         round(final / initial_capital * 100, 2) if initial_capital else 0,
            "max_drawdown":    round(max_dd, 0),
            "sharpe":          round(sh, 2),
            "max_consec_loss": max_cl,
            "avg_win":         round(float(win_arr.mean()), 0) if len(win_arr) else 0.0,
            "avg_loss":        round(float(loss_arr.mean()), 0) if len(loss_arr) else 0.0,
        }

    def _monthly_breakdown(self, trades: List[Dict]) -> Dict[str, float]:
        """Group trades by YYYY-MM and sum P&L."""
        monthly: Dict[str, float] = {}
        for t in trades:
            key = str(t.get("date", ""))[:7]  # "YYYY-MM"
            if key:
                monthly[key] = round(monthly.get(key, 0.0) + float(t.get("pnl", 0)), 2)
        return dict(sorted(monthly.items()))

    def _equity_curve(self, trades: List[Dict]) -> List[Dict]:
        """Build cumulative P&L curve from trades list."""
        cum = 0.0
        curve = []
        for t in sorted(trades, key=lambda x: str(x.get("date", ""))):
            cum += float(t.get("pnl", 0))
            curve.append({"date": str(t.get("date", ""))[:10], "cumulative_pnl": round(cum, 2)})
        return curve
