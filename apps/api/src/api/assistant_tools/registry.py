"""
Tool registry for Goblin Assistant.

Defines tool schemas and maps tool names to handler functions.
Exports tools in OpenAI-compatible JSON Schema format for native
function calling.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Dict, List, Optional


@dataclass
class ToolParameter:
    """Single parameter in a tool's input schema."""

    name: str
    type: str  # "string", "number", "integer", "boolean", "array", "object"
    description: str
    required: bool = True
    enum: Optional[List[str]] = None
    default: Any = None
    items: Optional[Dict[str, Any]] = None  # For array types


@dataclass
class ToolDefinition:
    """A registered tool with schema and handler."""

    name: str
    description: str
    parameters: List[ToolParameter] = field(default_factory=list)
    handler: Optional[Callable[..., Coroutine[Any, Any, Dict[str, Any]]]] = None
    category: str = "finance"

    def to_openai_schema(self) -> Dict[str, Any]:
        """Export as OpenAI function-calling tool format."""
        properties: Dict[str, Any] = {}
        required: List[str] = []

        for param in self.parameters:
            prop: Dict[str, Any] = {
                "type": param.type,
                "description": param.description,
            }
            if param.enum:
                prop["enum"] = param.enum
            if param.default is not None:
                prop["default"] = param.default
            if param.items:
                prop["items"] = param.items
            properties[param.name] = prop
            if param.required:
                required.append(param.name)

        parameters: Dict[str, Any] = {
            "type": "object",
            "properties": properties,
        }
        if required:
            parameters["required"] = required

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": parameters,
            },
        }


@dataclass(frozen=True)
class ToolSpec:
    """Provider-agnostic tool specification used by router/runtime code."""

    name: str
    description: str
    input_schema: Dict[str, Any]
    category: str = "finance"

    def to_openai_schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema,
            },
        }


# ---------------------------------------------------------------------------
# Global registry
# ---------------------------------------------------------------------------

TOOL_REGISTRY: Dict[str, ToolDefinition] = {}


def register_tool(definition: ToolDefinition) -> ToolDefinition:
    """Register a tool definition. Returns the definition for chaining."""
    TOOL_REGISTRY[definition.name] = definition
    return definition


def get_tool(name: str) -> Optional[ToolDefinition]:
    return TOOL_REGISTRY.get(name)


def export_openai_tools() -> List[Dict[str, Any]]:
    """Export all registered tools in OpenAI function-calling format."""
    return [tool.to_openai_schema() for tool in TOOL_REGISTRY.values()]


def export_tool_specs() -> List[ToolSpec]:
    """Export tool specifications in a provider-neutral contract."""
    specs: List[ToolSpec] = []
    for tool in TOOL_REGISTRY.values():
        schema = tool.to_openai_schema()["function"]["parameters"]
        specs.append(
            ToolSpec(
                name=tool.name,
                description=tool.description,
                input_schema=schema,
                category=tool.category,
            )
        )
    return specs


def format_tool_specs_for_provider(
    tool_specs: List[ToolSpec],
    provider_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Translate provider-neutral tool specs into provider payload format.

    For now all providers use OpenAI-compatible function tool payloads.
    Keeping this translation boundary here prevents OpenAI schema leakage
    into chat route and orchestration internals.
    """
    _ = provider_id
    return [spec.to_openai_schema() for spec in tool_specs]


def export_tools_for_provider(provider_id: Optional[str]) -> List[Dict[str, Any]]:
    """Export tools in the format expected by a specific provider.

    Currently all supported providers (OpenAI, Anthropic, Gemini, Groq)
    accept the OpenAI tools format, so this is a single code path.
    """
    return format_tool_specs_for_provider(export_tool_specs(), provider_id=provider_id)
