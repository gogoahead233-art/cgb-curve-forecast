"""
Agent Output Parser
====================
Extracts JSON from LLM output, shared by all Agents.
"""

import json
import re


def parse_agent_output(text: str, default_extra: dict | None = None) -> dict:
    """Parse JSON from LLM text output.

    Supports multiple output formats:
    - Pure JSON
    - ```json ... ``` code blocks
    - Mixed text description + JSON (extracts the JSON portion)
    Returns a default output with signal="none" when parsing fails.
    """
    fallback = {
        "signal": "none",
        "reasoning": f"Output parsing failed, raw content: {text[:200]}",
        "data_summary": "",
    }
    if default_extra:
        fallback.update(default_extra)

    # Method 1: Extract ```json ... ``` blocks using regex
    blocks = re.findall(r"```json\s*(.*?)```", text, re.DOTALL)
    if not blocks:
        # Method 2: Extract any ``` ... ``` blocks
        blocks = re.findall(r"```\s*(.*?)```", text, re.DOTALL)

    for block in blocks:
        parsed = _try_parse(block.strip())
        if parsed:
            return parsed

    # Method 3: Find content between the first { and the last }
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace > first_brace:
        candidate = text[first_brace:last_brace + 1]
        parsed = _try_parse(candidate)
        if parsed:
            return parsed

    # Method 4: Scan line by line, looking for JSON fragments containing "signal"
    for line_start in range(len(text)):
        if text[line_start] == "{":
            for line_end in range(len(text) - 1, line_start, -1):
                if text[line_end] == "}":
                    candidate = text[line_start:line_end + 1]
                    parsed = _try_parse(candidate)
                    if parsed:
                        return parsed
                    break

    return fallback


def _try_parse(text: str) -> dict | None:
    """Attempt to parse JSON text, returns dict if successful and contains 'signal' field."""
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict) and "signal" in parsed:
            return parsed
    except (json.JSONDecodeError, ValueError):
        pass
    return None
