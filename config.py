"""
Project Configuration
=====================
Reads sensitive information (API keys) from .env file; other configs defined directly.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ====================
# LLM Configuration
# ====================
BASE_URL = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
AGENT_MODEL = "claude-sonnet-4-20250514"              # 5 specialist Agents
CHIEF_THINKING_MODEL = "claude-opus-4-6-thinking"     # Chief A deep analysis
CHIEF_STANDARD_MODEL = "claude-opus-4-6"              # Chief B stable analysis
COMPARISON_MODEL = "claude-opus-4-6"                  # Comprehensive assessment

# ====================
# Data Source Configuration
# ====================
# "wind" or "akshare"
DATA_SOURCE = os.getenv("DATA_SOURCE", "wind")

# ====================
# Wind Lookback Depth
# ====================
MACRO_LOOKBACK_MONTHS = 24        # Fetch macro data for the past 24 months
YIELD_LOOKBACK_YEARS = 1          # Fetch yields for the past 1 year (not 3 years, to reduce structural downward shift noise)
FUTURES_LOOKBACK_DAYS = 60        # Fetch futures data for the past 60 trading days
FUNDING_LOOKBACK_DAYS = 60        # Fetch funding data for the past 60 trading days

# ====================
# Policy Rate (used for funding deviation calculation; update after rate cuts)
# ====================
POLICY_RATE_7D = 1.40             # Fallback value; priority is to fetch from Wind M0041371

# ====================
# Tavily Search Configuration
# ====================
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
TAVILY_MAX_RESULTS = 5            # Max results per search query

# ====================
# Check Configuration Completeness
# ====================
def check_config():
    """Check critical configuration at startup"""
    critical = []
    warnings = []
    if not API_KEY:
        critical.append("ANTHROPIC_API_KEY not set; please configure it in the .env file")
    if not TAVILY_API_KEY:
        warnings.append("TAVILY_API_KEY not set; search functionality will be unavailable (Agents B/D/E affected)")
    if DATA_SOURCE == "wind":
        try:
            from WindPy import w
        except ImportError:
            warnings.append("DATA_SOURCE=wind but WindPy is not installed; will auto-switch to akshare")

    if critical:
        print("[ERROR] Configuration check failed:")
        for issue in critical:
            print(f"  - {issue}")
        return False
    if warnings:
        print("[!] Configuration warnings:")
        for w in warnings:
            print(f"  - {w}")
    else:
        print("[OK] Configuration check passed")
    return True
