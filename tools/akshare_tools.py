"""
AKShare Backup Data Tools
==========================
When Wind is unavailable, use AKShare (free) to fetch data.
Function interfaces and return formats are consistent with wind_tools.
"""

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

import pandas as pd
import numpy as np
import akshare as ak
from langchain_core.tools import tool


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
    """Fetch macroeconomic data: CPI, PMI, M2, with trend direction. (AKShare source)"""
    results = []

    # AKShare macro interface column names
    date_col = "日期"
    val_col = "今值"

    # CPI
    try:
        df = ak.macro_china_cpi_yearly()
        df = df.sort_values(date_col)
        df[val_col] = pd.to_numeric(df[val_col], errors="coerce")
        df = df.dropna(subset=[val_col]).tail(lookback_months)
        if not df.empty:
            latest = df.iloc[-1][val_col]
            latest_date = str(df.iloc[-1][date_col])
            series = df[val_col]
            results.append(
                f"CPI YoY(%): latest={latest} (as of {latest_date}), "
                f"3-month trend={_trend_direction(series.tail(3))}, "
                f"6-month trend={_trend_direction(series.tail(6))}, "
                f"12-month trend={_trend_direction(series.tail(12))}"
            )
    except Exception as e:
        results.append(f"CPI: data retrieval failed ({e})")

    # PMI
    try:
        df = ak.macro_china_pmi_yearly()
        df = df.sort_values(date_col)
        df[val_col] = pd.to_numeric(df[val_col], errors="coerce")
        df = df.dropna(subset=[val_col]).tail(lookback_months)
        if not df.empty:
            latest = df.iloc[-1][val_col]
            latest_date = str(df.iloc[-1][date_col])
            series = df[val_col]
            results.append(
                f"PMI: latest={latest} (as of {latest_date}), "
                f"3-month trend={_trend_direction(series.tail(3))}, "
                f"6-month trend={_trend_direction(series.tail(6))}, "
                f"12-month trend={_trend_direction(series.tail(12))}"
            )
    except Exception as e:
        results.append(f"PMI: data retrieval failed ({e})")

    # Social financing (AKShare has no stable monthly increment API)
    results.append("Social financing monthly increment: AKShare has no stable API; please use search to get the latest social financing data (note: distinguish between monthly increment and stock YoY)")

    # M2
    try:
        df = ak.macro_china_m2_yearly()
        df = df.sort_values(date_col)
        df[val_col] = pd.to_numeric(df[val_col], errors="coerce")
        df = df.dropna(subset=[val_col]).tail(lookback_months)
        if not df.empty:
            latest = df.iloc[-1][val_col]
            latest_date = str(df.iloc[-1][date_col])
            series = df[val_col]
            results.append(
                f"M2 YoY(%): latest={latest} (as of {latest_date}), "
                f"3-month trend={_trend_direction(series.tail(3))}, "
                f"6-month trend={_trend_direction(series.tail(6))}, "
                f"12-month trend={_trend_direction(series.tail(12))}"
            )
    except Exception as e:
        results.append(f"M2: data retrieval failed ({e})")

    return "\n".join(results)


@tool
def get_yield_curve(lookback_years: int = 1) -> str:
    """Fetch government bond yield curve: 1Y/10Y/30Y current values, percentiles, and term spreads. (AKShare source)"""
    try:
        df = ak.bond_china_yield(start_date="", end_date="")
    except Exception as e:
        return f"Yield data retrieval failed: {e}"

    # Filter for ChinaBond government bond yield to maturity
    df_gov = df[df["曲线名称"] == "中债国债收益率曲线(到期)"].copy()
    if df_gov.empty:
        return "ChinaBond government bond yield data not found"

    df_gov["日期"] = pd.to_datetime(df_gov["日期"])
    cutoff = datetime.now() - relativedelta(years=lookback_years)
    df_gov = df_gov[df_gov["日期"] >= cutoff].sort_values("日期")

    lines = []
    yields = {}
    latest_date = df_gov["日期"].iloc[-1].strftime("%Y-%m-%d") if not df_gov.empty else "unknown"

    for col, tenor in [("1年", "1Y"), ("10年", "10Y"), ("30年", "30Y")]:
        if col not in df_gov.columns:
            lines.append(f"{tenor} CGB: column not found")
            continue
        series = pd.to_numeric(df_gov[col], errors="coerce").dropna()
        if series.empty:
            lines.append(f"{tenor} CGB: no data")
            continue

        latest = series.iloc[-1]
        pct = (series < latest).sum() / len(series) * 100
        yields[tenor] = latest
        lines.append(f"{tenor} CGB: {latest:.4f}% (as of {latest_date}), {lookback_years}-year percentile={pct:.0f}%")

    if "10Y" in yields and "1Y" in yields:
        spread = (yields["10Y"] - yields["1Y"]) * 100
        lines.append(f"10Y-1Y spread: {spread:.1f}bp")
    if "30Y" in yields and "10Y" in yields:
        spread = (yields["30Y"] - yields["10Y"]) * 100
        lines.append(f"30Y-10Y spread: {spread:.1f}bp")

    return "\n".join(lines)


@tool
def get_funding_data(lookback_days: int = 60) -> str:
    """Fetch funding data: DR007 related. (AKShare source)"""
    lines = []

    # DR007 via interbank repo rate
    try:
        df = ak.rate_interbank(market="China", symbol="Repo", indicator="7D")
        if df is not None and not df.empty:
            df = df.sort_values("报告日期").tail(lookback_days)
            series = pd.to_numeric(df["利率"], errors="coerce").dropna()
            if not series.empty:
                latest = series.iloc[-1]
                latest_date = str(df["报告日期"].iloc[-1])
                ma20 = series.tail(20).mean()
                import config
                policy_rate = config.POLICY_RATE_7D
                deviation = (latest - policy_rate) * 100
                lines.append(
                    f"Interbank 7-day repo rate: latest={latest:.4f}% (as of {latest_date}), 20-day avg={ma20:.4f}%, "
                    f"vs policy rate ({policy_rate}%) deviation={deviation:+.1f}bp"
                )
    except Exception as e:
        lines.append(f"Funding rate: data retrieval failed ({e})")

    lines.append("PBOC OMO reverse repo: AKShare data may be delayed; recommend using search for latest operation info")

    return "\n".join(lines) if lines else "Funding data retrieval failed"


@tool
def get_futures_data(lookback_days: int = 60) -> str:
    """Fetch treasury futures data: T (10Y) and TL (30Y) price, volume, and open interest. (AKShare source)"""
    lines = []

    for symbol, name in [("T0", "T (10Y futures)"), ("TL0", "TL (30Y futures)")]:
        try:
            df = ak.futures_main_sina(symbol=symbol)
            if df is None or df.empty:
                lines.append(f"{name}: no data")
                continue

            df = df.tail(lookback_days)
            latest = df.iloc[-1]

            close_col = "收盘价" if "收盘价" in df.columns else "close"
            vol_col = "成交量" if "成交量" in df.columns else "volume"
            oi_col = "持仓量" if "持仓量" in df.columns else "hold"
            date_col = "日期" if "日期" in df.columns else None

            latest_date = str(latest[date_col]) if date_col else df.index[-1]

            lines.append(
                f"{name}: close={latest[close_col]:.3f}, "
                f"volume={latest[vol_col]:.0f} lots, "
                f"OI={latest[oi_col]:.0f} lots (as of {latest_date})"
            )
            lines.append(
                f"  Last {len(df)} days: price range=[{df[close_col].min():.3f}, {df[close_col].max():.3f}], "
                f"avg volume={df[vol_col].mean():.0f} lots"
            )

            # Output daily data for technical indicator calculation
            if date_col:
                records = df[[date_col, close_col, vol_col, oi_col]].copy()
            else:
                records = df[[close_col, vol_col, oi_col]].reset_index()
            records.columns = ["date", "close", "volume", "oi"]
            records["date"] = records["date"].astype(str)
            lines.append(f"  {name} daily data: {records.to_dict('records')}")

        except Exception as e:
            lines.append(f"{name}: data retrieval failed ({e})")

    return "\n".join(lines)


@tool
def get_stock_index(lookback_days: int = 20) -> str:
    """Fetch Shanghai Composite Index recent trend. (AKShare source)"""
    try:
        df = ak.stock_zh_index_daily(symbol="sh000001")
        if df is None or df.empty:
            return "Shanghai Composite Index: no data"

        df = df.tail(lookback_days * 2)
        close = pd.to_numeric(df["close"], errors="coerce").dropna()

        latest = close.iloc[-1]
        # Get latest date
        if "date" in df.columns:
            latest_date = str(df["date"].iloc[-1])
        else:
            latest_date = str(df.index[-1])

        if len(close) >= lookback_days:
            change = (latest / close.iloc[-lookback_days] - 1) * 100
        else:
            change = (latest / close.iloc[0] - 1) * 100

        return f"Shanghai Composite Index: latest={latest:.2f} (as of {latest_date}), {lookback_days}-day change={change:+.2f}%"
    except Exception as e:
        return f"Shanghai Composite Index retrieval failed: {e}"


@tool
def get_us_treasury() -> str:
    """Fetch US 10Y Treasury yield and China-US yield spread. (AKShare source)"""
    try:
        df = ak.bond_zh_us_rate()
        if df is None or df.empty:
            return "China-US yield data retrieval failed"

        df = df.sort_values("日期")
        latest = df.iloc[-1]
        latest_date = str(latest["日期"])

        lines = []
        us_val = cn_val = None

        if "美国国债收益率10年" in df.columns:
            us_val = float(latest["美国国债收益率10年"])
            lines.append(f"US 10Y Treasury: {us_val:.4f}% (as of {latest_date})")
        if "中国国债收益率10年" in df.columns:
            cn_val = float(latest["中国国债收益率10年"])
            lines.append(f"China 10Y CGB: {cn_val:.4f}% (as of {latest_date})")

        if us_val is not None and cn_val is not None:
            spread = (cn_val - us_val) * 100
            lines.append(f"China-US spread (CN-US): {spread:+.0f}bp")

        return "\n".join(lines) if lines else "China-US yield data format error"
    except Exception as e:
        return f"China-US yield retrieval failed: {e}"
