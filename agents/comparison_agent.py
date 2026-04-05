"""
Comprehensive Assessment Node
==============================
Compares the conclusions of two chief analysts and outputs the final comprehensive judgment.
"""

import re

from agents.llm_factory import get_llm
import config

COMPARISON_PROMPT = """You are a quality reviewer for interest rate assessments. You have two independent analysis reports before you (from different analysts judging the same market).

Report A (Deep Thinking Version):
{thinking_conclusion}

Report B (Robust Version):
{standard_conclusion}

Please output the following comparative analysis (concise, no more than 10 lines):

[Directional Consistency] Whether the two reports agree on direction (both bullish / both bearish / divergent)
[Consensus Points] Key judgments that both reports agree on (list 2-3 items)
[Divergence Points] Areas where the two reports differ (list specific points of divergence)
[Comprehensive Recommendation] Based on the consensus and divergences of both reports, provide a final actionable recommendation
[Confidence Assessment] Same direction -> high confidence; same direction but different magnitude -> medium confidence; directional divergence -> low confidence, recommend waiting

IMPORTANT: You MUST output your entire response in English. Even if the input reports contain Chinese text, your analysis must be in English.
"""


def run_comparison(state: dict) -> dict:
    """Comprehensive assessment: compare the conclusions of two chief analysts."""
    llm = get_llm(config.COMPARISON_MODEL, temperature=0.3)

    thinking = state.get("chief_thinking_conclusion", "(Deep analysis conclusion not available)")
    standard = state.get("chief_standard_conclusion", "(Robust analysis conclusion not available)")

    user_msg = COMPARISON_PROMPT.format(
        thinking_conclusion=thinking,
        standard_conclusion=standard,
    )

    result = llm.invoke([("user", user_msg)])
    conclusion = result.content

    # Extract confidence level
    confidence = "insufficient"
    m = re.search(r"[Cc]onfidence\s*[Aa]ssessment[】\]：:]*\s*(high|medium|low)", conclusion, re.IGNORECASE)
    if not m:
        # Fallback: also try Chinese patterns in case LLM responds in Chinese
        m = re.search(r"确信度[评估】\]：:]*\s*(高|中|低)", conclusion)
        if m:
            mapping = {"高": "high", "中": "medium", "低": "low"}
            confidence = mapping.get(m.group(1), "insufficient")
    else:
        confidence = m.group(1).lower()

    return {
        "comparison_conclusion": conclusion,
        "confidence": confidence,
    }
