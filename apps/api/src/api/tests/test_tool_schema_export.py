from __future__ import annotations

from api.assistant_tools.registry import ToolDefinition, ToolParameter


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
