"""
Agent D: Asset Allocation
==========================
ReAct Agent using stock index data and allocation dynamics search.
"""

from langgraph.prebuilt import create_react_agent

from agents.llm_factory import get_llm
from agents.output_parser import parse_agent_output
from tools.data_tools import get_data_tools
from tools.search_tools import search_allocation_dynamics
from prompts.allocation_prompt import ALLOCATION_SYSTEM_PROMPT


def create_allocation_agent():
    data = get_data_tools()
    tools = [data["get_stock_index"], search_allocation_dynamics]
    llm = get_llm()
    return create_react_agent(llm, tools, prompt=ALLOCATION_SYSTEM_PROMPT)


def run_allocation_agent(state: dict) -> dict:
    """LangGraph node function: run asset allocation Agent."""
    agent = create_allocation_agent()
    query = state.get("query", "Analyze the impact of asset allocation dynamics on the bond market")
    result = agent.invoke({"messages": [("user", query)]})
    last_msg = result["messages"][-1].content
    return {"agent_d_output": parse_agent_output(last_msg)}
