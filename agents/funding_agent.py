"""
Agent B: Funding Supply-Demand + Policy Expectations
=====================================================
ReAct Agent using funding data, yield curve, and search tools.
"""

from langgraph.prebuilt import create_react_agent

from agents.llm_factory import get_llm
from agents.output_parser import parse_agent_output
from tools.data_tools import get_data_tools
from tools.search_tools import search_policy_news, search_bond_supply
from prompts.funding_prompt import FUNDING_SYSTEM_PROMPT


def create_funding_agent():
    data = get_data_tools()
    tools = [
        data["get_funding_data"],
        data["get_yield_curve"],
        search_policy_news,
        search_bond_supply,
    ]
    llm = get_llm()
    return create_react_agent(llm, tools, prompt=FUNDING_SYSTEM_PROMPT)


def run_funding_agent(state: dict) -> dict:
    """LangGraph node function: run funding analysis Agent."""
    agent = create_funding_agent()
    query = state.get("query", "Analyze the implications of current funding conditions and policy expectations on interest rates")
    result = agent.invoke({"messages": [("user", query)]})
    last_msg = result["messages"][-1].content
    return {"agent_b_output": parse_agent_output(last_msg)}
