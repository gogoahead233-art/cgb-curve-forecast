"""
Agent C: Market Signals (Technical Analysis)
=============================================
ReAct Agent using futures data and technical indicator calculation tools.
"""

from langgraph.prebuilt import create_react_agent

from agents.llm_factory import get_llm
from agents.output_parser import parse_agent_output
from tools.data_tools import get_data_tools
from tools.calc_tools import calc_tech_signals, calc_curve_shape
from prompts.market_prompt import MARKET_SYSTEM_PROMPT


def create_market_agent():
    data = get_data_tools()
    tools = [data["get_futures_data"], calc_tech_signals, calc_curve_shape]
    llm = get_llm()
    return create_react_agent(llm, tools, prompt=MARKET_SYSTEM_PROMPT)


def run_market_agent(state: dict) -> dict:
    """LangGraph node function: run market signals Agent."""
    agent = create_market_agent()
    query = state.get("query", "Analyze treasury futures technical indicators and curve shape")
    result = agent.invoke({"messages": [("user", query)]})
    last_msg = result["messages"][-1].content
    parsed = parse_agent_output(last_msg, default_extra={"curve_shape": "range_bound"})
    if "curve_shape" not in parsed:
        parsed["curve_shape"] = "range_bound"
    return {"agent_c_output": parsed}
