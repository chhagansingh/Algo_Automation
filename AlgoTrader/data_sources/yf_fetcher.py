"""
yfinance wrapper with custom timeframe support.

yfinance intraday limits (free tier):
  1m  : 7 days
  2m  : 60 days
  5m  : 60 days
  15m : 60 days
  30m : 60 days
  60m : 730 days (~2 years)
  1d  : unlimited

For intraday intervals, we auto-chunk requests if date range exceeds limits.
"""
import logging
from typing import Optional
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

# yfinance free-tier intraday limits (in days)
INTRADAY_LIMITS = {
    "1m": 7,
    "2m": 60,
    "5m": 60,
    "15m": 60,
    "30m": 60,
    "60m": 730,
    "1h": 730,
}

VALID_INTERVALS = ["1m", "2m", "5m", "15m", "30m", "60m", "1h", "1d", "1wk", "1mo"]


def _chunk_date_range(start: str, end: str, interval: str) -> list[tuple[str, str]]:
    """Split date range into chunks that fit yfinance intraday limits."""
    if interval in ("1d", "1wk", "1mo"):
        return [(start, end)]

    limit_days = INTRADAY_LIMITS.get(interval, 60)
    s = datetime.strptime(start, "%Y-%m-%d")
    e = datetime.strptime(end, "%Y-%m-%d")
    chunks = []
    cur = s
    while cur < e:
        chunk_end = min(cur + timedelta(days=limit_days - 1), e)
        chunks.append((cur.strftime("%Y-%m-%d"), chunk_end.strftime("%Y-%m-%d")))
        cur = chunk_end + timedelta(days=1)
    return chunks


def fetch_nifty_data(
    start_date: str,
    end_date: str,
    interval: str = "1d",
    ticker: str = "^NSEI",
) -> pd.DataFrame:
    """
    Fetch Nifty data from yfinance with custom interval.

    Parameters
    ----------
    start_date, end_date : YYYY-MM-DD
    interval : one of VALID_INTERVALS
    ticker : default ^NSEI (Nifty 50 index)

    Returns
    -------
    DataFrame with columns [Open, High, Low, Close, Volume] and DatetimeIndex.
    """
    if interval not in VALID_INTERVALS:
        raise ValueError(f"Invalid interval '{interval}'. Choose from: {VALID_INTERVALS}")

    chunks = _chunk_date_range(start_date, end_date, interval)
    frames = []

    for s, e in chunks:
        try:
            df = yf.download(ticker, start=s, end=e, interval=interval, progress=False)
            if not df.empty:
                frames.append(df)
        except Exception as exc:
            logger.warning("yfinance chunk %s → %s failed: %s", s, e, exc)

    if not frames:
        return pd.DataFrame()

    data = pd.concat(frames)
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = [c[0] for c in data.columns]
    data = data[["Open", "High", "Low", "Close", "Volume"]].dropna()
    data.index = pd.to_datetime(data.index)
    # Remove duplicates
    data = data[~data.index.duplicated(keep="first")]
    data = data.sort_index()
    return data


def fetch_live_spot_yf() -> Optional[float]:
    """Fetch current Nifty spot via yfinance (fallback if NSE fails)."""
    try:
        ticker = yf.Ticker("^NSEI")
        info = ticker.info
        spot = info.get("regularMarketPrice") or info.get("previousClose")
        if spot:
            return float(spot)
        # Fallback to last bar
        hist = ticker.history(period="1d", interval="1m")
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
    except Exception as e:
        logger.warning("yfinance live spot fetch failed: %s", e)
    return None
