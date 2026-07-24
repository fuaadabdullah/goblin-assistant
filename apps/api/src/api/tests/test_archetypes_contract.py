from __future__ import annotations

from api.assistant_tools.registry import export_openai_tools
from api.config.archetypes import (
    DEEP_RESEARCH_CONTRACT,
    FINANCE_ANALYST_CONTRACT,
    GENERAL_ASSISTANT_CONTRACT,
    is_finance_analyst_mode,
    missing_deep_research_tools,
    missing_finance_analyst_tools,
    missing_general_assistant_tools,
)


def test_general_assistant_capability_labels_are_stable():
    assert tuple(GENERAL_ASSISTANT_CONTRACT.required_capabilities) == (
        "chat",
        "memory",
        "files",
        "projects",
        "tasks",
        "lightweight_research",
        "coding_help",
    )


def test_general_assistant_required_tool_set_includes_core_domains():
    tools = GENERAL_ASSISTANT_CONTRACT.required_tool_names
    assert "memory_recall" in tools
    assert "read_file" in tools
    assert "create_project" in tools
    assert "create_task" in tools
    assert "lightweight_research" in tools
    assert "git_status" in tools
    assert "github_get_repo" in tools


def test_general_assistant_contract_satisfied_by_exported_tool_payload():
    exported = export_openai_tools()
    missing = missing_general_assistant_tools(exported)
    assert missing == []


def test_deep_research_capability_labels_are_stable():
    assert tuple(DEEP_RESEARCH_CONTRACT.required_capabilities) == (
        "web_research",
        "citations",
        "source_verification",
        "pdfs",
        "academic_papers",
        "synthesis",
    )


def test_deep_research_required_tool_set_includes_core_domains():
    tools = DEEP_RESEARCH_CONTRACT.required_tool_names
    assert "web_search" in tools
    assert "academic_search" in tools
    assert "citation_graph" in tools
    assert "lightweight_research" in tools
    assert "verify_sources" in tools
    assert "research_pdf_extract" in tools


def test_deep_research_contract_satisfied_by_exported_tool_payload():
    exported = export_openai_tools()
    missing = missing_deep_research_tools(exported)
    assert missing == []


def test_finance_analyst_capability_labels_are_stable():
    assert tuple(FINANCE_ANALYST_CONTRACT.required_capabilities) == (
        "financial_memory",
        "market_data",
        "portfolio_analysis",
        "earnings_analysis",
        "financial_news",
        "lightweight_research",
    )


def test_finance_analyst_required_tool_set_includes_core_domains():
    tools = FINANCE_ANALYST_CONTRACT.required_tool_names
    assert "memory_recall" in tools
    assert "get_stock_quote" in tools
    assert "news_summarizer" in tools
    assert "portfolio_analyzer" in tools
    assert "lightweight_research" in tools


def test_finance_analyst_contract_satisfied_by_exported_tool_payload():
    exported = export_openai_tools()
    missing = missing_finance_analyst_tools(exported)
    assert missing == []


def test_finance_analyst_mode_predicate_does_not_expand_to_trading_forge():
    assert is_finance_analyst_mode("FINANCE_ANALYST") is True
    assert is_finance_analyst_mode("TRADING_FORGE") is False
