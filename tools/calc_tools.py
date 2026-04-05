"""
Calculation Tools
==================
Technical indicator computation and curve shape determination.
"""

import json

import pandas as pd
import numpy as np
from langchain_core.tools import tool


def _parse_numeric_json(text: str) -> np.ndarray:
    """Parse a JSON string into a numeric array. Supports plain number lists or dict lists."""
    raw = json.loads(text)
    if not raw:
        return np.array([], dtype=float)
    if isinstance(raw[0], dict):
        for key in ["value", "close", "val", "数值"]:
            if key in raw[0]:
                raw = [item[key] for item in raw]
                break
        else:
            raw = [v for item in raw for v in item.values() if isinstance(v, (int, float))]
    return np.array(raw, dtype=float)


@tool
def calc_curve_shape(yield_1y_json: str, yield_10y_json: str, yield_30y_json: str) -> str:
    """Determine yield curve shape. Input: JSON lists of recent 30-day 1Y/10Y/30Y yields, e.g. '[1.5,1.51,...]'."""
    try:
        y1 = _parse_numeric_json(yield_1y_json)
        y10 = _parse_numeric_json(yield_10y_json)
        y30 = _parse_numeric_json(yield_30y_json)
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        return f"Data parsing error: {e}"

    if len(y1) < 5 or len(y10) < 5:
        return "Insufficient data (at least 5 data points required)"

    # Calculate change in bp between most recent and earliest
    delta_1y = (y1[-1] - y1[0]) * 100
    delta_10y = (y10[-1] - y10[0]) * 100
    delta_30y = (y30[-1] - y30[0]) * 100 if len(y30) >= 5 else 0

    # Term spread
    spread_10_1_now = (y10[-1] - y1[-1]) * 100
    spread_10_1_before = (y10[0] - y1[0]) * 100
    spread_change = spread_10_1_now - spread_10_1_before

    spread_30_10_now = (y30[-1] - y10[-1]) * 100 if len(y30) >= 5 else None

    lines = []
    lines.append(f"1Y change: {delta_1y:+.1f}bp, 10Y change: {delta_10y:+.1f}bp, 30Y change: {delta_30y:+.1f}bp")
    lines.append(f"10Y-1Y spread: {spread_10_1_now:.1f}bp (change {spread_change:+.1f}bp)")
    if spread_30_10_now is not None:
        lines.append(f"30Y-10Y spread: {spread_30_10_now:.1f}bp")

    # Shape determination
    threshold = 3  # bp
    if abs(delta_1y) < threshold and abs(delta_10y) < threshold:
        shape = "range_bound"
        desc = "Range-bound (both short-end and long-end moves < 3bp)"
    elif delta_1y < 0 and delta_10y < 0:
        # Bull market
        if abs(delta_10y) > abs(delta_1y):
            shape = "bull_flat"
            desc = "Bull flattening (long-end falls faster, spread narrows)"
        else:
            shape = "bull_steep"
            desc = "Bull steepening (short-end falls faster, spread widens)"
    elif delta_1y > 0 and delta_10y > 0:
        # Bear market
        if abs(delta_10y) > abs(delta_1y):
            shape = "bear_steep"
            desc = "Bear steepening (long-end rises faster, spread widens)"
        else:
            shape = "bear_flat"
            desc = "Bear flattening (short-end rises faster, spread narrows)"
    else:
        # Divergent directions
        if delta_10y < 0:
            shape = "bull_flat"
            desc = "Leaning bull flat (long-end falls but short-end rises, spread narrows)"
        else:
            shape = "bear_steep"
            desc = "Leaning bear steep (long-end rises but short-end falls, spread widens)"

    lines.append(f"Shape determination: {shape} — {desc}")

    return "\n".join(lines)


@tool
def calc_tech_signals(close_json: str, volume_json: str, oi_json: str) -> str:
    """Calculate treasury futures technical indicators. Input: JSON lists of recent 60-day close/volume/OI."""
    try:
        close = pd.Series(_parse_numeric_json(close_json))
        volume = pd.Series(_parse_numeric_json(volume_json))
        oi = pd.Series(_parse_numeric_json(oi_json))
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        return f"Data parsing error: {e}"

    if len(close) < 20:
        return "Insufficient data (at least 20 trading days required)"

    # Align array lengths (use shortest)
    min_len = min(len(close), len(volume), len(oi))
    close = close.iloc[:min_len].reset_index(drop=True)
    volume = volume.iloc[:min_len].reset_index(drop=True)
    oi = oi.iloc[:min_len].reset_index(drop=True)

    lines = []

    # === 1. Moving Average System ===
    ma5 = close.rolling(5).mean()
    ma20 = close.rolling(20).mean()
    ma5_now = ma5.iloc[-1]
    ma20_now = ma20.iloc[-1]

    if pd.isna(ma5_now) or pd.isna(ma20_now):
        lines.append("MA: insufficient data")
    else:
        gap = ma5_now - ma20_now
        ma5_shift5 = ma5.shift(5)
        ma20_shift5 = ma20.shift(5)
        if pd.notna(ma5_shift5.iloc[-1]) and pd.notna(ma20_shift5.iloc[-1]):
            prev_gap = ma5_shift5.iloc[-1] - ma20_shift5.iloc[-1]
            if gap > 0:
                if gap > prev_gap:
                    ma_desc = "Bullish alignment, gap widening (trend accelerating)"
                else:
                    ma_desc = "Bullish alignment, gap narrowing (trend weakening)"
            else:
                if gap < prev_gap:
                    ma_desc = "Bearish alignment, gap widening (decline accelerating)"
                else:
                    ma_desc = "Bearish alignment, gap narrowing (decline weakening)"
        else:
            ma_desc = f"MA5={'>' if gap > 0 else '<'}MA20"

        lines.append(f"MA5={ma5_now:.3f}, MA20={ma20_now:.3f}, {ma_desc}")

    # === 2. MACD ===
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    dif = ema12 - ema26
    dea = dif.ewm(span=9, adjust=False).mean()
    macd_bar = (dif - dea) * 2

    dif_now = dif.iloc[-1]
    dea_now = dea.iloc[-1]
    bar_now = macd_bar.iloc[-1]

    # Golden cross / Death cross
    if len(dif) >= 2 and len(dea) >= 2:
        prev_diff = dif.iloc[-2] - dea.iloc[-2]
        curr_diff = dif.iloc[-1] - dea.iloc[-1]
        if prev_diff <= 0 and curr_diff > 0:
            cross = "Golden cross (bullish signal)"
        elif prev_diff >= 0 and curr_diff < 0:
            cross = "Death cross (bearish signal)"
        else:
            cross = "No crossover"
    else:
        cross = "Insufficient data"

    # Bar direction
    if len(macd_bar) >= 2:
        bar_trend = "positive" if bar_now > 0 else "negative"
        bar_change = "expanding" if abs(bar_now) > abs(macd_bar.iloc[-2]) else "contracting"
    else:
        bar_trend = "N/A"
        bar_change = ""

    lines.append(f"MACD: DIF={dif_now:.4f}, DEA={dea_now:.4f}, bar={bar_now:.4f} ({bar_trend} {bar_change}), {cross}")

    # === 3. Volume-Price Validation ===
    # Price direction: recent 5-day avg vs prior 5-day avg
    if len(close) >= 10:
        recent_price = close.tail(5).mean()
        prev_price = close.iloc[-10:-5].mean()
        price_dir = "up" if recent_price > prev_price else "down"
    else:
        price_dir = "N/A"

    # Volume change: recent 5-day avg vs prior 20-day avg
    if len(volume) >= 25:
        recent_vol = volume.tail(5).mean()
        prev_vol = volume.iloc[-25:-5].mean()
        vol_dir = "rising volume" if recent_vol > prev_vol * 1.1 else ("falling volume" if recent_vol < prev_vol * 0.9 else "stable volume")
    elif len(volume) >= 10:
        recent_vol = volume.tail(5).mean()
        prev_vol = volume.iloc[:-5].mean()
        vol_dir = "rising volume" if recent_vol > prev_vol * 1.1 else ("falling volume" if recent_vol < prev_vol * 0.9 else "stable volume")
    else:
        vol_dir = "N/A"

    # Open interest change
    if len(oi) >= 20:
        oi_change = oi.iloc[-1] - oi.iloc[-20]
        oi_dir = "OI increasing" if oi_change > 0 else "OI decreasing"
    else:
        oi_dir = "N/A"

    # Comprehensive assessment
    if price_dir == "up":
        if oi_dir == "OI increasing" and vol_dir == "rising volume":
            vol_price = "OI increasing + rising volume + price up — new longs entering, high trend credibility"
        elif oi_dir == "OI decreasing" and vol_dir == "rising volume":
            vol_price = "OI decreasing + rising volume + price up — short covering driven, sustainability questionable"
        elif oi_dir == "OI decreasing" and vol_dir == "falling volume":
            vol_price = "OI decreasing + falling volume + price up — trend exhaustion"
        else:
            vol_price = f"Price up, {vol_dir}, {oi_dir}"
    elif price_dir == "down":
        if oi_dir == "OI increasing" and vol_dir == "rising volume":
            vol_price = "OI increasing + rising volume + price down — new shorts entering, downtrend initiating"
        elif oi_dir == "OI decreasing" and vol_dir == "rising volume":
            vol_price = "OI decreasing + rising volume + price down — long stop-loss"
        else:
            vol_price = f"Price down, {vol_dir}, {oi_dir}"
    else:
        vol_price = "Price direction unclear"

    lines.append(f"Volume-Price: price {price_dir}, {vol_dir}, {oi_dir} -> {vol_price}")

    return "\n".join(lines)


@tool
def calc_trend_direction(series_json: str, periods: str = "3,6,12") -> str:
    """Calculate trend direction for monthly series over specified periods. Input: monthly data JSON list and periods (e.g. '3,6,12')."""
    try:
        data = _parse_numeric_json(series_json)
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        return f"Data parsing error: {e}"

    period_list = [int(p.strip()) for p in periods.split(",")]

    results = []
    for p in period_list:
        if len(data) < p:
            results.append(f"Last {p} months: insufficient data")
            continue
        segment = data[-p:]
        x = np.arange(len(segment))
        slope = np.polyfit(x, segment, 1)[0]
        if abs(slope) < 1e-6:
            direction = "flat"
        else:
            direction = "rising" if slope > 0 else "falling"
        results.append(f"Last {p} months: {direction} (slope={slope:.4f})")

    return "\n".join(results)
