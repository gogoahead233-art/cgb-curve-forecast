"""
Dual Chief Analyst
==================
Two independent chief nodes: thinking version (deep reasoning) and standard version (robust reasoning).
They share the same prompt, receive the same Agent outputs, and independently generate conclusions.
"""

import json
import re

from agents.llm_factory import get_llm
from prompts.chief_prompt import CHIEF_SYSTEM_PROMPT
import config


def _build_chief_input(state: dict) -> str:
    """Build input text for the chief analyst (shared by both chiefs)."""
    agent_outputs = {
        "Agent A (Macro Cycle)": state.get("agent_a_output"),
        "Agent B (Funding Supply-Demand)": state.get("agent_b_output"),
        "Agent C (Market Signals)": state.get("agent_c_output"),
        "Agent D (Asset Allocation)": state.get("agent_d_output"),
        "Agent E (External Environment)": state.get("agent_e_output"),
    }

    input_parts = []
    for name, output in agent_outputs.items():
        if output:
            input_parts.append(f"### {name}\n{json.dumps(output, ensure_ascii=False, indent=2)}")
        else:
            input_parts.append(f"### {name}\nNo output received (treated as none)")

    query = state.get("query", "")

    return f"""{query}

Below are the assessment conclusions from 5 specialist analysts:

{chr(10).join(input_parts)}

Based on the above information, please provide your comprehensive judgment and investment recommendations."""


def _extract_content(result) -> str:
    """Extract text content from LLM return value (compatible with both thinking and non-thinking models)."""
    raw = result.content
    if isinstance(raw, list):
        text_parts = []
        for block in raw:
            if hasattr(block, "type") and block.type == "text":
                text_parts.append(block.text)
            elif isinstance(block, dict) and block.get("type") == "text":
                text_parts.append(block["text"])
        return "".join(text_parts) if text_parts else str(raw)
    return raw


def run_chief_thinking(state: dict) -> dict:
    """Chief A: Deep thinking version (claude-opus-4-6-thinking)."""
    llm = get_llm(config.CHIEF_THINKING_MODEL, thinking=True)
    user_msg = _build_chief_input(state)

    result = llm.invoke([
        ("system", CHIEF_SYSTEM_PROMPT),
        ("user", user_msg),
    ])

    return {"chief_thinking_conclusion": _extract_content(result)}


def run_chief_standard(state: dict) -> dict:
    """Chief B: Robust version (claude-opus-4-6)."""
    llm = get_llm(config.CHIEF_STANDARD_MODEL, temperature=0.3)
    user_msg = _build_chief_input(state)

    result = llm.invoke([
        ("system", CHIEF_SYSTEM_PROMPT),
        ("user", user_msg),
    ])

    return {"chief_standard_conclusion": _extract_content(result)}
