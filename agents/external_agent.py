"""
Agent E: External Environment and Policy Shocks
=================================================
ReAct Agent using US Treasury data and external event/policy search.
"""

from langgraph.prebuilt import create_react_agent

from agents.llm_factory import get_llm
from agents.output_parser import parse_agent_output
from tools.data_tools import get_data_tools
from tools.search_tools import search_external_events, search_policy_shock
from prompts.external_prompt import EXTERNAL_SYSTEM_PROMPT


def create_external_agent():
    data = get_data_tools()
    tools = [data["get_us_treasury"], search_external_events, search_policy_shock]
    llm = get_llm()
    return create_react_agent(llm, tools, prompt=EXTERNAL_SYSTEM_PROMPT)


def run_external_agent(state: dict) -> dict:
    """LangGraph node function: run external environment Agent."""
    agent = create_external_agent()
    query = state.get("query", "Analyze the impact of external environment and policy shocks on the interest rate market")
    result = agent.invoke({"messages": [("user", query)]})
    last_msg = result["messages"][-1].content
    return {"agent_e_output": parse_agent_output(last_msg)}
