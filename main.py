"""
Main Entry
==========
Runs the complete rate analysis workflow.
"""

from config import check_config
from graph import app


def run_analysis(query: str | None = None):
    """Run full analysis and output conclusions."""
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    if query is None:
        query = f"Today is {today}. Analyze the current government bond market, predict yield direction and curve shape."
    elif "Today is" not in query:
        query = f"Today is {today}. {query}"

    print("=" * 60)
    print("China Government Bond Multi-Agent Analysis System")
    print("=" * 60)
    print(f"\nAnalysis topic: {query}\n")

    print("Running analysis...")
    print("  Phase 1: 5 specialist Agents analyzing in parallel")
    print("  Phase 2: Dual chiefs assessing in parallel (Thinking Edition + Standard Edition)")
    print("  Phase 3: Comprehensive assessment")
    print()

    result = app.invoke({
        "query": query,
        "messages": [],
    })

    # === Signal Summary by Dimension ===
    print("-" * 60)
    print("Signal Summary by Dimension:")
    print("-" * 60)

    agent_names = {
        "agent_a_output": "Agent A (Macro Cycle)",
        "agent_b_output": "Agent B (Funding Supply-Demand)",
        "agent_c_output": "Agent C (Market Signals)",
        "agent_d_output": "Agent D (Asset Allocation)",
        "agent_e_output": "Agent E (External Environment)",
    }

    for key, name in agent_names.items():
        output = result.get(key)
        if output:
            signal = output.get("signal", "N/A")
            reasoning = output.get("reasoning", "")[:80]
            print(f"  {name}: {signal} — {reasoning}")
        else:
            print(f"  {name}: No output received")

    # === Deep Analysis (Thinking Edition) ===
    print()
    print("=" * 60)
    print("Deep Analysis (Thinking Edition)")
    print("=" * 60)
    print()
    print(result.get("chief_thinking_conclusion", "No conclusion received"))

    # === Stable Analysis (Standard Edition) ===
    print()
    print("=" * 60)
    print("Stable Analysis (Standard Edition)")
    print("=" * 60)
    print()
    print(result.get("chief_standard_conclusion", "No conclusion received"))

    # === Comprehensive Assessment (Final Conclusion) ===
    print()
    print()
    border = "=" * 60
    print(border)
    print(f"{'=== Comprehensive Assessment ===':^60}")
    print(border)
    print()
    print(result.get("comparison_conclusion", "No comprehensive assessment conclusion received"))
    print()
    print(border)


if __name__ == "__main__":
    import sys

    if not check_config():
        sys.exit(1)

    # Pre-initialize Wind connection in Wind mode to avoid race conditions during parallel execution
    import config as _cfg
    if _cfg.DATA_SOURCE == "wind":
        try:
            from tools.wind_tools import init_wind
            print("Connecting to Wind...")
            init_wind()
            print("Wind connected successfully")
        except (ImportError, ConnectionError, OSError) as e:
            print(f"Wind connection failed: {e}")
            print("Auto-switching to AKShare")
            _cfg.DATA_SOURCE = "akshare"

    run_analysis()
