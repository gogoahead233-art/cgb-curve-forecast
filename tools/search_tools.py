"""
Search Tools
=============
Wraps Tavily search, providing 5 specialized search functions.
"""

from langchain_core.tools import tool
import config


def _tavily_search(queries: list[str], max_results: int = 3) -> str:
    """Execute Tavily search and return formatted summaries."""
    if not config.TAVILY_API_KEY:
        return "Tavily API Key not configured. Search unavailable. Please set TAVILY_API_KEY in .env."

    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=config.TAVILY_API_KEY)
    except Exception as e:
        return f"Tavily initialization failed: {e}"

    all_results = []
    for query in queries:
        try:
            response = client.search(
                query=query,
                max_results=max_results,
                search_depth="basic",
                include_answer=True,
            )
            if response.get("answer"):
                all_results.append(f"[{query}] {response['answer']}")
            for r in response.get("results", [])[:max_results]:
                title = r.get("title", "")
                content = r.get("content", "")[:200]
                pub_date = r.get("published_date", "")
                date_tag = f" ({pub_date})" if pub_date else ""
                all_results.append(f"- {title}{date_tag}: {content}")
        except Exception as e:
            all_results.append(f"[{query}] Search failed: {e}")

    return "\n".join(all_results) if all_results else "No significant recent information found"


@tool
def search_policy_news() -> str:
    """Search for PBOC monetary policy operations and policy developments."""
    return _tavily_search([
        "中国央行公开市场操作 最新",
        "中国货币政策 降息降准 预期",
        "央行货币政策执行报告 定调",
    ])


@tool
def search_bond_supply() -> str:
    """Search for government bond supply plans and issuance updates."""
    return _tavily_search([
        "2026年国债发行计划",
        "2026年特别国债 地方债 供给",
    ])


@tool
def search_external_events() -> str:
    """Search for Fed developments, geopolitical risks, and other external events."""
    return _tavily_search([
        "美联储利率决议 最新",
        "地缘政治风险 中美关系",
    ])


@tool
def search_allocation_dynamics() -> str:
    """Search for asset allocation dynamics: asset scarcity, wealth management, institutional positioning."""
    return _tavily_search([
        "债券市场 资产荒 负债荒",
        "银行理财规模 配置动态",
    ])


@tool
def search_policy_shock() -> str:
    """Search for major domestic policy shocks: regulatory statements, Politburo meetings, etc."""
    return _tavily_search([
        "政治局会议 经济 最新 2026",
        "央行 约谈 债市 2026",
    ])
