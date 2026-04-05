"""
LangGraph State Definition
==========================
Defines the state structure for the entire Graph, including output formats for each Agent.
"""

from typing import TypedDict, Annotated, Optional
from langgraph.graph import add_messages


class AgentOutput(TypedDict):
    signal: str       # "bullish" | "bearish" | "none"
    reasoning: str    # Analysis reasoning process
    data_summary: str # Key data summary


class MarketAgentOutput(AgentOutput):
    curve_shape: str  # "bull_flat" | "bull_steep" | "bear_flat" | "bear_steep" | "range_bound"


class RateAnalysisState(TypedDict):
    messages: Annotated[list, add_messages]
    query: str
    agent_a_output: Optional[AgentOutput]
    agent_b_output: Optional[AgentOutput]
    agent_c_output: Optional[MarketAgentOutput]
    agent_d_output: Optional[AgentOutput]
    agent_e_output: Optional[AgentOutput]
    # Dual chiefs
    chief_thinking_conclusion: Optional[str]
    chief_standard_conclusion: Optional[str]
    # Comprehensive assessment
    comparison_conclusion: Optional[str]
    confidence: Optional[str]       # "high" | "medium" | "low" | "insufficient"
