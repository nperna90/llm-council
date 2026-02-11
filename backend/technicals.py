"""
Technical Indicators Module for LLM Council

Pre-computes technical indicators so that LLM agents INTERPRET numbers
rather than calculate them. All indicators are computed using only pandas
and numpy — no external TA libraries required.

Functions:
    get_ohlcv_data          — Fetch OHLCV data for a single ticker
    compute_technical_indicators — Main entry point: returns dict of all indicators
    find_support_levels     — Local-minima-based support detection
    find_resistance_levels  — Local-maxima-based resistance detection
    format_technicals_for_llm — Format indicators into a readable LLM context string
"""

import numpy as np
import pandas as pd
import yfinance as yf
from typing import Optional

from .cache_manager import cached_data


# ---------------------------------------------------------------------------
# OHLCV Data Fetcher
# ---------------------------------------------------------------------------

@cached_data(ttl_seconds=3600)
def get_ohlcv_data(ticker: str, period: str = "1y") -> pd.DataFrame:
    """
    Fetch OHLCV price history for a single ticker via yfinance.

    Args:
        ticker: Stock/ETF ticker symbol (e.g. "NVDA").
        period: yfinance period string ("1y", "2y", "5y", etc.).

    Returns:
        DataFrame with columns [Open, High, Low, Close, Volume] indexed by date.
        Returns an empty DataFrame on failure.
    """
    try:
        tk = yf.Ticker(ticker)
        df = tk.history(period=period)
        if df.empty:
            return pd.DataFrame()
        # Keep only the columns we need
        required = ["Open", "High", "Low", "Close", "Volume"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            print(f"[TECHNICALS] Missing columns {missing} for {ticker}")
            return pd.DataFrame()
        return df[required].copy()
    except Exception as e:
        print(f"[TECHNICALS] Error fetching OHLCV for {ticker}: {e}")
        return pd.DataFrame()


# ---------------------------------------------------------------------------
# Private Helper Functions
# ---------------------------------------------------------------------------

def _compute_rsi(series: pd.Series, period: int = 14) -> Optional[float]:
    """
    Compute the Relative Strength Index (Wilder's smoothing).

    Args:
        series: Close price series.
        period: Look-back period (default 14).

    Returns:
        RSI value (0–100) or None if insufficient data.
    """
    if series is None or len(series) < period + 1:
        return None
    try:
        delta = series.diff()
        gains = delta.where(delta > 0, 0.0)
        losses = -delta.where(delta < 0, 0.0)

        avg_gain = gains.ewm(span=period, adjust=False).mean()
        avg_loss = losses.ewm(span=period, adjust=False).mean()

        # Guard against division by zero
        last_loss = avg_loss.iloc[-1]
        if last_loss == 0:
            return 100.0

        rs = avg_gain.iloc[-1] / last_loss
        rsi = 100.0 - (100.0 / (1.0 + rs))
        return round(float(rsi), 2)
    except Exception:
        return None


def _compute_macd(series: pd.Series,
                  fast: int = 12, slow: int = 26, signal: int = 9) -> Optional[dict]:
    """
    Compute MACD line, signal line, histogram, and crossover status.

    Args:
        series: Close price series.
        fast:   Fast EMA period (default 12).
        slow:   Slow EMA period (default 26).
        signal: Signal EMA period (default 9).

    Returns:
        Dict with macd_line, signal_line, histogram, crossover or None.
    """
    if series is None or len(series) < slow + signal:
        return None
    try:
        ema_fast = series.ewm(span=fast, adjust=False).mean()
        ema_slow = series.ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line

        # Crossover detection (compare last two bars)
        crossover = "NONE"
        if len(macd_line) >= 2 and len(signal_line) >= 2:
            prev_diff = macd_line.iloc[-2] - signal_line.iloc[-2]
            curr_diff = macd_line.iloc[-1] - signal_line.iloc[-1]
            if prev_diff <= 0 < curr_diff:
                crossover = "BULLISH"
            elif prev_diff >= 0 > curr_diff:
                crossover = "BEARISH"

        return {
            "macd_line": round(float(macd_line.iloc[-1]), 4),
            "signal_line": round(float(signal_line.iloc[-1]), 4),
            "histogram": round(float(histogram.iloc[-1]), 4),
            "crossover": crossover,
        }
    except Exception:
        return None


def _compute_stochastic(close: pd.Series, high: pd.Series,
                        low: pd.Series, period: int = 14,
                        smooth_k: int = 3) -> Optional[float]:
    """
    Compute Stochastic %K (slow, smoothed).

    Args:
        close: Close price series.
        high:  High price series.
        low:   Low price series.
        period: Look-back period (default 14).
        smooth_k: Smoothing period for %K (default 3).

    Returns:
        %K value (0–100) or None.
    """
    if close is None or len(close) < period + smooth_k:
        return None
    try:
        lowest_low = low.rolling(window=period).min()
        highest_high = high.rolling(window=period).max()

        denom = highest_high - lowest_low
        # Guard division by zero
        denom = denom.replace(0, np.nan)

        raw_k = ((close - lowest_low) / denom) * 100.0
        smooth = raw_k.rolling(window=smooth_k).mean()

        val = smooth.iloc[-1]
        if pd.isna(val):
            return None
        return round(float(val), 2)
    except Exception:
        return None


def _compute_atr(high: pd.Series, low: pd.Series,
                 close: pd.Series, period: int = 14) -> Optional[float]:
    """
    Compute Average True Range.

    Args:
        high:  High price series.
        low:   Low price series.
        close: Close price series.
        period: Look-back period (default 14).

    Returns:
        ATR value or None.
    """
    if high is None or len(high) < period + 1:
        return None
    try:
        prev_close = close.shift(1)
        tr1 = high - low
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = true_range.rolling(window=period).mean()
        val = atr.iloc[-1]
        if pd.isna(val):
            return None
        return round(float(val), 2)
    except Exception:
        return None


def _compute_bollinger(series: pd.Series,
                       period: int = 20, num_std: int = 2) -> Optional[dict]:
    """
    Compute Bollinger Bands: upper, lower, bandwidth, and %B.

    Args:
        series: Close price series.
        period: SMA period (default 20).
        num_std: Number of standard deviations (default 2).

    Returns:
        Dict with upper, lower, bandwidth, percent_b or None.
    """
    if series is None or len(series) < period:
        return None
    try:
        sma = series.rolling(window=period).mean()
        std = series.rolling(window=period).std()

        upper = sma + num_std * std
        lower = sma - num_std * std

        last_upper = float(upper.iloc[-1])
        last_lower = float(lower.iloc[-1])
        last_sma = float(sma.iloc[-1])
        last_close = float(series.iloc[-1])

        # Bandwidth = (upper - lower) / middle
        bandwidth = ((last_upper - last_lower) / last_sma * 100.0
                     if last_sma != 0 else 0.0)

        # %B = (price - lower) / (upper - lower)
        band_range = last_upper - last_lower
        percent_b = ((last_close - last_lower) / band_range
                     if band_range != 0 else 0.5)

        return {
            "upper": round(last_upper, 2),
            "lower": round(last_lower, 2),
            "bandwidth": round(bandwidth, 2),
            "percent_b": round(percent_b, 4),
        }
    except Exception:
        return None


def _compute_obv_trend(close: pd.Series, volume: pd.Series,
                       period: int = 20) -> Optional[str]:
    """
    Determine On-Balance Volume trend over the given period.

    Args:
        close:  Close price series.
        volume: Volume series.
        period: Look-back window for trend determination (default 20).

    Returns:
        "RISING" or "FALLING", or None.
    """
    if close is None or volume is None or len(close) < period + 1:
        return None
    try:
        direction = np.sign(close.diff())
        obv = (direction * volume).cumsum()

        # Compare OBV at start and end of the look-back period
        obv_recent = obv.iloc[-period:]
        if len(obv_recent) < 2:
            return None
        return "RISING" if obv_recent.iloc[-1] > obv_recent.iloc[0] else "FALLING"
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Support / Resistance Detection
# ---------------------------------------------------------------------------

def find_support_levels(df: pd.DataFrame, n: int = 3) -> list[float]:
    """
    Find support levels using local minima from the most recent 60 trading days.

    Args:
        df: OHLCV DataFrame.
        n:  Number of support levels to return.

    Returns:
        List of up to *n* support prices below the current price, sorted by
        proximity (closest first).
    """
    if df is None or df.empty or "Low" not in df.columns:
        return []
    try:
        window = df.tail(60)
        if len(window) < 5:
            return []

        lows = window["Low"]
        current_price = float(df["Close"].iloc[-1])

        # Local minimum: lower than both neighbors
        shifted_prev = lows.shift(1)
        shifted_next = lows.shift(-1)
        is_min = (lows < shifted_prev) & (lows < shifted_next)

        candidates = lows[is_min]
        below = candidates[candidates < current_price]

        # Sort by proximity to current price (closest first)
        below_sorted = below.sort_values(ascending=False)
        return [round(float(v), 2) for v in below_sorted.head(n)]
    except Exception:
        return []


def find_resistance_levels(df: pd.DataFrame, n: int = 3) -> list[float]:
    """
    Find resistance levels using local maxima from the most recent 60 trading days.

    Args:
        df: OHLCV DataFrame.
        n:  Number of resistance levels to return.

    Returns:
        List of up to *n* resistance prices above the current price, sorted by
        proximity (closest first).
    """
    if df is None or df.empty or "High" not in df.columns:
        return []
    try:
        window = df.tail(60)
        if len(window) < 5:
            return []

        highs = window["High"]
        current_price = float(df["Close"].iloc[-1])

        # Local maximum: higher than both neighbors
        shifted_prev = highs.shift(1)
        shifted_next = highs.shift(-1)
        is_max = (highs > shifted_prev) & (highs > shifted_next)

        candidates = highs[is_max]
        above = candidates[candidates > current_price]

        # Sort by proximity to current price (closest first)
        above_sorted = above.sort_values(ascending=True)
        return [round(float(v), 2) for v in above_sorted.head(n)]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------

def compute_technical_indicators(ticker: str, df: pd.DataFrame) -> Optional[dict]:
    """
    Compute a comprehensive set of technical indicators from an OHLCV DataFrame.

    Each indicator is computed independently — a failure in one does not
    prevent the others from being calculated.

    Args:
        ticker: Ticker symbol (used as label only).
        df:     OHLCV DataFrame with columns [Open, High, Low, Close, Volume].

    Returns:
        Dict of indicator values (see module docstring for full key list),
        or None if the DataFrame is empty / unusable.
    """
    if df is None or df.empty:
        return None

    try:
        close = df["Close"].dropna()
        high = df["High"].dropna()
        low = df["Low"].dropna()
        volume = df["Volume"].dropna()
    except KeyError:
        return None

    if len(close) < 2:
        return None

    current_price = float(close.iloc[-1])

    # --- 52-week range ---
    hist_52w = close.tail(252)
    high_52w = float(hist_52w.max()) if len(hist_52w) > 0 else None
    low_52w = float(hist_52w.min()) if len(hist_52w) > 0 else None
    pct_from_52w_high = (
        round((current_price - high_52w) / high_52w * 100, 2)
        if high_52w and high_52w != 0 else None
    )

    # --- Moving Averages ---
    sma_20 = round(float(close.rolling(20).mean().iloc[-1]), 2) if len(close) >= 20 else None
    sma_50 = round(float(close.rolling(50).mean().iloc[-1]), 2) if len(close) >= 50 else None
    sma_200 = round(float(close.rolling(200).mean().iloc[-1]), 2) if len(close) >= 200 else None

    ema_12 = round(float(close.ewm(span=12, adjust=False).mean().iloc[-1]), 2) if len(close) >= 12 else None
    ema_26 = round(float(close.ewm(span=26, adjust=False).mean().iloc[-1]), 2) if len(close) >= 26 else None

    # Price vs SMA200
    price_vs_sma200 = None
    if sma_200 is not None:
        price_vs_sma200 = "ABOVE" if current_price > sma_200 else "BELOW"

    # Golden / Death cross (SMA50 vs SMA200)
    golden_death_cross = "NONE"
    if len(close) >= 200:
        sma50_series = close.rolling(50).mean()
        sma200_series = close.rolling(200).mean()
        valid = sma50_series.dropna()
        valid200 = sma200_series.dropna()
        if len(valid) >= 2 and len(valid200) >= 2:
            prev_diff = valid.iloc[-2] - valid200.iloc[-2]
            curr_diff = valid.iloc[-1] - valid200.iloc[-1]
            if prev_diff <= 0 < curr_diff:
                golden_death_cross = "GOLDEN_CROSS"
            elif prev_diff >= 0 > curr_diff:
                golden_death_cross = "DEATH_CROSS"

    # --- Momentum Indicators ---
    rsi_14 = _compute_rsi(close, 14)
    macd = _compute_macd(close)
    stochastic_k = _compute_stochastic(close, high, low, 14)

    # --- Volatility ---
    atr_14 = _compute_atr(high, low, close, 14)
    bollinger = _compute_bollinger(close, 20, 2)

    # 30-day realized volatility (annualized)
    volatility_30d = None
    if len(close) >= 31:
        daily_ret = close.tail(31).pct_change().dropna()
        if len(daily_ret) > 1:
            volatility_30d = round(float(daily_ret.std() * np.sqrt(252) * 100), 2)

    # --- Volume ---
    volume_avg_20d = None
    volume_ratio = None
    if len(volume) >= 20:
        avg_vol = volume.tail(20).mean()
        if avg_vol and avg_vol > 0:
            volume_avg_20d = round(float(avg_vol), 0)
            volume_ratio = round(float(volume.iloc[-1] / avg_vol), 2)

    # --- OBV Trend ---
    obv_trend = _compute_obv_trend(close, volume, 20)

    # --- Performance Returns ---
    def _pct_return(n_days: int) -> Optional[float]:
        """Return percentage change over the last n trading days."""
        if len(close) <= n_days:
            return None
        old = float(close.iloc[-(n_days + 1)])
        if old == 0:
            return None
        return round((current_price - old) / old * 100, 2)

    return_1d = _pct_return(1)
    return_1w = _pct_return(5)
    return_1m = _pct_return(21)
    return_3m = _pct_return(63)
    return_6m = _pct_return(126)
    return_1y = _pct_return(252)

    # --- Support / Resistance ---
    support_levels = find_support_levels(df, n=3)
    resistance_levels = find_resistance_levels(df, n=3)

    # --- Assemble Result ---
    result = {
        "ticker": ticker,
        "current_price": round(current_price, 2),
        "high_52w": round(high_52w, 2) if high_52w is not None else None,
        "low_52w": round(low_52w, 2) if low_52w is not None else None,
        "pct_from_52w_high": pct_from_52w_high,
        # Moving averages
        "sma_20": sma_20,
        "sma_50": sma_50,
        "sma_200": sma_200,
        "ema_12": ema_12,
        "ema_26": ema_26,
        "price_vs_sma200": price_vs_sma200,
        "golden_death_cross": golden_death_cross,
        # Momentum
        "rsi_14": rsi_14,
        "macd_line": macd["macd_line"] if macd else None,
        "macd_signal": macd["signal_line"] if macd else None,
        "macd_histogram": macd["histogram"] if macd else None,
        "macd_crossover": macd["crossover"] if macd else None,
        "stochastic_k": stochastic_k,
        # Volatility
        "atr_14": atr_14,
        "bb_upper": bollinger["upper"] if bollinger else None,
        "bb_lower": bollinger["lower"] if bollinger else None,
        "bb_bandwidth": bollinger["bandwidth"] if bollinger else None,
        "bb_percent_b": bollinger["percent_b"] if bollinger else None,
        "volatility_30d": volatility_30d,
        # Volume
        "volume_avg_20d": volume_avg_20d,
        "volume_ratio": volume_ratio,
        "obv_trend": obv_trend,
        # Performance
        "return_1d": return_1d,
        "return_1w": return_1w,
        "return_1m": return_1m,
        "return_3m": return_3m,
        "return_6m": return_6m,
        "return_1y": return_1y,
        # Levels
        "support_levels": support_levels,
        "resistance_levels": resistance_levels,
    }

    return result


# ---------------------------------------------------------------------------
# LLM Formatter
# ---------------------------------------------------------------------------

def format_technicals_for_llm(indicators: dict) -> str:
    """
    Format a technical-indicators dict into a readable, categorised string
    suitable for inclusion in the LLM context window.

    Groups: Trend, Momentum, Volatility, Volume, Levels, Performance.
    Adds interpretive labels (e.g. "OVERBOUGHT", "BULLISH CROSSOVER").

    Args:
        indicators: Dict returned by compute_technical_indicators().

    Returns:
        Multi-line formatted string, or empty string if indicators is None.
    """
    if not indicators:
        return ""

    ticker = indicators.get("ticker", "???")
    lines: list[str] = []
    lines.append(f"--- TECHNICAL INDICATORS: {ticker} ---")

    def _v(key: str, fmt: str = ".2f", prefix: str = "", suffix: str = "") -> str:
        """Format a single indicator value, return '' if None."""
        val = indicators.get(key)
        if val is None:
            return ""
        return f"{prefix}{val:{fmt}}{suffix}"

    # ── TREND ──────────────────────────────────────────────────────────
    trend_parts: list[str] = []
    price_str = _v("current_price", ".2f", "$")
    if price_str:
        hi = _v("high_52w", ".2f", "$")
        lo = _v("low_52w", ".2f", "$")
        pct = _v("pct_from_52w_high", ".1f", suffix="%")
        trend_parts.append(f"  Price: {price_str}  |  52W Range: {lo} – {hi}  |  From 52W High: {pct}")

    ma_tokens: list[str] = []
    for key, label in [("sma_20", "SMA20"), ("sma_50", "SMA50"), ("sma_200", "SMA200"),
                       ("ema_12", "EMA12"), ("ema_26", "EMA26")]:
        s = _v(key, ".2f", "$")
        if s:
            ma_tokens.append(f"{label}={s}")
    if ma_tokens:
        trend_parts.append(f"  Moving Averages: {' | '.join(ma_tokens)}")

    vs = indicators.get("price_vs_sma200")
    gd = indicators.get("golden_death_cross")
    status_tokens: list[str] = []
    if vs:
        status_tokens.append(f"Price vs SMA200: {vs}")
    if gd and gd != "NONE":
        label = "GOLDEN CROSS (Bullish)" if gd == "GOLDEN_CROSS" else "DEATH CROSS (Bearish)"
        status_tokens.append(f"Cross: {label}")
    if status_tokens:
        trend_parts.append(f"  {' | '.join(status_tokens)}")

    if trend_parts:
        lines.append("[TREND]")
        lines.extend(trend_parts)

    # ── MOMENTUM ───────────────────────────────────────────────────────
    mom_parts: list[str] = []
    rsi = indicators.get("rsi_14")
    if rsi is not None:
        if rsi > 70:
            rsi_label = "OVERBOUGHT"
        elif rsi < 30:
            rsi_label = "OVERSOLD"
        else:
            rsi_label = "NEUTRAL"
        mom_parts.append(f"  RSI(14): {rsi:.1f} ({rsi_label})")

    macd_l = indicators.get("macd_line")
    macd_s = indicators.get("macd_signal")
    macd_h = indicators.get("macd_histogram")
    macd_x = indicators.get("macd_crossover")
    if macd_l is not None:
        macd_str = f"  MACD(12,26,9): Line={macd_l:+.4f} | Signal={macd_s:+.4f} | Hist={macd_h:+.4f}"
        if macd_x and macd_x != "NONE":
            macd_str += f" ({macd_x} CROSSOVER)"
        mom_parts.append(macd_str)

    stoch = indicators.get("stochastic_k")
    if stoch is not None:
        if stoch > 80:
            sk_label = "OVERBOUGHT"
        elif stoch < 20:
            sk_label = "OVERSOLD"
        else:
            sk_label = "NEUTRAL"
        mom_parts.append(f"  Stochastic %K(14,3): {stoch:.1f} ({sk_label})")

    if mom_parts:
        lines.append("[MOMENTUM]")
        lines.extend(mom_parts)

    # ── VOLATILITY ─────────────────────────────────────────────────────
    vol_parts: list[str] = []
    atr = indicators.get("atr_14")
    if atr is not None:
        vol_parts.append(f"  ATR(14): ${atr:.2f}")

    bb_u = indicators.get("bb_upper")
    bb_l = indicators.get("bb_lower")
    bb_bw = indicators.get("bb_bandwidth")
    bb_pb = indicators.get("bb_percent_b")
    if bb_u is not None:
        pb_label = ""
        if bb_pb is not None:
            if bb_pb > 1.0:
                pb_label = " — ABOVE UPPER BAND"
            elif bb_pb < 0.0:
                pb_label = " — BELOW LOWER BAND"
            else:
                pb_label = " — INSIDE BANDS"
        vol_parts.append(
            f"  Bollinger(20,2): ${bb_l:.2f} – ${bb_u:.2f} | "
            f"BW={bb_bw:.2f}% | %B={bb_pb:.2f}{pb_label}"
        )

    v30 = indicators.get("volatility_30d")
    if v30 is not None:
        vol_parts.append(f"  30-Day Realized Volatility: {v30:.1f}% (annualized)")

    if vol_parts:
        lines.append("[VOLATILITY]")
        lines.extend(vol_parts)

    # ── VOLUME ─────────────────────────────────────────────────────────
    vol_sec: list[str] = []
    va = indicators.get("volume_avg_20d")
    vr = indicators.get("volume_ratio")
    if va is not None:
        vol_sec.append(f"  20-Day Avg Volume: {va:,.0f} | Current Ratio: {vr:.2f}x")

    obv = indicators.get("obv_trend")
    if obv:
        vol_sec.append(f"  OBV Trend (20d): {obv}")

    if vol_sec:
        lines.append("[VOLUME]")
        lines.extend(vol_sec)

    # ── LEVELS ─────────────────────────────────────────────────────────
    supports = indicators.get("support_levels", [])
    resistances = indicators.get("resistance_levels", [])
    if supports or resistances:
        lines.append("[KEY LEVELS]")
        if supports:
            s_str = ", ".join(f"${v:.2f}" for v in supports)
            lines.append(f"  Support: {s_str}")
        if resistances:
            r_str = ", ".join(f"${v:.2f}" for v in resistances)
            lines.append(f"  Resistance: {r_str}")

    # ── PERFORMANCE ────────────────────────────────────────────────────
    perf_tokens: list[str] = []
    for key, label in [("return_1d", "1D"), ("return_1w", "1W"), ("return_1m", "1M"),
                       ("return_3m", "3M"), ("return_6m", "6M"), ("return_1y", "1Y")]:
        val = indicators.get(key)
        if val is not None:
            perf_tokens.append(f"{label}: {val:+.2f}%")
    if perf_tokens:
        lines.append("[PERFORMANCE]")
        lines.append(f"  {' | '.join(perf_tokens)}")

    return "\n".join(lines)
