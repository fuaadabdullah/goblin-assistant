from __future__ import annotations

from api.assistant_tools import skills  # noqa: F401
from api.assistant_tools.registry import (
    ToolDefinition,
    ToolParameter,
    export_openai_tools,
)
from api.config.archetypes import DEEP_RESEARCH_CONTRACT, GENERAL_ASSISTANT_CONTRACT


def test_omits_empty_required_from_openai_schema():
    definition = ToolDefinition(
        name="optional_only",
        description="All params optional",
        parameters=[
            ToolParameter(
                name="limit",
                type="integer",
                description="Optional limit",
                required=False,
            ),
        ],
    )

    schema = definition.to_openai_schema()

    assert schema["function"]["parameters"]["properties"]["limit"]["type"] == "integer"
    assert "required" not in schema["function"]["parameters"]


def test_includes_defaults_and_enums_in_openai_schema():
    definition = ToolDefinition(
        name="history",
        description="Fetch historical data",
        parameters=[
            ToolParameter(
                name="period",
                type="string",
                description="Lookback period",
                required=False,
                enum=["1mo", "1y"],
                default="1y",
            ),
        ],
    )

    schema = definition.to_openai_schema()

    period = schema["function"]["parameters"]["properties"]["period"]
    assert period["enum"] == ["1mo", "1y"]
    assert period["default"] == "1y"


def test_exported_financial_tools_include_model_inference_guidance():
    tools = {tool["function"]["name"]: tool["function"] for tool in export_openai_tools()}

    quote = tools["get_stock_quote"]
    assert "Use when" in quote["description"]
    assert "not for historical" in quote["description"]

    history_period = tools["get_price_history"]["parameters"]["properties"]["period"]
    assert history_period["default"] == "1y"
    assert history_period["enum"] == [
        "1d",
        "5d",
        "1mo",
        "3mo",
        "6mo",
        "1y",
        "2y",
        "5y",
        "ytd",
        "max",
    ]
    assert "Default: 1y" in history_period["description"]

    dcf_growth = tools["dcf_calculator"]["parameters"]["properties"]["growth_rate"]
    assert "decimal, not a percent" in dcf_growth["description"]

    portfolio_period = tools["portfolio_analyzer"]["parameters"]["properties"]["period"]
    assert portfolio_period["default"] == "1y"
    assert portfolio_period["enum"] == ["1mo", "3mo", "6mo", "1y", "2y", "5y"]

    assert "get_market_news" in tools
    assert "news_summarizer" in tools
    assert "search_filings" in tools
    assert "create_reminder" in tools
    assert "create_calendar_event" in tools
    market_news = tools["get_market_news"]
    assert market_news["parameters"]["properties"]["limit"]["default"] == 10
    assert "market-moving headlines" in market_news["description"]

    news_summary = tools["news_summarizer"]
    assert news_summary["parameters"]["properties"]["max_items"]["default"] == 6
    assert "concise synthesis" in news_summary["description"]

    filing_search = tools["search_filings"]
    assert filing_search["parameters"]["properties"]["limit"]["default"] == 5
    assert "structured filing metadata" in filing_search["description"]

    reminder_tool = tools["create_reminder"]
    assert reminder_tool["parameters"]["properties"]["status"]["default"] == "scheduled"

    calendar_tool = tools["create_calendar_event"]
    assert calendar_tool["parameters"]["properties"]["status"]["default"] == "planned"


def test_exported_tools_include_memory_recall_contract():
    tools = {tool["function"]["name"]: tool["function"] for tool in export_openai_tools()}
    assert "memory_recall" in tools
    memory_tool = tools["memory_recall"]
    assert "Read-only" in memory_tool["description"]
    assert memory_tool["parameters"]["properties"]["limit"]["default"] == 5


def test_exported_tools_include_project_tool_contracts():
    tools = {tool["function"]["name"]: tool["function"] for tool in export_openai_tools()}

    assert "create_project" in tools
    assert "list_projects" in tools
    assert "get_project_info" in tools

    create_project = tools["create_project"]
    create_required = set(create_project["parameters"]["required"])
    assert {"name", "path", "confirm"}.issubset(create_required)
    assert "template" not in create_required

    list_projects = tools["list_projects"]
    assert list_projects["parameters"]["properties"]["directory"]["default"] == "."
    assert list_projects["parameters"]["properties"]["max_depth"]["default"] == 4


def test_exported_tools_include_task_and_research_contracts():
    tools = {tool["function"]["name"]: tool["function"] for tool in export_openai_tools()}

    assert "create_task" in tools
    assert "list_tasks" in tools
    assert "update_task" in tools
    assert "complete_task" in tools
    assert "lightweight_research" in tools

    create_task_required = set(tools["create_task"]["parameters"]["required"])
    assert "title" in create_task_required

    list_tasks = tools["list_tasks"]
    assert list_tasks["parameters"]["properties"]["limit"]["default"] == 50

    lw_research = tools["lightweight_research"]
    assert lw_research["parameters"]["properties"]["max_sources"]["default"] == 6
    assert lw_research["parameters"]["properties"]["include_web"]["default"] is True
    assert lw_research["parameters"]["properties"]["include_academic"]["default"] is True
    assert "verify_sources" in tools
    assert "research_pdf_extract" in tools
    assert (
        tools["verify_sources"]["parameters"]["properties"]["strictness"]["default"] == "standard"
    )
    assert tools["research_pdf_extract"]["parameters"]["properties"]["max_chunks"]["default"] == 5


def test_exported_tools_satisfy_general_assistant_required_set():
    tool_names = {tool["function"]["name"] for tool in export_openai_tools()}
    missing = sorted(GENERAL_ASSISTANT_CONTRACT.required_tool_names - tool_names)
    assert missing == []


def test_exported_tools_satisfy_deep_research_required_set():
    tool_names = {tool["function"]["name"] for tool in export_openai_tools()}
    missing = sorted(DEEP_RESEARCH_CONTRACT.required_tool_names - tool_names)
    assert missing == []
