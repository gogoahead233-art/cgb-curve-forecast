"""
LLM Factory
=============
Unified creation of ChatAnthropic instances.
"""

from langchain_anthropic import ChatAnthropic
import config


def get_llm(model: str | None = None, temperature: float = 0, thinking: bool = False) -> ChatAnthropic:
    model = model or config.AGENT_MODEL
    kwargs = {
        "model": model,
        "api_key": config.API_KEY,
        "base_url": config.BASE_URL,
        "max_tokens": 16000 if thinking else 4096,
    }

    if thinking:
        # Thinking model requires temperature=1 and a thinking budget
        kwargs["temperature"] = 1
        kwargs["thinking"] = {"type": "enabled", "budget_tokens": 10000}
    else:
        kwargs["temperature"] = temperature

    return ChatAnthropic(**kwargs)
