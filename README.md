# cgb-curve-forecast

A multi-agent system built on LangGraph that predicts Chinese Government Bond (CGB) yield curve direction and shape, outputting allocation-oriented investment recommendations.

## How It Works

```
5 Specialist Agents (parallel)     Dual Chief Analysts (parallel)     Final
┌─ Agent A: Macro Cycle      ─┐   ┌─ Chief Thinking (deep)    ─┐
├─ Agent B: Funding & Policy  ─┤   │                             ├─ Comparison ─→ Output
├─ Agent C: Market Signals    ─┼──►│                             │
├─ Agent D: Asset Allocation  ─┤   └─ Chief Standard (stable)  ─┘
└─ Agent E: External Shocks   ─┘
```

Each specialist agent outputs a **tri-state signal**: `bullish` / `bearish` / `none` (no signal ≠ neutral). Two independent chief analysts synthesize signals in parallel, then a comparison node cross-validates their conclusions and produces the final assessment.

## Key Design Principles

- **Tri-state signals**: `none` means "this dimension has nothing to contribute" — the chief ignores it entirely
- **Honest uncertainty**: Aligned signals → give direction; conflicting signals → say "uncertain"
- **No mean reversion**: China's rate center is structurally declining; historical percentiles don't predict future levels
- **Three-layer drivers**: Long-term (policy rate) → Medium-term (data marginal changes) → Short-term (catalysts)
- **Allocation perspective**: Focus on medium-term trends, not short-term trading

## Output Example

```
Signal Summary by Dimension:
  Agent A (Macro Cycle):  none — data vacuum period
  Agent B (Funding):      bullish — accommodative policy, rate cut expectations
  Agent C (Market):       bullish — MA bullish alignment, MACD golden cross
  Agent D (Allocation):   bearish — liability scarcity regime
  Agent E (External):     none — no major events

═══ Comprehensive Assessment ═══
[Directional Consistency] Both reports bullish, aligned
[Consensus Points] 1) Policy easing is the dominant driver  2) Avoid ultra-long end (30Y)
[Confidence Assessment] Medium-high confidence
```

## Quick Start

### Prerequisites

- Python 3.11+
- [Wind terminal](https://www.wind.com.cn/) (primary data) or AKShare (free backup)
- Anthropic API key (Claude)
- Tavily API key (for search, optional but recommended)

### Installation

```bash
git clone https://github.com/gogoahead233-art/cgb-curve-forecast.git
cd cgb-curve-forecast

pip install -r requirements.txt

cp .env.example .env
# Edit .env with your API keys
```

### Run

```bash
# Full analysis
python main.py

# Data quality check
python tests/test_data_quality.py
```

### Configuration

Edit `.env`:

```bash
ANTHROPIC_API_KEY=sk-ant-...        # Required
TAVILY_API_KEY=tvly-...             # Optional but recommended
DATA_SOURCE=wind                     # "wind" or "akshare"
# ANTHROPIC_BASE_URL=https://...    # Optional: custom API endpoint
```

## Architecture

| Component | Model | Temperature | Role |
|-----------|-------|-------------|------|
| Agent A-E | claude-sonnet-4 | 0 | Data retrieval + signal generation |
| Chief Thinking | claude-opus-4-6-thinking | 1 (required) | Deep reasoning with extended thinking |
| Chief Standard | claude-opus-4-6 | 0.3 | Stable, consistent analysis |
| Comparison | claude-opus-4-6 | 0.3 | Cross-validate dual conclusions |

## Data Sources

### Wind (Primary)
| Category | Indicators |
|----------|-----------|
| Macro | CPI (M0000612), PMI (M0017126), Social Financing (M5201945), M2 (M0001385) |
| Yields | 1Y (S0059744), 10Y (S0059749), 30Y (S0059751) |
| Funding | DR007 (M0041653), Policy Rate (M0041371), Reverse Repo (M0062063/M0062065) |
| Futures | T.CFE (10Y), TL.CFE (30Y) |
| External | US 10Y (G0000891), SSE Index (000001.SH) |

### AKShare (Free Backup)
Automatically used when Wind is unavailable. Some data may be delayed or missing.

## Project Structure

```
├── config.py              # Configuration (models, data source, lookback periods)
├── state.py               # LangGraph state definition
├── graph.py               # Graph orchestration (fan-out → fan-in)
├── main.py                # Entry point
├── agents/
│   ├── macro_agent.py     # Agent A: Macro cycle
│   ├── funding_agent.py   # Agent B: Funding & policy
│   ├── market_agent.py    # Agent C: Technical signals
│   ├── allocation_agent.py# Agent D: Asset allocation
│   ├── external_agent.py  # Agent E: External shocks
│   ├── chief_agent.py     # Dual chief analysts
│   ├── comparison_agent.py# Cross-validation node
│   ├── output_parser.py   # Robust JSON extraction from LLM output
│   └── llm_factory.py     # LLM instance factory
├── tools/
│   ├── wind_tools.py      # Wind data functions
│   ├── akshare_tools.py   # AKShare backup functions
│   ├── calc_tools.py      # Technical indicators & curve shape
│   ├── search_tools.py    # Tavily search wrapper
│   └── data_tools.py      # Auto-switch between Wind/AKShare
├── prompts/               # System prompts for all agents
└── tests/
    └── test_data_quality.py  # Data validation + Tavily cross-check
```

## License

[MIT](LICENSE)

## Disclaimer

This system is for research and educational purposes only. It does not constitute investment advice. Always conduct your own analysis before making investment decisions.
