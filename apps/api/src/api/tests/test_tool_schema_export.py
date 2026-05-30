from __future__ import annotations

from api.assistant_tools.registry import (
    ToolDefinition,
    ToolParameter,
    export_openai_tools,
)


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
