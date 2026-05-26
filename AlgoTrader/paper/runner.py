"""
AlgoTrader — Paper Trading Runner (with REAL NSE Option Chain)
Simulated paper trading using live NSE data:
  - Nifty spot from NSE (accurate, no delay)
  - Option chain from NSE (real strikes, real LTP, real IV, real OI)
  - PCR, Max Pain, Support/Resistance from live chain
  - Paper positions use REAL option premiums for entry/exit P&L
"""
import time
import uuid
import threading
import pandas as pd
import yfinance as yf
from datetime import datetime, date
from typing import Dict, Any, Optional

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    ALGOS, ALGO_IDS, PAPER_INTERVAL_SECONDS,
    MARKET_OPEN_IST, MARKET_CLOSE_IST, OPTION_CHAIN_REFRESH_SECONDS
)
from storage.csv_store import (
    write_open_position, close_open_position, read_open_positions,
    write_trade, compute_and_save_daily_summary
)
from algos import get_algo
from utils.logger import (
    log_session_start, log_session_end, log_market_snapshot,
    log_signal_check, log_trade_entry, log_trade_exit,
    log_paper_interval, log_error, log_no_trade
)
from data_sources.nse_fetcher import get_nse_fetcher
from data_sources.option_chain_service import get_option_chain_service
from utils.settings_store import is_algo_reset_pending, clear_reset_flag, get_algo_settings

# ── Global state ───────────────────────────────────────────────────────────────
_runners: Dict[str, threading.Thread] = {}
_stop_flags: Dict[str, threading.Event] = {}
_status: Dict[str, bool] = {aid: False for aid in ALGO_IDS}


def paper_status(algo_id: str) -> bool:
    return _status.get(algo_id, False)


def get_all_status() -> Dict[str, Any]:
    return {
        aid: {
            "running": _status.get(aid, False),
            "algo_name": ALGOS[aid]["name"],
        }
        for aid in ALGO_IDS
    }


def _is_market_hours() -> bool:
    """Check if Indian equity market is currently open.
    NSE: Mon-Fri 09:15 IST - 15:30 IST.
    Uses explicit IST timezone via Asia/Kolkata.
    """
    try:
        from zoneinfo import ZoneInfo
        now_ist = datetime.now(ZoneInfo("Asia/Kolkata"))
    except Exception:
        now_ist = datetime.now()  # fallback to local (should already be IST)

    # Weekend check
    if now_ist.weekday() >= 5:  # Saturday=5, Sunday=6
        return False

    open_h, open_m   = 9, 15
    close_h, close_m = 15, 30
    now_minutes = now_ist.hour * 60 + now_ist.minute
    open_minutes  = open_h * 60 + open_m
    close_minutes = close_h * 60 + close_m
    return open_minutes <= now_minutes <= close_minutes


def fetch_live_market_data() -> Dict[str, Any]:
    """Fetch live Nifty spot + option chain from NSE. Returns enriched market data."""
    nse = get_nse_fetcher()
    svc = get_option_chain_service()
    result = {
        "spot": None,
        "open": None,
        "high": None,
        "low": None,
        "daily_range_pct": 0.0,
        "close_move_pct": 0.0,
        "option_chain": None,
        "chain_summary": None,
        "vix": None,
        "pcr": None,
        "source": "nse",
    }

    # 1. Nifty spot from NSE direct API (nsepython fallback inside fetcher)
    try:
        spot = nse.fetch_nifty_spot()
        if spot:
            result["spot"] = spot
    except Exception as e:
        pass

    # Fallback to yfinance
    if result["spot"] is None:
        try:
            ticker = yf.Ticker("^NSEI")
            hist = ticker.history(period="1d", interval="1m")
            if not hist.empty:
                result["spot"] = float(hist["Close"].iloc[-1])
                result["open"] = float(hist["Open"].iloc[0])
                result["high"] = float(hist["High"].max())
                result["low"] = float(hist["Low"].min())
                result["source"] = "yfinance"
        except Exception as e:
            print(f"[Paper] Both NSE and yfinance spot fetch failed: {e}")
            return result

    # Calculate daily context
    if result["open"]:
        result["daily_range_pct"] = (result["high"] - result["low"]) / result["open"] * 100
        result["close_move_pct"] = abs(result["spot"] - result["open"]) / result["open"] * 100

    # 2. Real option chain from polling service
    chain = svc.get_latest()
    if chain:
        result["option_chain"] = chain
        result["chain_summary"] = chain  # same dict, consistent naming
        result["pcr"] = chain.get("pcr")
        # Use ATM IV as VIX proxy if no direct VIX available
        ce_iv = chain.get("atm_ce", {}).get("iv", 0)
        pe_iv = chain.get("atm_pe", {}).get("iv", 0)
        avg_iv = (ce_iv + pe_iv) / 2 if ce_iv and pe_iv else ce_iv or pe_iv
        if avg_iv:
            result["vix"] = avg_iv

    return result


def _get_atm_option_prices(chain_data: Dict[str, Any]) -> tuple:
    """Return (ce_ltp, pe_ltp, ce_iv, pe_iv, atm_strike) from live chain."""
    if not chain_data:
        return None, None, None, None, None
    atm_strike = chain_data.get("atm_strike")
    atm_ce = chain_data.get("atm_ce", {})
    atm_pe = chain_data.get("atm_pe", {})
    return (
        atm_ce.get("ltp"),
        atm_pe.get("ltp"),
        atm_ce.get("iv"),
        atm_pe.get("iv"),
        atm_strike,
    )


def _get_strike_ltp(chain_data: Dict[str, Any], strike: float, opt_type: str) -> Optional[float]:
    """Look up a specific strike's LTP from the live chain."""
    if not chain_data:
        return None
    for s in chain_data.get("strikes", []):
        if s["strike"] == strike:
            return s.get(opt_type.lower(), {}).get("ltp")
    return None


def _compute_indicators(algo_id: str, spot: float, market_data: Dict) -> Dict[str, float]:
    """Compute live indicators. Uses real IV from option chain if available."""
    try:
        ticker = yf.Ticker("^NSEI")
        hist = ticker.history(period="60d", interval="1d")
        if hist.empty:
            return market_data
        close = hist["Close"]
        high = hist["High"]
        low = hist["Low"]
        ema5 = float(close.ewm(span=5, adjust=False).mean().iloc[-1])
        ema20 = float(close.ewm(span=20, adjust=False).mean().iloc[-1])
        delta = close.diff()
        gain = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
        loss = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
        rsi = float(100 - (100 / (1 + gain.iloc[-1] / max(float(loss.iloc[-1]), 1e-6))))
        tr_ = pd.concat([high-low, (high-close.shift()).abs(), (low-close.shift()).abs()], axis=1).max(axis=1)
        atr = float(tr_.rolling(14).mean().iloc[-1])
        atr_pct = atr / float(close.iloc[-1]) * 100
        adx = 20.0
        bb_w = float((close.rolling(20).mean() + 2*close.rolling(20).std() -
                      (close.rolling(20).mean() - 2*close.rolling(20).std())).iloc[-1]
                     / close.rolling(20).mean().iloc[-1] * 100)
        if atr_pct > 1.2:
            regime = "HIGH_VOLATILITY"
        elif adx >= 25 and bb_w >= 3.0:
            regime = "TRENDING"
        elif adx < 20 or bb_w < 1.5:
            regime = "RANGING"
        else:
            regime = "RANGING"

        # Inject real IV from option chain if available
        chain = market_data.get("option_chain")
        if chain:
            ce_iv = chain.get("atm_ce", {}).get("iv", 0)
            pe_iv = chain.get("atm_pe", {}).get("iv", 0)
            real_iv = (ce_iv + pe_iv) / 2 if ce_iv and pe_iv else ce_iv or pe_iv
            if real_iv:
                market_data["real_iv"] = real_iv
                market_data["vix"] = real_iv

        return {
            **market_data,
            "ema5": ema5, "ema20": ema20, "rsi": rsi,
            "adx": adx, "atr_pct": atr_pct, "regime": regime,
        }
    except Exception as e:
        print(f"[Paper] indicator compute error: {e}")
        return market_data


def _paper_loop(algo_id: str, stop_event: threading.Event):
    """Main paper trading loop for one algo."""
    _status[algo_id] = True
    print(f"[Paper] {algo_id} started")
    algo = get_algo(algo_id)
    lot_size = ALGOS[algo_id]["lot_size"]
    last_signal = None
    last_trade_date: Optional[str] = None
    session_logged_today: Optional[str] = None

    while not stop_event.is_set():
        try:
            now = datetime.now()
            today_str = now.strftime("%Y-%m-%d")
            time_str = now.strftime("%H:%M:%S")

            if not _is_market_hours():
                log_paper_interval(algo_id, time_str, market_open=False, next_check="market_open")
                stop_event.wait(300)
                continue

            # Check if algo is enabled
            algo_settings = get_algo_settings(algo_id)
            if not algo_settings.get("enabled", True):
                log_paper_interval(algo_id, time_str, market_open=True,
                                   next_check="disabled")
                stop_event.wait(PAPER_INTERVAL_SECONDS)
                continue

            if session_logged_today != today_str:
                log_session_start(algo_id, ALGOS[algo_id]["name"], today_str, mode="paper")
                session_logged_today = today_str

            # Fetch LIVE NSE data (spot + option chain + VIX + PCR)
            market_data = fetch_live_market_data()
            spot = market_data.get("spot")
            if spot is None:
                log_error(algo_id, "fetch_live_market_data returned no spot — skipping tick")
                stop_event.wait(PAPER_INTERVAL_SECONDS)
                continue

            # Check reset flag (after spot is available so we can use real price for exit)
            if is_algo_reset_pending(algo_id):
                print(f"[Paper] {algo_id} RESET requested — closing all positions")
                open_df = read_open_positions(algo_id)
                if not open_df.empty:
                    for _, pos in open_df.iterrows():
                        trade_id = pos["trade_id"]
                        entry_px = float(pos["entry_price"])
                        strike = float(pos.get("strike", 0))
                        opt_type = pos.get("option_type", "CE")
                        exit_px = spot  # reset uses current spot as exit
                        pnl = (exit_px - entry_px) * lot_size
                        close_open_position(
                            algo_id, trade_id,
                            exit_price=exit_px,
                            exit_time=now.isoformat(),
                            exit_reason="RESET"
                        )
                        log_trade_exit(
                            algo_id, trade_id, now.isoformat(), exit_px,
                            "RESET", pnl,
                            round(pnl / (entry_px * lot_size) * 100, 2) if entry_px else 0,
                            context={"reason": "user_reset", "spot": spot}
                        )
                        compute_and_save_daily_summary(algo_id, today_str)
                clear_reset_flag(algo_id)
                log_session_end(algo_id, 0, 0.0, status="RESET")
                session_logged_today = None
                print(f"[Paper] {algo_id} RESET complete — positions cleared")
                stop_event.wait(PAPER_INTERVAL_SECONDS)
                continue

            # Get real option chain data
            chain = market_data.get("option_chain")
            real_iv = chain.get("atm_ce", {}).get("iv") if chain else None
            real_vix = market_data.get("vix")
            pcr = chain.get("pcr") if chain else None
            max_pain = chain.get("max_pain_strike") if chain else None

            indicators = _compute_indicators(algo_id, spot, market_data)
            log_market_snapshot(algo_id, spot, {
                **indicators,
                "real_iv": real_iv or "N/A",
                "real_vix": real_vix or "N/A",
                "pcr_oi": pcr if pcr is not None else "N/A",
                "max_pain": max_pain if max_pain is not None else "N/A",
                "source": market_data.get("source", "unknown"),
            })

            # Generate signal
            signal_result = algo.get_live_signal(spot, indicators)
            signal = signal_result.get("signal", "NO_TRADE")
            signal_cards = signal_result.get("signal_cards", {})

            # Log signal
            if signal == "NO_TRADE":
                log_signal_check(algo_id, "ALL", False,
                                 "No qualifying signal in current market conditions",
                                 context={**signal_cards, "pcr": pcr},
                                 timestamp=time_str)
            else:
                log_signal_check(algo_id, signal, True,
                                 f"Live signal at {time_str} | PCR={pcr}",
                                 context={**signal_cards, "real_iv": real_iv, "vix": real_vix},
                                 timestamp=time_str)

            # Check open positions — close if needed
            open_df = read_open_positions(algo_id)
            if not open_df.empty:
                for _, pos in open_df.iterrows():
                    trade_id = pos["trade_id"]
                    entry_px = float(pos["entry_price"])
                    strike = float(pos.get("strike", 0))
                    opt_type = pos.get("option_type", "CE")

                    # Close at EOD (15:25) — use REAL current LTP from option chain
                    if now.hour == 15 and now.minute >= 25:
                        exit_px = _get_strike_ltp(chain, strike, opt_type) if chain else spot
                        if exit_px is None:
                            exit_px = spot  # fallback
                        pnl = (exit_px - entry_px) * lot_size
                        close_open_position(
                            algo_id, trade_id,
                            exit_price=exit_px,
                            exit_time=now.isoformat(),
                            exit_reason="EOD_CLOSE"
                        )
                        log_trade_exit(
                            algo_id, trade_id, now.isoformat(), exit_px,
                            "EOD_CLOSE", pnl,
                            round(pnl / (entry_px * lot_size) * 100, 2) if entry_px else 0,
                            context={"entry_price": entry_px, "spot": spot, "real_iv": real_iv, "exit_ltp": exit_px}
                        )
                        compute_and_save_daily_summary(algo_id, today_str)
                        log_session_end(algo_id, 1, pnl, status="EOD_CLOSE")
                        session_logged_today = None

            # Enter new position if signal and no open position for today
            open_df_refresh = read_open_positions(algo_id)
            has_open = not open_df_refresh.empty
            if signal != "NO_TRADE" and not has_open and last_trade_date != today_str:
                strike = signal_result.get("strike")
                opt_type = signal_result.get("option_type", "CE")
                tid = str(uuid.uuid4())[:8]

                # Use REAL option premium from live chain
                entry_px = None
                if chain:
                    if strike:
                        entry_px = _get_strike_ltp(chain, strike, opt_type)
                    if entry_px is None:
                        # Fallback to ATM
                        entry_px = _get_atm_option_prices(chain)[0] if opt_type == "CE" else _get_atm_option_prices(chain)[1]

                if entry_px is None:
                    entry_px = spot  # ultimate fallback

                new_pos = {
                    "trade_id": tid,
                    "algo_id": algo_id,
                    "open_time": now.isoformat(),
                    "symbol": "NIFTY",
                    "strike": strike or round(spot / 50) * 50,
                    "option_type": opt_type,
                    "signal_name": signal,
                    "entry_price": entry_px,
                    "current_ltp": entry_px,
                    "unrealized_pnl": 0.0,
                    "lot_size": lot_size,
                }
                write_open_position(new_pos)
                last_trade_date = today_str
                log_trade_entry(
                    algo_id, tid, signal, spot,
                    strike or round(spot / 50) * 50, opt_type,
                    entry_px, now.isoformat(), lot_size,
                    context={"indicators": indicators, "real_iv": real_iv, "vix": real_vix,
                             "pcr": pcr, "entry_ltp": entry_px}
                )
                print(f"[Paper] {algo_id} | ENTRY | {signal} | spot={spot} | strike={strike} | ltp={entry_px} | iv={real_iv}")

            last_signal = signal
            log_paper_interval(algo_id, time_str, market_open=True,
                               next_check=f"+{PAPER_INTERVAL_SECONDS}s")

        except Exception as e:
            log_error(algo_id, "paper loop exception", exc=e)
            print(f"[Paper] {algo_id} loop error: {e}")

        stop_event.wait(PAPER_INTERVAL_SECONDS)

    _status[algo_id] = False
    print(f"[Paper] {algo_id} stopped")


def start_paper(algo_id: str):
    """Start paper trading for an algo."""
    if _status.get(algo_id):
        return
    stop_event = threading.Event()
    _stop_flags[algo_id] = stop_event
    t = threading.Thread(target=_paper_loop, args=(algo_id, stop_event), daemon=True)
    _runners[algo_id] = t
    t.start()


def stop_paper(algo_id: str):
    """Stop paper trading for an algo."""
    if algo_id in _stop_flags:
        _stop_flags[algo_id].set()
    _status[algo_id] = False
