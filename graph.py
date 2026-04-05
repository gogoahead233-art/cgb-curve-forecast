"""
LangGraph Orchestration
=======================
5 Agents in parallel -> Dual chiefs in parallel -> Comprehensive assessment -> END
"""

from langgraph.graph import StateGraph, START, END

from state import RateAnalysisState
from agents.macro_agent import run_macro_agent
from agents.funding_agent import run_funding_agent
from agents.market_agent import run_market_agent
from agents.allocation_agent import run_allocation_agent
from agents.external_agent import run_external_agent
from agents.chief_agent import run_chief_thinking, run_chief_standard
from agents.comparison_agent import run_comparison


def build_graph():
    graph = StateGraph(RateAnalysisState)

    # 5 specialist Agents
    graph.add_node("agent_a", run_macro_agent)
    graph.add_node("agent_b", run_funding_agent)
    graph.add_node("agent_c", run_market_agent)
    graph.add_node("agent_d", run_allocation_agent)
    graph.add_node("agent_e", run_external_agent)

    # Dual chiefs
    graph.add_node("chief_thinking", run_chief_thinking)
    graph.add_node("chief_standard", run_chief_standard)

    # Comprehensive assessment
    graph.add_node("comparison", run_comparison)

    # Fan-out: START -> 5 Agents in parallel
    graph.add_edge(START, "agent_a")
    graph.add_edge(START, "agent_b")
    graph.add_edge(START, "agent_c")
    graph.add_edge(START, "agent_d")
    graph.add_edge(START, "agent_e")

    # 5 Agents -> Dual chiefs in parallel
    graph.add_edge("agent_a", "chief_thinking")
    graph.add_edge("agent_b", "chief_thinking")
    graph.add_edge("agent_c", "chief_thinking")
    graph.add_edge("agent_d", "chief_thinking")
    graph.add_edge("agent_e", "chief_thinking")

    graph.add_edge("agent_a", "chief_standard")
    graph.add_edge("agent_b", "chief_standard")
    graph.add_edge("agent_c", "chief_standard")
    graph.add_edge("agent_d", "chief_standard")
    graph.add_edge("agent_e", "chief_standard")

    # Dual chiefs -> Comprehensive assessment
    graph.add_edge("chief_thinking", "comparison")
    graph.add_edge("chief_standard", "comparison")

    # Comprehensive assessment -> END
    graph.add_edge("comparison", END)

    return graph.compile()


# Compiled app instance
app = build_graph()
