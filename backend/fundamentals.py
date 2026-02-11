"""
Fundamentals Module for LLM Council

Provides comprehensive fundamental data for LLM agents to interpret.
All data is fetched via yfinance's Ticker.info and organized into
structured categories: Valuation, Profitability, Growth, Balance Sheet,
Dividends, Analyst Consensus, Ownership, and Meta.

Functions:
    get_enhanced_fundamentals  — Main entry: returns structured dict
    format_fundamentals_for_llm — Format dict into readable LLM context
    get_peer_tickers           — Return peer tickers in the same industry
    get_fundamental_ratios     — Backward-compatible wrapper (returns str)
"""

import yfinance as yf
from typing import Optional

from .cache_manager import cached_data


# ---------------------------------------------------------------------------
# Peer Ticker Lookup (sector / industry → representative peers)
# ---------------------------------------------------------------------------

# Major-industry → peer tickers.  Not exhaustive, but covers the sectors
# most likely to be queried.  Fallback: yfinance recommendations.
_INDUSTRY_PEERS: dict[str, list[str]] = {
    # Technology — Semiconductors
    "Semiconductors": ["NVDA", "AMD", "INTC", "AVGO", "QCOM", "TXN", "MU"],
    "Semiconductor Equipment & Materials": ["ASML", "AMAT", "LRCX", "KLAC", "TER"],
    # Technology — Software
    "Software—Infrastructure": ["MSFT", "ORCL", "CRM", "NOW", "ADBE", "PLTR"],
    "Software—Application": ["ADBE", "CRM", "INTU", "WDAY", "SHOP", "SNOW"],
    "Internet Content & Information": ["GOOGL", "META", "SNAP", "PINS", "RDDT"],
    "Internet Retail": ["AMZN", "BABA", "JD", "MELI", "SE", "SHOP"],
    # Technology — Hardware
    "Consumer Electronics": ["AAPL", "SONY", "HPQ", "DELL", "LOGI"],
    "Information Technology Services": ["ACN", "IBM", "CTSH", "INFY", "WIT"],
    # Automotive
    "Auto Manufacturers": ["TSLA", "TM", "F", "GM", "RIVN", "LCID", "NIO"],
    # Financial
    "Banks—Diversified": ["JPM", "BAC", "WFC", "C", "GS", "MS"],
    "Insurance—Diversified": ["BRK-B", "AIG", "MET", "PRU", "ALL"],
    "Capital Markets": ["GS", "MS", "SCHW", "BLK", "ICE"],
    # Healthcare
    "Drug Manufacturers—General": ["JNJ", "PFE", "MRK", "LLY", "ABBV", "NVO"],
    "Biotechnology": ["AMGN", "GILD", "REGN", "VRTX", "BIIB", "MRNA"],
    "Medical Devices": ["MDT", "ABT", "SYK", "BSX", "ISRG", "EW"],
    # Energy
    "Oil & Gas Integrated": ["XOM", "CVX", "SHEL", "TTE", "BP", "COP"],
    "Oil & Gas E&P": ["EOG", "PXD", "DVN", "FANG", "OXY"],
    # Consumer
    "Restaurants": ["MCD", "SBUX", "CMG", "YUM", "DPZ", "WING"],
    "Beverages—Non-Alcoholic": ["KO", "PEP", "MNST", "CELH"],
    "Household & Personal Products": ["PG", "CL", "KMB", "EL", "CHD"],
    "Discount Stores": ["WMT", "COST", "TGT", "DG", "DLTR"],
    # Industrials
    "Aerospace & Defense": ["BA", "LMT", "RTX", "NOC", "GD", "HII"],
    # Telecom
    "Telecom Services": ["T", "VZ", "TMUS", "AMX"],
    # Real Estate
    "REIT—Diversified": ["AMT", "PLD", "CCI", "EQIX", "SPG", "O"],
    # Utilities
    "Utilities—Regulated Electric": ["NEE", "DUK", "SO", "D", "AEP"],
}

# Broader sector fallback when industry isn't found in the dict above
_SECTOR_PEERS: dict[str, list[str]] = {
    "Technology": ["AAPL", "MSFT", "GOOGL", "META", "NVDA", "AMZN"],
    "Healthcare": ["JNJ", "UNH", "PFE", "MRK", "LLY", "ABBV"],
    "Financial Services": ["JPM", "BAC", "GS", "BRK-B", "V", "MA"],
    "Consumer Cyclical": ["AMZN", "TSLA", "HD", "NKE", "MCD", "SBUX"],
    "Consumer Defensive": ["PG", "KO", "PEP", "WMT", "COST", "CL"],
    "Energy": ["XOM", "CVX", "COP", "SLB", "EOG", "OXY"],
    "Industrials": ["CAT", "UNP", "HON", "BA", "GE", "MMM"],
    "Communication Services": ["GOOGL", "META", "DIS", "NFLX", "CMCSA"],
    "Real Estate": ["AMT", "PLD", "CCI", "EQIX", "SPG", "O"],
    "Utilities": ["NEE", "DUK", "SO", "D", "AEP", "SRE"],
    "Basic Materials": ["LIN", "APD", "ECL", "DD", "NEM", "FCX"],
}


# ---------------------------------------------------------------------------
# Helper: safe extraction from yfinance info dict
# ---------------------------------------------------------------------------

def _safe_get(info: dict, key: str, multiply: float = 1.0) -> Optional[float]:
    """
    Safely extract a numeric value from a yfinance info dict.

    Args:
        info: yfinance Ticker.info dict.
        key:  Key to look up.
        multiply: Optional multiplier (e.g. 100 to convert ratio → pct).

    Returns:
        Float value or None.
    """
    val = info.get(key)
    if val is None:
        return None
    try:
        return float(val) * multiply
    except (TypeError, ValueError):
        return None


def _fmt_large_number(value: Optional[float]) -> Optional[str]:
    """
    Format a large number into a human-readable string (e.g. $12.34B).

    Args:
        value: Numeric value or None.

    Returns:
        Formatted string or None.
    """
    if value is None:
        return None
    abs_val = abs(value)
    sign = "-" if value < 0 else ""
    if abs_val >= 1e12:
        return f"{sign}${abs_val / 1e12:.2f}T"
    if abs_val >= 1e9:
        return f"{sign}${abs_val / 1e9:.2f}B"
    if abs_val >= 1e6:
        return f"{sign}${abs_val / 1e6:.2f}M"
    return f"{sign}${abs_val:,.0f}"


# ---------------------------------------------------------------------------
# Main Data Extraction
# ---------------------------------------------------------------------------

@cached_data(ttl_seconds=3600)
def get_enhanced_fundamentals(ticker: str) -> Optional[dict]:
    """
    Fetch and organize comprehensive fundamental data for a ticker.

    Uses yfinance Ticker.info to extract valuation, profitability, growth,
    balance-sheet health, dividend, analyst consensus, ownership, and meta.

    Args:
        ticker: Stock ticker symbol (e.g. "NVDA").

    Returns:
        Structured dict with category sub-dicts, or None on failure.
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        if not info or info.get("quoteType") is None:
            return None

        # ── VALUATION ──────────────────────────────────────────────────
        valuation = {
            "pe_trailing": _safe_get(info, "trailingPE"),
            "pe_forward": _safe_get(info, "forwardPE"),
            "peg_ratio": _safe_get(info, "pegRatio"),
            "price_to_book": _safe_get(info, "priceToBook"),
            "price_to_sales": _safe_get(info, "priceToSalesTrailing12Months"),
            "ev_to_ebitda": _safe_get(info, "enterpriseToEbitda"),
            "ev_to_revenue": _safe_get(info, "enterpriseToRevenue"),
        }

        # ── PROFITABILITY ──────────────────────────────────────────────
        profitability = {
            "gross_margin": _safe_get(info, "grossMargins", 100),
            "operating_margin": _safe_get(info, "operatingMargins", 100),
            "net_margin": _safe_get(info, "profitMargins", 100),
            "roe": _safe_get(info, "returnOnEquity", 100),
            "roa": _safe_get(info, "returnOnAssets", 100),
        }

        # ── GROWTH ─────────────────────────────────────────────────────
        growth = {
            "revenue_growth": _safe_get(info, "revenueGrowth", 100),
            "earnings_growth": _safe_get(info, "earningsGrowth", 100),
            "earnings_quarterly_growth": _safe_get(info, "earningsQuarterlyGrowth", 100),
        }

        # ── BALANCE SHEET ──────────────────────────────────────────────
        balance_sheet = {
            "total_debt": _safe_get(info, "totalDebt"),
            "total_cash": _safe_get(info, "totalCash"),
            "debt_to_equity": _safe_get(info, "debtToEquity"),
            "current_ratio": _safe_get(info, "currentRatio"),
            "free_cash_flow": _safe_get(info, "freeCashflow"),
        }

        # ── DIVIDENDS ─────────────────────────────────────────────────
        dividends = {
            "dividend_yield": _safe_get(info, "dividendYield", 100),
            "payout_ratio": _safe_get(info, "payoutRatio", 100),
        }

        # ── ANALYST ────────────────────────────────────────────────────
        analyst = {
            "target_high": _safe_get(info, "targetHighPrice"),
            "target_low": _safe_get(info, "targetLowPrice"),
            "target_mean": _safe_get(info, "targetMeanPrice"),
            "recommendation_key": info.get("recommendationKey"),
            "num_analysts": _safe_get(info, "numberOfAnalystOpinions"),
        }

        # ── OWNERSHIP ─────────────────────────────────────────────────
        ownership = {
            "short_ratio": _safe_get(info, "shortRatio"),
            "short_pct_float": _safe_get(info, "shortPercentOfFloat", 100),
            "insider_pct_held": _safe_get(info, "heldPercentInsiders", 100),
            "institution_pct_held": _safe_get(info, "heldPercentInstitutions", 100),
        }

        # ── META ───────────────────────────────────────────────────────
        market_cap_raw = _safe_get(info, "marketCap")
        next_earnings = info.get("earningsTimestamp")
        # Convert Unix timestamp to date string if present
        next_earnings_str = None
        if next_earnings:
            try:
                from datetime import datetime
                next_earnings_str = datetime.fromtimestamp(next_earnings).strftime("%Y-%m-%d")
            except Exception:
                next_earnings_str = None

        meta = {
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "market_cap": market_cap_raw,
            "market_cap_fmt": _fmt_large_number(market_cap_raw),
            "next_earnings_date": next_earnings_str,
            "name": info.get("shortName") or info.get("longName"),
            "currency": info.get("currency", "USD"),
        }

        return {
            "ticker": ticker,
            "valuation": valuation,
            "profitability": profitability,
            "growth": growth,
            "balance_sheet": balance_sheet,
            "dividends": dividends,
            "analyst": analyst,
            "ownership": ownership,
            "meta": meta,
        }

    except Exception as e:
        print(f"[FUNDAMENTALS] Error fetching data for {ticker}: {e}")
        return None


# ---------------------------------------------------------------------------
# Peer Ticker Lookup
# ---------------------------------------------------------------------------

def get_peer_tickers(ticker: str, max_peers: int = 5) -> list[str]:
    """
    Return peer tickers in the same industry/sector.

    Strategy:
    1. Look up ticker's industry via yfinance → match against _INDUSTRY_PEERS.
    2. Fallback: match against _SECTOR_PEERS.
    3. Always excludes the query ticker itself from the result list.

    Args:
        ticker: Stock ticker symbol.
        max_peers: Maximum number of peers to return (default 5).

    Returns:
        List of peer ticker strings (may be empty).
    """
    ticker_upper = ticker.upper()
    try:
        stock = yf.Ticker(ticker)
        info = stock.info or {}

        industry = info.get("industry", "")
        sector = info.get("sector", "")

        # 1. Try exact industry match
        if industry and industry in _INDUSTRY_PEERS:
            peers = [t for t in _INDUSTRY_PEERS[industry] if t != ticker_upper]
            return peers[:max_peers]

        # 2. Fallback: sector match
        if sector and sector in _SECTOR_PEERS:
            peers = [t for t in _SECTOR_PEERS[sector] if t != ticker_upper]
            return peers[:max_peers]

        return []

    except Exception as e:
        print(f"[FUNDAMENTALS] Error finding peers for {ticker}: {e}")
        return []


# ---------------------------------------------------------------------------
# LLM Formatter
# ---------------------------------------------------------------------------

def format_fundamentals_for_llm(data: dict) -> str:
    """
    Format the enhanced fundamentals dict into a categorised, readable string
    for inclusion in LLM context.

    Adds interpretive labels where meaningful (e.g. P/E vs typical range,
    debt health, margin quality, analyst consensus).

    Args:
        data: Dict returned by get_enhanced_fundamentals().

    Returns:
        Multi-line formatted string, or empty string if data is None/empty.
    """
    if not data:
        return ""

    ticker = data.get("ticker", "???")
    lines: list[str] = []
    lines.append(f"--- FUNDAMENTALS: {ticker} ---")

    na = "N/A"

    def _f(val, fmt: str = ".2f", suffix: str = "") -> str:
        """Format a value, returning 'N/A' if None."""
        if val is None:
            return na
        try:
            return f"{val:{fmt}}{suffix}"
        except (TypeError, ValueError):
            return str(val)

    # ── META ───────────────────────────────────────────────────────────
    meta = data.get("meta", {})
    meta_parts: list[str] = []
    name = meta.get("name")
    if name:
        meta_parts.append(name)
    sector = meta.get("sector")
    industry = meta.get("industry")
    if sector:
        si = f"{sector}"
        if industry:
            si += f" / {industry}"
        meta_parts.append(si)
    mcap = meta.get("market_cap_fmt")
    if mcap:
        meta_parts.append(f"Mkt Cap: {mcap}")
    ne = meta.get("next_earnings_date")
    if ne:
        meta_parts.append(f"Next Earnings: {ne}")
    if meta_parts:
        lines.append(f"  {' | '.join(meta_parts)}")

    # ── VALUATION ──────────────────────────────────────────────────────
    val = data.get("valuation", {})
    val_tokens: list[str] = []

    pe_t = val.get("pe_trailing")
    pe_label = ""
    if pe_t is not None:
        if pe_t < 0:
            pe_label = " (NEGATIVE EARNINGS)"
        elif pe_t > 50:
            pe_label = " (HIGH)"
        elif pe_t < 15:
            pe_label = " (LOW)"
    val_tokens.append(f"P/E: {_f(pe_t)}{pe_label}")

    pe_fw = val.get("pe_forward")
    val_tokens.append(f"Fwd P/E: {_f(pe_fw)}")

    peg = val.get("peg_ratio")
    peg_label = ""
    if peg is not None:
        if peg < 1.0:
            peg_label = " (UNDERVALUED)"
        elif peg > 2.0:
            peg_label = " (EXPENSIVE)"
        else:
            peg_label = " (FAIR)"
    val_tokens.append(f"PEG: {_f(peg)}{peg_label}")

    val_tokens.append(f"P/B: {_f(val.get('price_to_book'))}")
    val_tokens.append(f"P/S: {_f(val.get('price_to_sales'))}")
    val_tokens.append(f"EV/EBITDA: {_f(val.get('ev_to_ebitda'))}")
    val_tokens.append(f"EV/Rev: {_f(val.get('ev_to_revenue'))}")

    lines.append("[VALUATION]")
    # Split into two lines for readability
    lines.append(f"  {' | '.join(val_tokens[:4])}")
    if val_tokens[4:]:
        lines.append(f"  {' | '.join(val_tokens[4:])}")

    # ── PROFITABILITY ──────────────────────────────────────────────────
    prof = data.get("profitability", {})
    prof_tokens: list[str] = []

    gm = prof.get("gross_margin")
    prof_tokens.append(f"Gross: {_f(gm, '.1f', '%')}")

    om = prof.get("operating_margin")
    om_label = ""
    if om is not None:
        if om > 25:
            om_label = " (STRONG)"
        elif om < 10:
            om_label = " (THIN)"
    prof_tokens.append(f"Operating: {_f(om, '.1f', '%')}{om_label}")

    prof_tokens.append(f"Net: {_f(prof.get('net_margin'), '.1f', '%')}")

    roe = prof.get("roe")
    roe_label = ""
    if roe is not None:
        if roe > 20:
            roe_label = " (EXCELLENT)"
        elif roe < 5:
            roe_label = " (WEAK)"
    prof_tokens.append(f"ROE: {_f(roe, '.1f', '%')}{roe_label}")

    prof_tokens.append(f"ROA: {_f(prof.get('roa'), '.1f', '%')}")

    lines.append("[PROFITABILITY]")
    lines.append(f"  {' | '.join(prof_tokens)}")

    # ── GROWTH ─────────────────────────────────────────────────────────
    gr = data.get("growth", {})
    gr_tokens: list[str] = []

    rg = gr.get("revenue_growth")
    rg_label = ""
    if rg is not None:
        if rg > 25:
            rg_label = " (HIGH GROWTH)"
        elif rg < 0:
            rg_label = " (DECLINING)"
    gr_tokens.append(f"Revenue: {_f(rg, '+.1f', '%')}{rg_label}")

    eg = gr.get("earnings_growth")
    gr_tokens.append(f"Earnings: {_f(eg, '+.1f', '%')}")

    eqg = gr.get("earnings_quarterly_growth")
    gr_tokens.append(f"Quarterly: {_f(eqg, '+.1f', '%')}")

    lines.append("[GROWTH]")
    lines.append(f"  {' | '.join(gr_tokens)}")

    # ── BALANCE SHEET ──────────────────────────────────────────────────
    bs = data.get("balance_sheet", {})
    bs_tokens: list[str] = []

    td = bs.get("total_debt")
    bs_tokens.append(f"Debt: {_fmt_large_number(td) or na}")

    tc = bs.get("total_cash")
    bs_tokens.append(f"Cash: {_fmt_large_number(tc) or na}")

    dte = bs.get("debt_to_equity")
    dte_label = ""
    if dte is not None:
        if dte > 200:
            dte_label = " (HIGH LEVERAGE)"
        elif dte < 50:
            dte_label = " (CONSERVATIVE)"
    bs_tokens.append(f"D/E: {_f(dte, '.1f')}{dte_label}")

    cr = bs.get("current_ratio")
    cr_label = ""
    if cr is not None:
        if cr < 1.0:
            cr_label = " (LIQUIDITY RISK)"
        elif cr > 2.0:
            cr_label = " (STRONG)"
    bs_tokens.append(f"Current Ratio: {_f(cr)}{cr_label}")

    fcf = bs.get("free_cash_flow")
    fcf_label = ""
    if fcf is not None and fcf < 0:
        fcf_label = " (CASH BURN)"
    bs_tokens.append(f"FCF: {_fmt_large_number(fcf) or na}{fcf_label}")

    lines.append("[BALANCE SHEET]")
    lines.append(f"  {' | '.join(bs_tokens[:3])}")
    if bs_tokens[3:]:
        lines.append(f"  {' | '.join(bs_tokens[3:])}")

    # ── DIVIDENDS ──────────────────────────────────────────────────────
    div = data.get("dividends", {})
    dy = div.get("dividend_yield")
    pr = div.get("payout_ratio")
    if dy is not None or pr is not None:
        div_tokens: list[str] = []
        if dy is not None:
            div_tokens.append(f"Yield: {dy:.2f}%")
        if pr is not None:
            pr_label = ""
            if pr > 80:
                pr_label = " (HIGH)"
            elif pr > 100:
                pr_label = " (UNSUSTAINABLE)"
            div_tokens.append(f"Payout Ratio: {pr:.1f}%{pr_label}")
        lines.append("[DIVIDENDS]")
        lines.append(f"  {' | '.join(div_tokens)}")

    # ── ANALYST ────────────────────────────────────────────────────────
    an = data.get("analyst", {})
    an_tokens: list[str] = []

    rec = an.get("recommendation_key")
    if rec:
        an_tokens.append(f"Consensus: {rec.upper()}")

    tm = an.get("target_mean")
    tl = an.get("target_low")
    th = an.get("target_high")
    if tm is not None:
        target_str = f"Target: ${tm:.2f}"
        if tl is not None and th is not None:
            target_str += f" (${tl:.2f} – ${th:.2f})"
        an_tokens.append(target_str)

    na_count = an.get("num_analysts")
    if na_count is not None:
        an_tokens.append(f"Analysts: {int(na_count)}")

    if an_tokens:
        lines.append("[ANALYST CONSENSUS]")
        lines.append(f"  {' | '.join(an_tokens)}")

    # ── OWNERSHIP ──────────────────────────────────────────────────────
    own = data.get("ownership", {})
    own_tokens: list[str] = []

    inst = own.get("institution_pct_held")
    if inst is not None:
        own_tokens.append(f"Institutional: {inst:.1f}%")

    ins = own.get("insider_pct_held")
    if ins is not None:
        own_tokens.append(f"Insider: {ins:.1f}%")

    sr = own.get("short_ratio")
    if sr is not None:
        own_tokens.append(f"Short Ratio: {sr:.2f}")

    spf = own.get("short_pct_float")
    spf_label = ""
    if spf is not None:
        if spf > 20:
            spf_label = " (HIGH SHORT INTEREST)"
        elif spf > 10:
            spf_label = " (ELEVATED)"
        own_tokens.append(f"Short Float: {spf:.1f}%{spf_label}")

    if own_tokens:
        lines.append("[OWNERSHIP]")
        lines.append(f"  {' | '.join(own_tokens)}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Backward-Compatible Wrapper
# ---------------------------------------------------------------------------

def get_fundamental_ratios(ticker: str) -> str:
    """
    Backward-compatible wrapper: fetches enhanced fundamentals and returns
    a formatted string for the LLM context.

    Args:
        ticker: Stock ticker symbol.

    Returns:
        Formatted fundamentals string, or empty string on failure.
    """
    data = get_enhanced_fundamentals(ticker)
    if not data:
        return ""
    return format_fundamentals_for_llm(data)
