# China Interest Rate Prediction Multi-Agent System

## Project Overview
A LangGraph-based multi-agent system that predicts Chinese government bond yield direction (1Y/10Y/30Y) and curve shape (bull flat/bull steep/bear flat/bear steep), outputting allocation-oriented interest rate bond investment recommendations.

## Architecture
5 specialist Agents analyze in parallel → Dual Chief Analysts synthesize → Comparison node outputs final conclusion + reasoning chain + investment advice

- Agent A: Macro Cycle (fundamentals + credit cycle)
- Agent B: Funding Supply-Demand (DR007 + PBoC operations + policy expectations)
- Agent C: Market Signals (futures + MA/MACD + volume-price + curve shape)
- Agent D: Asset Allocation (asset scarcity vs liability scarcity + stock-bond rotation)
- Agent E: External Environment (geopolitics + Fed + domestic policy shocks)
- Chief Thinking: Deep reasoning with extended thinking
- Chief Standard: Stable reasoning
- Comparison: Cross-validates dual chief conclusions → final assessment

Each Agent outputs a tri-state signal: "bullish" / "bearish" / "none" (no signal ≠ neutral)

## Tech Stack
- Python 3.11+
- LangGraph (state management / parallel / conditional routing)
- LangChain + ChatAnthropic (LLM calls)
- WindPy (primary data source) / AKShare (backup)
- Tavily (search: policy/events/market dynamics)
- pandas + numpy (technical indicator calculation)

## LLM Configuration
```python
# Call Claude API (configurable via .env)
BASE_URL = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
API_KEY = os.getenv("ANTHROPIC_API_KEY")  # Read from .env
AGENT_MODEL = "claude-sonnet-4-20250514"
CHIEF_THINKING_MODEL = "claude-opus-4-6-thinking"
CHIEF_STANDARD_MODEL = "claude-opus-4-6"
COMPARISON_MODEL = "claude-opus-4-6"
```
IMPORTANT: API key should only be in the .env file, never in code files.

## Key Design Principles
1. Tri-state signals: Each Agent outputs bullish/bearish/none. "none" means that dimension has no impact
2. Honest uncertainty: Give conclusion when signals align, say "uncertain" when signals conflict
3. Three-layer drivers: Long-term follows policy rate direction, medium-term follows marginal data changes, short-term follows catalysts/disturbances
4. No mean reversion: China's rate center is structurally declining, cannot use historical percentiles to predict future
5. Allocation perspective: Focus on medium-term trends, no short-term trading advice

## Project Structure
```
langgraph/
├── CLAUDE.md
├── .env                       # API keys (git ignored)
├── requirements.txt
├── config.py                  # Configuration
├── state.py                   # LangGraph State
├── graph.py                   # Graph orchestration
├── main.py                    # Entry point
├── agents/                    # 8 Agents (5 specialist + 2 chief + 1 comparison)
├── tools/                     # Data + calculation + search tools
├── prompts/                   # System Prompts
├── tests/                     # Tests
└── docs/                      # Detailed documentation
    ├── PLAN.md                # Development plan
    └── DESIGN.md              # Detailed design
```

## Commands
```bash
# Install dependencies
pip install -r requirements.txt

# Run full analysis
python main.py

# Data quality test
python tests/test_data_quality.py
```

## Wind Data Codes (Verified)
- Macro: M0000612(CPI), M0017126(PMI), M5201945(Social financing monthly), M0001385(M2)
- Yields: S0059744(1Y), S0059749(10Y), S0059751(30Y)
- Funding: M0041653(DR007), M0062063/M0062065(Reverse repo injection/maturity), M0041371(Policy rate)
- Futures: T.CFE(10Y futures), TL.CFE(30Y futures) — use w.wsd() for close,volume,oi
- External: G0000891(US 10Y), 000001.SH(SSE Composite Index)

## Notes
- Wind API requires Wind terminal to be open and logged in
- Tavily search uses Chinese keywords for Chinese sources
- LangGraph fan-out/fan-in: 5 Agents parallel → dual chiefs parallel → comparison → END
- No report files generated, output is plain text to terminal
- No frontend, focus on Agent logic first
