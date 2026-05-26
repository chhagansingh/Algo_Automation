"""
AlgoTrader — Daily Algo Logger
================================
Every algo gets its own daily log file:
  logs/algo1/YYYY-MM-DD.log
  logs/algo2/YYYY-MM-DD.log
  logs/algo3/YYYY-MM-DD.log

Granularity: full session trace — signal checks, trade entries/exits,
reasons for no-trade, market context (spot, indicators, regime).
This is the source of truth for validating CSV / dashboard data.
"""
import os
import logging
from datetime import datetime
from typing import Any, Dict

# ── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGS_DIR = os.path.join(BASE_DIR, "logs")

_ALGO_LOGGERS: Dict[str, logging.Logger] = {}


def _get_logger(algo_id: str) -> logging.Logger:
    """Return a singleton logger for this algo (creates new one per day)."""
    # Re-create logger each call so file handler always points to today's file
    today = datetime.now().strftime("%Y-%m-%d")
    key = f"{algo_id}_{today}"

    # Remove old handler if day changed
    old = _ALGO_LOGGERS.get(algo_id)
    if old:
        for h in old.handlers[:]:
            old.removeHandler(h)
            h.close()
        del _ALGO_LOGGERS[algo_id]

    algo_logs = os.path.join(LOGS_DIR, algo_id)
    os.makedirs(algo_logs, exist_ok=True)
    log_file = os.path.join(algo_logs, f"{today}.log")

    logger = logging.getLogger(key)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    # File handler (daily rotate by filename)
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%H:%M:%S"
    )
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    _ALGO_LOGGERS[algo_id] = logger
    return logger


def log_session_start(algo_id: str, algo_name: str, session_date: str, mode: str = "paper") -> None:
    """Log the beginning of a trading session."""
    log = _get_logger(algo_id)
    log.info("=" * 72)
    log.info(f" SESSION START | {algo_name} | {session_date} | mode={mode}")
    log.info("=" * 72)


def log_session_end(algo_id: str, total_trades: int, pnl: float, status: str = "OK") -> None:
    """Log the end of a trading session."""
    log = _get_logger(algo_id)
    log.info("-" * 72)
    log.info(f" SESSION END   | trades={total_trades} | P&L=₹{pnl:,.2f} | status={status}")
    log.info("=" * 72 + "\n")


def log_market_snapshot(algo_id: str, spot: float, indicators: Dict[str, Any]) -> None:
    """Log current market snapshot before signal evaluation."""
    log = _get_logger(algo_id)
    parts = [f"spot={spot:,.2f}"]
    for k, v in indicators.items():
        parts.append(f"{k}={v}")
    log.debug(f"MARKET_SNAPSHOT | {' | '.join(parts)}")


def log_signal_check(
    algo_id: str,
    signal: str,
    eligible: bool,
    reason: str,
    context: Dict[str, Any] = None,
    timestamp: str = None,
) -> None:
    """Log a signal evaluation — whether it passed or was rejected."""
    log = _get_logger(algo_id)
    ts = timestamp or datetime.now().strftime("%H:%M:%S")
    if eligible:
        log.info(f"SIGNAL_PASS   | {ts} | {signal} | REASON={reason}")
    else:
        log.warning(f"SIGNAL_BLOCK  | {ts} | {signal} | REASON={reason}")
    if context:
        for k, v in context.items():
            log.debug(f"  {k} = {v}")


def log_trade_entry(
    algo_id: str,
    trade_id: str,
    signal: str,
    spot: float,
    strike: float,
    option_type: str,
    entry_price: float,
    entry_time: str,
    lot_size: int,
    context: Dict[str, Any] = None,
) -> None:
    """Log a successful trade entry."""
    log = _get_logger(algo_id)
    log.info(
        f"TRADE_ENTRY   | {entry_time} | ID={trade_id} | "
        f"SIGNAL={signal} | spot={spot:,.2f} | strike={strike} | "
        f"type={option_type} | entry=₹{entry_price:,.2f} | lots={lot_size}"
    )
    if context:
        for k, v in context.items():
            log.debug(f"  {k} = {v}")


def log_trade_exit(
    algo_id: str,
    trade_id: str,
    exit_time: str,
    exit_price: float,
    exit_reason: str,
    pnl: float,
    pnl_pct: float,
    context: Dict[str, Any] = None,
) -> None:
    """Log a trade exit (target hit, SL hit, signal flip, etc.)."""
    log = _get_logger(algo_id)
    level = logging.INFO if pnl >= 0 else logging.WARNING
    log.log(
        level,
        f"TRADE_EXIT    | {exit_time} | ID={trade_id} | "
        f"exit=₹{exit_price:,.2f} | reason={exit_reason} | "
        f"P&L=₹{pnl:,.2f} ({pnl_pct:+.2f}%)",
    )
    if context:
        for k, v in context.items():
            log.debug(f"  {k} = {v}")


def log_no_trade(algo_id: str, reason: str, context: Dict[str, Any] = None) -> None:
    """Log why no trade was taken (e.g., no signal, market closed)."""
    log = _get_logger(algo_id)
    log.warning(f"NO_TRADE      | REASON={reason}")
    if context:
        for k, v in context.items():
            log.debug(f"  {k} = {v}")


def log_paper_interval(algo_id: str, ist_time: str, market_open: bool, next_check: str) -> None:
    """Log paper-trading periodic check."""
    log = _get_logger(algo_id)
    if market_open:
        log.debug(f"PAPER_TICK    | {ist_time} | market=OPEN | next_check={next_check}")
    else:
        log.debug(f"PAPER_TICK    | {ist_time} | market=CLOSED | sleeping…")


def log_error(algo_id: str, msg: str, exc: Exception = None) -> None:
    """Log an error that occurred during algo execution."""
    log = _get_logger(algo_id)
    if exc:
        log.error(f"ERROR         | {msg} | exc={type(exc).__name__}: {exc}")
    else:
        log.error(f"ERROR         | {msg}")


def log_backtest_run(algo_id: str, start: str, end: str, trades: int, win_rate: float, pnl: float) -> None:
    """Log backtest completion summary."""
    log = _get_logger(algo_id)
    log.info(
        f"BACKTEST_DONE | range={start} → {end} | trades={trades} | "
        f"win_rate={win_rate:.1f}% | total_pnl=₹{pnl:,.2f}"
    )
