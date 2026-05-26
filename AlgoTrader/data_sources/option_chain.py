"""
Option Chain Parser + Calculator
Parses NSE option chain response and computes:
  - ATM strike
  - PCR (OI-based, Volume-based)
  - Max Pain
  - Support / Resistance zones from OI clusters
  - Market bias
  - Real IV from ATM options
"""
import math
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

import logging

logger = logging.getLogger(__name__)


@dataclass
class StrikeData:
    strike: float
    ce_oi: int = 0
    ce_oi_change: int = 0
    ce_volume: int = 0
    ce_iv: float = 0.0
    ce_ltp: float = 0.0
    ce_ltp_change: float = 0.0
    ce_ltp_change_pct: float = 0.0
    ce_buy_qty: int = 0
    ce_sell_qty: int = 0
    pe_oi: int = 0
    pe_oi_change: int = 0
    pe_volume: int = 0
    pe_iv: float = 0.0
    pe_ltp: float = 0.0
    pe_ltp_change: float = 0.0
    pe_ltp_change_pct: float = 0.0
    pe_buy_qty: int = 0
    pe_sell_qty: int = 0
    strike_pcr: float = 0.0


@dataclass
class Greeks:
    delta: float = 0.0
    gamma: float = 0.0
    theta: float = 0.0
    vega: float = 0.0
    rho: float = 0.0


@dataclass
class ChainSummary:
    spot_price: float
    atm_strike: float
    expiry: str
    pcr_oi: float
    pcr_volume: float
    max_pain: float
    total_ce_oi: int
    total_pe_oi: int
    total_ce_vol: int
    total_pe_vol: int
    market_bias: str
    atm_ce_iv: float = 0.0
    atm_pe_iv: float = 0.0
    avg_iv: float = 0.0
    support_zones: List[float] = field(default_factory=list)
    resistance_zones: List[float] = field(default_factory=list)


# ── Core Calculations ────────────────────────────────────────────

def find_atm_strike(spot_price: float, strikes: List[float]) -> float:
    if not strikes:
        return round(spot_price / 50) * 50
    return min(strikes, key=lambda s: abs(s - spot_price))


def calculate_pcr(strikes: List[StrikeData]) -> tuple[float, float]:
    total_ce_oi = sum(s.ce_oi for s in strikes)
    total_pe_oi = sum(s.pe_oi for s in strikes)
    total_ce_vol = sum(s.ce_volume for s in strikes)
    total_pe_vol = sum(s.pe_volume for s in strikes)

    pcr_oi = round(total_pe_oi / total_ce_oi, 4) if total_ce_oi > 0 else 0.0
    pcr_volume = round(total_pe_vol / total_ce_vol, 4) if total_ce_vol > 0 else 0.0
    return pcr_oi, pcr_volume


def calculate_max_pain(strikes: List[StrikeData]) -> float:
    if not strikes:
        return 0.0
    strike_prices = [s.strike for s in strikes]
    min_pain = float('inf')
    max_pain_strike = strike_prices[0]

    for candidate in strike_prices:
        ce_pain = sum(max(0.0, s.strike - candidate) * s.ce_oi for s in strikes)
        pe_pain = sum(max(0.0, candidate - s.strike) * s.pe_oi for s in strikes)
        total_pain = ce_pain + pe_pain
        if total_pain < min_pain:
            min_pain = total_pain
            max_pain_strike = candidate
    return max_pain_strike


def find_support_resistance(
    strikes: List[StrikeData],
    atm_strike: float,
    top_n: int = 3,
) -> tuple[List[float], List[float]]:
    above_atm = [s for s in strikes if s.strike > atm_strike]
    below_atm = [s for s in strikes if s.strike < atm_strike]

    resistance = sorted(above_atm, key=lambda s: s.ce_oi, reverse=True)[:top_n]
    support = sorted(below_atm, key=lambda s: s.pe_oi, reverse=True)[:top_n]

    resistance_levels = sorted([s.strike for s in resistance])
    support_levels = sorted([s.strike for s in support], reverse=True)
    return support_levels, resistance_levels


def interpret_pcr(pcr: float) -> str:
    if pcr >= 1.5:
        return "Strongly Bullish"
    elif pcr >= 1.2:
        return "Bullish"
    elif pcr >= 0.9:
        return "Neutral"
    elif pcr >= 0.7:
        return "Bearish"
    else:
        return "Strongly Bearish"


def classify_moneyness(strike: float, spot: float, option_type: str) -> str:
    diff_pct = abs(strike - spot) / spot * 100
    if diff_pct <= 0.5:
        return "ATM"
    if option_type.upper() == "CE":
        return "ITM" if strike < spot else "OTM"
    else:
        return "ITM" if strike > spot else "OTM"


def summarise_chain(
    spot_price: float,
    expiry: str,
    strikes: List[StrikeData],
) -> ChainSummary:
    if not strikes:
        raise ValueError("No strike data provided")

    strike_prices = [s.strike for s in strikes]
    atm_strike = find_atm_strike(spot_price, strike_prices)
    pcr_oi, pcr_volume = calculate_pcr(strikes)
    max_pain = calculate_max_pain(strikes)
    support, resistance = find_support_resistance(strikes, atm_strike)

    # Per-strike PCR
    for s in strikes:
        s.strike_pcr = round(s.pe_oi / s.ce_oi, 4) if s.ce_oi > 0 else 0.0

    total_ce_oi = sum(s.ce_oi for s in strikes)
    total_pe_oi = sum(s.pe_oi for s in strikes)
    total_ce_vol = sum(s.ce_volume for s in strikes)
    total_pe_vol = sum(s.pe_volume for s in strikes)

    # ATM IV
    atm_ce_iv = 0.0
    atm_pe_iv = 0.0
    iv_count = 0
    iv_sum = 0.0
    for s in strikes:
        if abs(s.strike - atm_strike) < 1:
            atm_ce_iv = s.ce_iv
            atm_pe_iv = s.pe_iv
        if s.ce_iv > 0:
            iv_sum += s.ce_iv
            iv_count += 1
        if s.pe_iv > 0:
            iv_sum += s.pe_iv
            iv_count += 1

    avg_iv = round(iv_sum / iv_count, 4) if iv_count > 0 else 0.0

    return ChainSummary(
        spot_price=spot_price,
        atm_strike=atm_strike,
        expiry=expiry,
        pcr_oi=pcr_oi,
        pcr_volume=pcr_volume,
        max_pain=max_pain,
        total_ce_oi=total_ce_oi,
        total_pe_oi=total_pe_oi,
        total_ce_vol=total_ce_vol,
        total_pe_vol=total_pe_vol,
        market_bias=interpret_pcr(pcr_oi),
        atm_ce_iv=atm_ce_iv,
        atm_pe_iv=atm_pe_iv,
        avg_iv=avg_iv,
        support_zones=support,
        resistance_zones=resistance,
    )


# ── Black-Scholes with Real IV ───────────────────────────────────

def bs_price(spot: float, strike: float, days: float, sigma: float, opt: str = "CE", r: float = 0.07) -> float:
    """Black-Scholes option price. sigma = IV (decimal, e.g. 0.15 for 15%)."""
    if sigma <= 0 or days <= 0:
        return max(0.0, spot - strike) if opt == "CE" else max(0.0, strike - spot)
    from scipy.stats import norm
    t = days / 365.0
    d1 = (math.log(spot / strike) + (r + 0.5 * sigma ** 2) * t) / (sigma * math.sqrt(t))
    d2 = d1 - sigma * math.sqrt(t)
    if opt == "CE":
        return max(0.0, spot * norm.cdf(d1) - strike * math.exp(-r * t) * norm.cdf(d2))
    return max(0.0, strike * math.exp(-r * t) * norm.cdf(-d2) - spot * norm.cdf(-d1))


def bs_greeks(spot: float, strike: float, days: float, sigma: float, opt: str = "CE", r: float = 0.07) -> Greeks:
    """Compute Black-Scholes Greeks."""
    from scipy.stats import norm
    t = days / 365.0
    if sigma <= 0 or t <= 0:
        return Greeks()

    d1 = (math.log(spot / strike) + (r + 0.5 * sigma ** 2) * t) / (sigma * math.sqrt(t))
    d2 = d1 - sigma * math.sqrt(t)
    nd1 = norm.pdf(d1)
    N_d1 = norm.cdf(d1)
    N_md1 = norm.cdf(-d1)
    N_d2 = norm.cdf(d2)
    N_md2 = norm.cdf(-d2)

    if opt == "CE":
        delta = N_d1
        theta = (-(spot * nd1 * sigma) / (2 * math.sqrt(t))
                 - r * strike * math.exp(-r * t) * N_d2) / 365.0
        rho = strike * t * math.exp(-r * t) * N_d2 / 100.0
    else:
        delta = -N_md1
        theta = (-(spot * nd1 * sigma) / (2 * math.sqrt(t))
                 + r * strike * math.exp(-r * t) * N_md2) / 365.0
        rho = -strike * t * math.exp(-r * t) * N_md2 / 100.0

    gamma = nd1 / (spot * sigma * math.sqrt(t))
    vega = spot * nd1 * math.sqrt(t) / 100.0

    return Greeks(delta=round(delta, 4), gamma=round(gamma, 4),
                  theta=round(theta, 4), vega=round(vega, 4), rho=round(rho, 4))


# ── Synthetic Option Chain Generator ─────────────────────────────

def generate_synthetic_chain(
    spot: float,
    vix: Optional[float] = None,
    days_to_expiry: int = 3,
    strike_count: int = 10,
    strike_step: int = 50,
) -> tuple[List[StrikeData], ChainSummary]:
    """
    Generate a synthetic option chain when NSE API is unavailable.
    Uses Black-Scholes with VIX-derived IV for realistic premiums.
    OI is estimated based on strike distance from ATM (higher OI near ATM).
    """
    iv = (vix / 100.0) if vix and vix > 0 else 0.13
    atm = round(spot / strike_step) * strike_step
    expiry = (datetime.now() + timedelta(days=days_to_expiry)).strftime("%d-%b-%Y")

    strikes: List[StrikeData] = []
    for i in range(-strike_count, strike_count + 1):
        strike = atm + (i * strike_step)
        dte = max(days_to_expiry, 0.1)

        # Synthetic OI: Gaussian around ATM
        distance = abs(strike - spot) / spot
        oi_base = int(50000 * math.exp(-distance * 20)) + 1000

        # BS price
        ce_price = bs_price(spot, strike, dte, iv, "CE")
        pe_price = bs_price(spot, strike, dte, iv, "PE")

        # OI skew: more CE OI above spot, more PE OI below
        ce_oi = int(oi_base * (1.2 if strike > spot else 0.8))
        pe_oi = int(oi_base * (0.8 if strike > spot else 1.2))

        sd = StrikeData(
            strike=float(strike),
            ce_oi=ce_oi,
            ce_oi_change=int(ce_oi * 0.05),
            ce_volume=int(ce_oi * 0.1),
            ce_iv=iv,
            ce_ltp=round(ce_price, 2),
            ce_ltp_change=round(ce_price * 0.02, 2),
            ce_ltp_change_pct=2.0,
            ce_buy_qty=int(ce_oi * 0.3),
            ce_sell_qty=int(ce_oi * 0.7),
            pe_oi=pe_oi,
            pe_oi_change=int(pe_oi * 0.05),
            pe_volume=int(pe_oi * 0.1),
            pe_iv=iv,
            pe_ltp=round(pe_price, 2),
            pe_ltp_change=round(pe_price * 0.02, 2),
            pe_ltp_change_pct=2.0,
            pe_buy_qty=int(pe_oi * 0.3),
            pe_sell_qty=int(pe_oi * 0.7),
        )
        strikes.append(sd)

    strikes.sort(key=lambda s: s.strike)
    summary = summarise_chain(spot, expiry, strikes)
    return strikes, summary


# ── Parser ───────────────────────────────────────────────────────

class OptionChainParser:
    """Parse raw NSE option chain JSON into structured StrikeData + ChainSummary."""

    @staticmethod
    def parse(raw: Dict[str, Any]) -> tuple[List[StrikeData], Optional[ChainSummary]]:
        """
        Parse NSE option chain response.
        Returns (strikes_list, chain_summary) or ([], None) on failure.
        """
        if not raw:
            return [], None

        records = raw.get("records", {})
        data = records.get("data", [])
        if not data:
            return [], None

        # Extract underlying value and expiry
        underlying = float(records.get("underlyingValue", raw.get("underlyingValue", 0)))
        expiry = records.get("expiryDate", raw.get("expiryDate", ""))

        strikes: List[StrikeData] = []
        for item in data:
            strike_price = item.get("strikePrice", 0)
            if strike_price == 0:
                continue

            ce = item.get("CE", {}) or {}
            pe = item.get("PE", {}) or {}

            sd = StrikeData(
                strike=float(strike_price),
                ce_oi=int(ce.get("openInterest", 0) or 0),
                ce_oi_change=int(ce.get("changeinOpenInterest", 0) or 0),
                ce_volume=int(ce.get("totalTradedVolume", 0) or 0),
                ce_iv=float(ce.get("impliedVolatility", 0) or 0) / 100.0 if ce.get("impliedVolatility") else 0.0,
                ce_ltp=float(ce.get("lastPrice", 0) or 0),
                ce_ltp_change=float(ce.get("change", 0) or 0),
                ce_ltp_change_pct=float(ce.get("pChange", 0) or 0),
                ce_buy_qty=int(ce.get("totalBuyQuantity", 0) or 0),
                ce_sell_qty=int(ce.get("totalSellQuantity", 0) or 0),
                pe_oi=int(pe.get("openInterest", 0) or 0),
                pe_oi_change=int(pe.get("changeinOpenInterest", 0) or 0),
                pe_volume=int(pe.get("totalTradedVolume", 0) or 0),
                pe_iv=float(pe.get("impliedVolatility", 0) or 0) / 100.0 if pe.get("impliedVolatility") else 0.0,
                pe_ltp=float(pe.get("lastPrice", 0) or 0),
                pe_ltp_change=float(pe.get("change", 0) or 0),
                pe_ltp_change_pct=float(pe.get("pChange", 0) or 0),
                pe_buy_qty=int(pe.get("totalBuyQuantity", 0) or 0),
                pe_sell_qty=int(pe.get("totalSellQuantity", 0) or 0),
            )
            strikes.append(sd)

        if not strikes:
            return [], None

        # Sort by strike
        strikes.sort(key=lambda s: s.strike)

        try:
            summary = summarise_chain(underlying, expiry, strikes)
        except Exception as e:
            logger.warning("Chain summary failed: %s", e)
            summary = None

        return strikes, summary
