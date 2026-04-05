"""
Data Quality Check
==================
Check the reasonableness of all data tool return values using Wind/AKShare data,
and cross-validate via Tavily search.
Run: python tests/test_data_quality.py
"""

import re
import sys
import os
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config


# ============================================================
# Utility Functions
# ============================================================

def extract_number(text: str, pattern: str) -> float | None:
    """Extract a number from text using a regex pattern."""
    m = re.search(pattern, text)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            return None
    return None


def extract_date(text: str) -> datetime | None:
    """Extract date in (as of YYYY-MM-DD) format from text."""
    m = re.search(r"as of (\d{4}-\d{2}-\d{2})", text)
    if m:
        return datetime.strptime(m.group(1), "%Y-%m-%d")
    return None


def check_range(name: str, value: float | None, lo: float, hi: float) -> bool:
    """Range validation, returns whether passed."""
    if value is None:
        print(f"  [WARNING] {name}: could not extract value")
        return False
    if lo <= value <= hi:
        print(f"  [OK] {name}: {value} (valid range {lo}~{hi})")
        return True
    else:
        print(f"  [WARNING] {name}: {value} outside valid range {lo}~{hi}")
        return False


def check_freshness(name: str, date: datetime | None, max_days: int) -> bool:
    """Data freshness validation."""
    if date is None:
        print(f"  [WARNING] {name}: could not extract date")
        return False
    age = (datetime.now() - date).days
    if age <= max_days:
        print(f"  [OK] {name}: as of {date.strftime('%Y-%m-%d')}, {age} days ago (max {max_days})")
        return True
    else:
        print(f"  [WARNING] {name}: as of {date.strftime('%Y-%m-%d')}, {age} days ago, exceeds {max_days}")
        return False


def tavily_search(query: str) -> str:
    """Execute a single Tavily search, return answer + top 2 snippets."""
    if not config.TAVILY_API_KEY:
        return "[Tavily not configured]"
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=config.TAVILY_API_KEY)
        resp = client.search(query=query, max_results=2, search_depth="basic", include_answer=True)
        parts = []
        if resp.get("answer"):
            parts.append(resp["answer"])
        for r in resp.get("results", [])[:2]:
            parts.append(f"  - {r.get('title', '')}: {r.get('content', '')[:150]}")
        return "\n".join(parts) if parts else "[No results]"
    except Exception as e:
        return f"[Search failed: {e}]"


def extract_number_from_search(text: str, patterns: list[str]) -> float | None:
    """Try multiple regex patterns to extract a number from search results."""
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                continue
    return None


def check_cross_validate(name: str, wind_val: float | None, search_val: float | None,
                         tolerance: float, unit: str = "") -> bool:
    """Cross-validate: Wind data vs search data; alert if deviation exceeds tolerance."""
    if wind_val is None:
        print(f"  [SKIP] {name}: Wind data missing, cannot cross-validate")
        return True
    if search_val is None:
        print(f"  [SKIP] {name}: Could not extract value from search, cannot cross-validate")
        return True
    diff = abs(wind_val - search_val)
    if diff <= tolerance:
        print(f"  [OK] {name}: Wind={wind_val}{unit}, Search={search_val}{unit}, deviation={diff:.4f} (tolerance {tolerance})")
        return True
    else:
        print(f"  [WARNING] {name}: Wind={wind_val}{unit}, Search={search_val}{unit}, deviation={diff:.4f} exceeds tolerance {tolerance}")
        return False


def _indent(text: str, prefix: str = "    ") -> str:
    """Add indentation to multi-line text."""
    return "\n".join(f"{prefix}{line}" for line in text.split("\n"))


# ============================================================
# Main Flow
# ============================================================

def main():
    print("=" * 70)
    print(f"Data Quality Check  (Current time: {datetime.now().strftime('%Y-%m-%d %H:%M')})")
    print(f"Data source: {config.DATA_SOURCE}")
    print(f"Tavily cross-validation: {'Configured' if config.TAVILY_API_KEY else 'Not configured (skipping)'}")
    print("=" * 70)

    # Initialize Wind (if needed)
    if config.DATA_SOURCE == "wind":
        try:
            from tools.wind_tools import init_wind
            init_wind()
            print("[OK] Wind connected successfully\n")
        except Exception as e:
            print(f"[ERROR] Wind connection failed: {e}")
            print("Please confirm Wind terminal is logged in, or set DATA_SOURCE=akshare\n")
            return

    from tools.data_tools import get_data_tools
    tools = get_data_tools()

    total_checks = 0
    warnings = 0

    def tally(ok: bool):
        nonlocal total_checks, warnings
        total_checks += 1
        if not ok:
            warnings += 1

    # ============================================================
    # PART 1: Basic Range + Freshness Validation
    # ============================================================

    # --- 1. Macro Data ---
    print("-" * 70)
    print("1. Macro Data (get_macro_data)")
    print("-" * 70)
    macro_text = tools["get_macro_data"].invoke({"lookback_months": 24})
    print(f"  Raw output:\n{_indent(macro_text)}\n")

    # CPI: "CPI YoY(%): latest=X.XX (as of ...)"
    cpi_val = extract_number(macro_text, r"CPI YoY.*?latest=([-\d.]+)")
    tally(check_range("CPI YoY (%)", cpi_val, -3, 10))
    date = extract_date(macro_text.split("CPI")[1]) if "CPI" in macro_text else None
    tally(check_freshness("CPI data date", date, 45))

    # PMI: "PMI: latest=X.XX (as of ...)"
    pmi_val = extract_number(macro_text, r"PMI.*?latest=([-\d.]+)")
    tally(check_range("PMI", pmi_val, 40, 60))
    date = extract_date(macro_text.split("PMI")[1]) if "PMI" in macro_text else None
    tally(check_freshness("PMI data date", date, 45))

    # Social financing: "Social financing monthly increment: X (100M CNY) (as of ...)"
    sf_val = extract_number(macro_text, r"[Ss]ocial financing monthly increment.*?([-\d.]+)")
    if sf_val is not None:
        tally(check_range("Social financing monthly increment (100M CNY)", sf_val, -5000, 80000))
    else:
        print("  [WARNING] Social financing monthly increment: could not retrieve value (may be AKShare limitation)")
        tally(False)

    # M2: "M2 YoY(%): latest=X.XX (as of ...)"
    m2_val = extract_number(macro_text, r"M2 YoY.*?latest=([-\d.]+)")
    tally(check_range("M2 YoY (%)", m2_val, 5, 15))
    date = extract_date(macro_text.split("M2")[1]) if "M2" in macro_text else None
    tally(check_freshness("M2 data date", date, 45))

    # --- Social financing unit label check ---
    print()
    print("  -- Social financing description check (should be 'monthly increment' not 'growth rate') --")
    if "monthly increment" in macro_text.lower() and "100M CNY" in macro_text:
        print("  [OK] Social financing description contains 'monthly increment' and '100M CNY'")
        tally(True)
    elif "AKShare" in macro_text and ("unavailable" in macro_text.lower() or "no stable" in macro_text.lower()):
        print("  [OK] AKShare mode correctly indicates social financing API unavailable")
        tally(True)
    else:
        print(f"  [WARNING] Social financing description may be incorrect, please check:")
        for line in macro_text.split("\n"):
            if "social" in line.lower() or "financing" in line.lower():
                print(f"    {line}")
        tally(False)

    if "social" in macro_text.lower() and "growth rate" in macro_text.lower():
        print("  [WARNING] Social financing description contains 'growth rate', may mislead LLM")
        tally(False)

    # --- 2. Yield Curve ---
    print()
    print("-" * 70)
    print("2. Yield Curve (get_yield_curve)")
    print("-" * 70)
    yield_text = tools["get_yield_curve"].invoke({"lookback_years": 1})
    print(f"  Raw output:\n{_indent(yield_text)}\n")

    # "10Y CGB: X.XXXX% (as of ...)"
    yield_10y = extract_number(yield_text, r"10Y CGB.*?([\d.]+)%")
    for tenor in ["1Y", "10Y", "30Y"]:
        val = extract_number(yield_text, rf"{tenor} CGB.*?([\d.]+)%")
        tally(check_range(f"{tenor} CGB yield (%)", val, 0, 6))
    tally(check_freshness("Yield data date", extract_date(yield_text), 5))

    # --- 3. Funding Data ---
    print()
    print("-" * 70)
    print("3. Funding Data (get_funding_data)")
    print("-" * 70)
    fund_text = tools["get_funding_data"].invoke({"lookback_days": 60})
    print(f"  Raw output:\n{_indent(fund_text)}\n")

    # "DR007: latest=X.XXXX% (as of ...)"
    dr007_val = extract_number(fund_text, r"DR007.*?latest=([\d.]+)%")
    if dr007_val is None:
        # AKShare fallback: "7-day repo rate: latest=X.XXXX%"
        dr007_val = extract_number(fund_text, r"[Rr]epo.*?latest=([\d.]+)%")
    tally(check_range("DR007 (%)", dr007_val, 0.5, 5))
    tally(check_freshness("DR007 data date", extract_date(fund_text), 5))

    # --- 4. Policy Rate Consistency ---
    print()
    print("-" * 70)
    print("4. Policy Rate Consistency Check")
    print("-" * 70)
    # "vs policy rate (X.XX%)"
    pr_match = re.search(r"policy rate \(([\d.]+)%\)", fund_text)
    wind_policy_rate = float(pr_match.group(1)) if pr_match else None
    if wind_policy_rate is not None:
        config_pr = config.POLICY_RATE_7D
        if abs(wind_policy_rate - config_pr) < 0.01:
            print(f"  [OK] Policy rate consistent: actual={wind_policy_rate}%, config={config_pr}%")
            tally(True)
        else:
            print(f"  [WARNING] Policy rate inconsistent: actual={wind_policy_rate}%, config={config_pr}%")
            print(f"    Wind dynamically fetched a different value, or config.POLICY_RATE_7D needs updating")
            tally(False)
    else:
        print("  [WARNING] Could not extract policy rate value from output")
        tally(False)

    # --- 5. Futures Data ---
    print()
    print("-" * 70)
    print("5. Futures Data (get_futures_data)")
    print("-" * 70)
    futures_text = tools["get_futures_data"].invoke({"lookback_days": 60})
    futures_lines = futures_text.split("\n")
    print(f"  Raw output (first 3 lines):\n{_indent(chr(10).join(futures_lines[:3]))}\n")

    # "T(10Y futures): close=X.XXX"
    tally(check_range("T futures price", extract_number(futures_text, r"T\(10Y futures\).*?close=([\d.]+)"), 95, 115))
    tally(check_range("TL futures price", extract_number(futures_text, r"TL\(30Y futures\).*?close=([\d.]+)"), 95, 125))
    tally(check_freshness("Futures data date", extract_date(futures_text), 5))

    # --- 6. Shanghai Composite Index ---
    print()
    print("-" * 70)
    print("6. Shanghai Composite Index (get_stock_index)")
    print("-" * 70)
    stock_text = tools["get_stock_index"].invoke({"lookback_days": 20})
    print(f"  Raw output:\n{_indent(stock_text)}\n")

    # "SSE Composite: latest=X.XX (as of ...)"
    tally(check_range("SSE Composite Index", extract_number(stock_text, r"latest=([\d.]+)"), 2000, 6500))
    tally(check_freshness("SSE Composite date", extract_date(stock_text), 5))

    # --- 7. US Treasury / CN-US Spread ---
    print()
    print("-" * 70)
    print("7. US Treasury / CN-US Spread (get_us_treasury)")
    print("-" * 70)
    us_text = tools["get_us_treasury"].invoke({})
    print(f"  Raw output:\n{_indent(us_text)}\n")

    # "US 10Y: X.XXXX% (as of ...)"
    us10y_val = extract_number(us_text, r"US 10Y.*?([\d.]+)%")
    tally(check_range("US 10Y Treasury (%)", us10y_val, 0, 8))
    tally(check_freshness("US Treasury data date", extract_date(us_text), 5))

    # ============================================================
    # PART 2: Search Cross-Validation
    # ============================================================
    print()
    print("=" * 70)
    print("PART 2: Search Cross-Validation")
    print("=" * 70)

    if not config.TAVILY_API_KEY:
        print("  [SKIP] Tavily not configured, skipping cross-validation\n")
    else:
        # --- CPI Cross-Validation ---
        print()
        print("-" * 70)
        print("8. CPI Cross-Validation")
        print("-" * 70)
        cpi_search = tavily_search("中国最新CPI同比 2026")
        print(f"  Search results:\n{_indent(cpi_search)}\n")
        cpi_search_val = extract_number_from_search(cpi_search, [
            r"CPI.*?同比.*?([-\d.]+)%",
            r"CPI.*?([-\d.]+)%",
            r"([-\d.]+)%.*?CPI",
        ])
        tally(check_cross_validate("CPI YoY", cpi_val, cpi_search_val, tolerance=0.5, unit="%"))

        # --- DR007 Cross-Validation ---
        print()
        print("-" * 70)
        print("9. DR007 Cross-Validation")
        print("-" * 70)
        dr_search = tavily_search("DR007 最新利率")
        print(f"  Search results:\n{_indent(dr_search)}\n")
        dr_search_val = extract_number_from_search(dr_search, [
            r"DR007.*?([\d.]+)%",
            r"([\d.]+)%.*?DR007",
        ])
        tally(check_cross_validate("DR007", dr007_val, dr_search_val, tolerance=0.10, unit="%"))

        # --- 10Y CGB Yield Cross-Validation ---
        print()
        print("-" * 70)
        print("10. 10Y CGB Yield Cross-Validation")
        print("-" * 70)
        y10_search = tavily_search("10年期国债收益率 最新 2026")
        print(f"  Search results:\n{_indent(y10_search)}\n")
        y10_search_val = extract_number_from_search(y10_search, [
            r"10年.*?国债.*?收益率.*?([\d.]+)%",
            r"([\d.]+)%.*?10年.*?国债",
            r"10Y.*?([\d.]+)%",
        ])
        tally(check_cross_validate("10Y CGB yield", yield_10y, y10_search_val, tolerance=0.10, unit="%"))

        # --- Policy Rate Cross-Validation ---
        print()
        print("-" * 70)
        print("11. 7-Day Reverse Repo Policy Rate Cross-Validation")
        print("-" * 70)
        pr_search = tavily_search("7天逆回购利率 最新 央行")
        print(f"  Search results:\n{_indent(pr_search)}\n")
        pr_search_val = extract_number_from_search(pr_search, [
            r"7天.*?逆回购.*?([\d.]+)%",
            r"逆回购.*?利率.*?([\d.]+)%",
            r"OMO.*?([\d.]+)%",
        ])
        # Compare with Wind dynamically fetched value
        tally(check_cross_validate("Policy rate (vs Wind)", wind_policy_rate, pr_search_val, tolerance=0.10, unit="%"))
        # Compare with config fallback value
        tally(check_cross_validate("Policy rate (vs config)", config.POLICY_RATE_7D, pr_search_val, tolerance=0.10, unit="%"))

    # ============================================================
    # Summary
    # ============================================================
    print()
    print("=" * 70)
    print(f"Check complete: {total_checks} checks, {total_checks - warnings} passed, {warnings} warnings")
    if warnings == 0:
        print("[OK] All passed")
    else:
        print(f"[!] {warnings} items need attention")
    print("=" * 70)


if __name__ == "__main__":
    main()
