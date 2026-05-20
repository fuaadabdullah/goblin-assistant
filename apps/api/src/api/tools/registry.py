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


def export_tools_for_provider(provider_id: str) -> List[Dict[str, Any]]:
    """Export tools in the format expected by a specific provider.

    Currently all supported providers (OpenAI, Anthropic, Gemini, Groq)
    accept the OpenAI tools format, so this is a single code path.
    """
    return export_openai_tools()
