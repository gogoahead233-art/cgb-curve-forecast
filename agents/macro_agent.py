"""
Agent A: Macro Cycle Analysis
==============================
ReAct Agent using macroeconomic data and trend calculation tools.
"""

from langgraph.prebuilt import create_react_agent

from agents.llm_factory import get_llm
from agents.output_parser import parse_agent_output
from tools.data_tools import get_data_tools
from tools.calc_tools import calc_trend_direction
from prompts.macro_prompt import MACRO_SYSTEM_PROMPT


def create_macro_agent():
    data = get_data_tools()
    tools = [data["get_macro_data"], calc_trend_direction]
    llm = get_llm()
    return create_react_agent(llm, tools, prompt=MACRO_SYSTEM_PROMPT)


def run_macro_agent(state: dict) -> dict:
    """LangGraph node function: run macro analysis Agent."""
    agent = create_macro_agent()
    query = state.get("query", "Analyze the implications of current macroeconomic conditions on interest rates")
    result = agent.invoke({"messages": [("user", query)]})
    last_msg = result["messages"][-1].content
    return {"agent_a_output": parse_agent_output(last_msg)}
