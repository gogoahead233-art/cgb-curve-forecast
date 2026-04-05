"""
Wind Data Tools
================
Fetch macro, yield, funding, futures, stock index, and US Treasury data via WindPy.
Each function returns a formatted text string for LLM consumption.
"""

import atexit
import threading
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

import pandas as pd
import numpy as np
from langchain_core.tools import tool

import config

# Wind connection management (thread-safe)
_w = None
_w_lock = threading.Lock()


def _get_wind():
    """Lazy-load Wind connection, thread-safe, auto-close on program exit."""
    global _w
    if _w is not None:
        return _w
    with _w_lock:
        if _w is not None:
            return _w
        try:
            from WindPy import w
            w.start()
            if not w.isconnected():
                raise ConnectionError("Wind terminal not connected. Please ensure the Wind client is running.")
            _w = w
            atexit.register(lambda: w.stop())
        except ImportError:
            raise ImportError("WindPy not installed. Please install from Wind terminal, or set DATA_SOURCE=akshare")
    return _w


def init_wind():
    """Pre-initialize Wind connection (call in main thread to avoid parallel contention)."""
    _get_wind()


def _trend_direction(series: pd.Series) -> str:
    """Determine trend direction using linear regression slope."""
    s = series.dropna()
    if len(s) < 3:
        return "insufficient data"
    x = np.arange(len(s))
    slope = np.polyfit(x, s.values, 1)[0]
    if abs(slope) < 1e-6:
        return "flat"
    return "rising" if slope > 0 else "falling"


@tool
def get_macro_data(lookback_months: int = 24) -> str:
    """Fetch macroeconomic data: CPI, PMI, social financing (monthly increment + YoY), M2, with trend direction."""
    try:
        w = _get_wind()
    except (ImportError, ConnectionError) as e:
        return f"[Wind error] {e}"

    end = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - relativedelta(months=lookback_months)).strftime("%Y-%m-%d")

    # CPI/PMI/M2: YoY growth indicators
    pct_indicators = {
        "M0000612": "CPI YoY(%)",
        "M0017126": "PMI",
        "M0001385": "M2 YoY(%)",
    }

    results = []
    for code, name in pct_indicators.items():
        data = w.edb(code, start, end)
        if data.ErrorCode != 0:
            results.append(f"{name}: data retrieval failed (error code {data.ErrorCode})")
            continue

        series = pd.Series(data.Data[0], index=pd.to_datetime(data.Times)).dropna()
        if series.empty:
            results.append(f"{name}: no data")
            continue

        latest = series.iloc[-1]
        latest_date = series.index[-1].strftime("%Y-%m-%d")
        trend_3m = _trend_direction(series.tail(3))
        trend_6m = _trend_direction(series.tail(6))
        trend_12m = _trend_direction(series.tail(12))

        results.append(
            f"{name}: latest={latest:.2f} (as of {latest_date}), "
            f"3-month trend={trend_3m}, 6-month trend={trend_6m}, 12-month trend={trend_12m}"
        )

    # Social financing: monthly increment (100M CNY) + YoY comparison, assess credit expansion/contraction
    # M5201945 = Social financing monthly increment
    sf_data = w.edb("M5201945", start, end)
    if sf_data.ErrorCode == 0:
        sf_series = pd.Series(sf_data.Data[0], index=pd.to_datetime(sf_data.Times)).dropna()
        if not sf_series.empty:
            latest_val = sf_series.iloc[-1]
            latest_date = sf_series.index[-1].strftime("%Y-%m-%d")
            latest_month = sf_series.index[-1]

            # YoY: find same month last year
            yoy_month = latest_month - relativedelta(years=1)
            # Find the closest data point to the same month last year
            yoy_candidates = sf_series[
                (sf_series.index.year == yoy_month.year) &
                (sf_series.index.month == yoy_month.month)
            ]
            if not yoy_candidates.empty:
                yoy_val = yoy_candidates.iloc[-1]
                yoy_change = latest_val - yoy_val
                yoy_pct = (yoy_change / abs(yoy_val) * 100) if yoy_val != 0 else 0
                results.append(
                    f"Social financing monthly increment: {latest_val:.0f} (100M CNY) (as of {latest_date}), "
                    f"same month last year={yoy_val:.0f} (100M CNY), YoY {'increase' if yoy_change > 0 else 'decrease'} {abs(yoy_change):.0f} (100M CNY) ({yoy_pct:+.1f}%)"
                )
            else:
                results.append(f"Social financing monthly increment: {latest_val:.0f} (100M CNY) (as of {latest_date}), same month last year data unavailable")

            # Credit expansion/contraction trend
            trend = _trend_direction(sf_series.tail(6))
            results.append(f"  Social financing increment 6-month trend: {trend} (rising=credit expansion, falling=credit contraction)")
        else:
            results.append("Social financing monthly increment: no data")
    else:
        # fallback: use stock YoY
        sf_stock = w.edb("M5525755", start, end)
        if sf_stock.ErrorCode == 0:
            s = pd.Series(sf_stock.Data[0], index=pd.to_datetime(sf_stock.Times)).dropna()
            if not s.empty:
                latest = s.iloc[-1]
                latest_date = s.index[-1].strftime("%Y-%m-%d")
                results.append(f"Social financing stock YoY: {latest:.2f}% (as of {latest_date})")
        else:
            results.append("Social financing: data retrieval failed")

    return "\n".join(results)


@tool
def get_yield_curve(lookback_years: int = 1) -> str:
    """Fetch government bond yield curve: 1Y/10Y/30Y current values, percentiles, and term spreads."""
    try:
        w = _get_wind()
    except (ImportError, ConnectionError) as e:
        return f"[Wind error] {e}"

    end = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - relativedelta(years=lookback_years)).strftime("%Y-%m-%d")

    codes = {
        "S0059744": "1Y",
        "S0059749": "10Y",
        "S0059751": "30Y",
    }

    yields = {}
    lines = []
    latest_date = None

    for code, tenor in codes.items():
        data = w.edb(code, start, end)
        if data.ErrorCode != 0:
            lines.append(f"{tenor} CGB: data retrieval failed")
            continue

        series = pd.Series(data.Data[0], index=pd.to_datetime(data.Times)).dropna()
        if series.empty:
            lines.append(f"{tenor} CGB: no data")
            continue

        latest = series.iloc[-1]
        latest_date = series.index[-1].strftime("%Y-%m-%d")
        pct = (series < latest).sum() / len(series) * 100
        yields[tenor] = latest

        lines.append(f"{tenor} CGB: {latest:.4f}% (as of {latest_date}), {lookback_years}-year percentile={pct:.0f}%")

    # Term spreads
    if "10Y" in yields and "1Y" in yields:
        spread_10_1 = (yields["10Y"] - yields["1Y"]) * 100
        lines.append(f"10Y-1Y spread: {spread_10_1:.1f}bp")
    if "30Y" in yields and "10Y" in yields:
        spread_30_10 = (yields["30Y"] - yields["10Y"]) * 100
        lines.append(f"30Y-10Y spread: {spread_30_10:.1f}bp")

    return "\n".join(lines)


@tool
def get_funding_data(lookback_days: int = 60) -> str:
    """Fetch funding data: DR007, PBOC reverse repo net injection."""
    try:
        w = _get_wind()
    except (ImportError, ConnectionError) as e:
        return f"[Wind error] {e}"

    end = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")

    lines = []

    # Dynamically fetch 7-day reverse repo policy rate (M0041371: China reverse repo rate 7D)
    policy_rate = config.POLICY_RATE_7D  # fallback
    pr_data = w.edb("M0041371", (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d"), end)
    if pr_data.ErrorCode == 0:
        pr_s = pd.Series(pr_data.Data[0], index=pd.to_datetime(pr_data.Times)).dropna()
        if not pr_s.empty:
            policy_rate = pr_s.iloc[-1]

    # DR007
    dr = w.edb("M0041653", start, end)
    if dr.ErrorCode == 0:
        s = pd.Series(dr.Data[0], index=pd.to_datetime(dr.Times)).dropna()
        if not s.empty:
            latest = s.iloc[-1]
            latest_date = s.index[-1].strftime("%Y-%m-%d")
            ma20 = s.tail(20).mean()
            deviation = (latest - policy_rate) * 100
            lines.append(
                f"DR007: latest={latest:.4f}% (as of {latest_date}), 20-day avg={ma20:.4f}%, "
                f"vs policy rate ({policy_rate:.2f}%) deviation={deviation:+.1f}bp"
            )

    # Reverse repo injection/maturity
    for code, name in [("M0062063", "Reverse repo injection"), ("M0062065", "Reverse repo maturity")]:
        data = w.edb(code, start, end)
        if data.ErrorCode == 0:
            s = pd.Series(data.Data[0], index=pd.to_datetime(data.Times)).dropna()
            if not s.empty:
                latest = s.iloc[-1]
                latest_date = s.index[-1].strftime("%Y-%m-%d")
                lines.append(f"{name}: latest={latest:.0f} (100M CNY) (as of {latest_date})")

    # Calculate net injection
    invest = w.edb("M0062063", start, end)
    expire = w.edb("M0062065", start, end)
    if invest.ErrorCode == 0 and expire.ErrorCode == 0:
        s_inv = pd.Series(invest.Data[0], index=pd.to_datetime(invest.Times)).dropna()
        s_exp = pd.Series(expire.Data[0], index=pd.to_datetime(expire.Times)).dropna()
        if not s_inv.empty and not s_exp.empty:
            net = s_inv.iloc[-1] - s_exp.iloc[-1]
            lines.append(f"Net injection: {net:+.0f} (100M CNY)")

    return "\n".join(lines) if lines else "Funding data retrieval failed"


@tool
def get_futures_data(lookback_days: int = 60) -> str:
    """Fetch treasury futures data: T (10Y) and TL (30Y) price, volume, and open interest."""
    try:
        w = _get_wind()
    except (ImportError, ConnectionError) as e:
        return f"[Wind error] {e}"

    end = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")

    lines = []

    for contract, name in [("T.CFE", "T (10Y futures)"), ("TL.CFE", "TL (30Y futures)")]:
        data = w.wsd(contract, "close,volume,oi", start, end)
        if data.ErrorCode != 0:
            lines.append(f"{name}: data retrieval failed")
            continue

        df = pd.DataFrame(
            {"close": data.Data[0], "volume": data.Data[1], "oi": data.Data[2]},
            index=pd.to_datetime(data.Times),
        ).dropna()

        if df.empty:
            lines.append(f"{name}: no data")
            continue

        latest = df.iloc[-1]
        latest_date = df.index[-1].strftime("%Y-%m-%d")
        lines.append(
            f"{name}: close={latest['close']:.3f}, "
            f"volume={latest['volume']:.0f} lots, "
            f"OI={latest['oi']:.0f} lots (as of {latest_date})"
        )

        # Provide summary of recent data for technical indicator calculation
        lines.append(
            f"  Last {len(df)} days: price range=[{df['close'].min():.3f}, {df['close'].max():.3f}], "
            f"avg volume={df['volume'].mean():.0f} lots"
        )

        # Output daily data (JSON format) for calc_tech_signals
        records = df.reset_index().rename(columns={"index": "date"})
        records["date"] = records["date"].dt.strftime("%Y-%m-%d")
        lines.append(f"  {name} daily data: {records.to_dict('records')}")

    return "\n".join(lines)


@tool
def get_stock_index(lookback_days: int = 20) -> str:
    """Fetch Shanghai Composite Index recent trend."""
    try:
        w = _get_wind()
    except (ImportError, ConnectionError) as e:
        return f"[Wind error] {e}"

    end = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=lookback_days * 2)).strftime("%Y-%m-%d")

    data = w.wsd("000001.SH", "close", start, end)
    if data.ErrorCode != 0:
        return "Shanghai Composite Index data retrieval failed"

    s = pd.Series(data.Data[0], index=pd.to_datetime(data.Times)).dropna()
    if s.empty:
        return "Shanghai Composite Index: no data"

    latest = s.iloc[-1]
    latest_date = s.index[-1].strftime("%Y-%m-%d")
    if len(s) >= lookback_days:
        change = (latest / s.iloc[-lookback_days] - 1) * 100
    else:
        change = (latest / s.iloc[0] - 1) * 100

    return f"Shanghai Composite Index: latest={latest:.2f} (as of {latest_date}), {lookback_days}-day change={change:+.2f}%"


@tool
def get_us_treasury() -> str:
    """Fetch US 10Y Treasury yield and China-US yield spread."""
    try:
        w = _get_wind()
    except (ImportError, ConnectionError) as e:
        return f"[Wind error] {e}"

    end = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    # US 10Y Treasury
    us = w.edb("G0000891", start, end)
    # China 10Y CGB
    cn = w.edb("S0059749", start, end)

    lines = []
    us_latest = cn_latest = None

    if us.ErrorCode == 0:
        s = pd.Series(us.Data[0], index=pd.to_datetime(us.Times)).dropna()
        if not s.empty:
            us_latest = s.iloc[-1]
            us_date = s.index[-1].strftime("%Y-%m-%d")
            lines.append(f"US 10Y Treasury: {us_latest:.4f}% (as of {us_date})")

    if cn.ErrorCode == 0:
        s = pd.Series(cn.Data[0], index=pd.to_datetime(cn.Times)).dropna()
        if not s.empty:
            cn_latest = s.iloc[-1]
            cn_date = s.index[-1].strftime("%Y-%m-%d")
            lines.append(f"China 10Y CGB: {cn_latest:.4f}% (as of {cn_date})")

    if us_latest is not None and cn_latest is not None:
        spread = (cn_latest - us_latest) * 100
        lines.append(f"China-US spread (CN-US): {spread:+.0f}bp")

    return "\n".join(lines) if lines else "China-US yield data retrieval failed"
