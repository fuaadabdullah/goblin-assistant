"""Machine-readable assistant archetype contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, FrozenSet, Iterable, List, Optional, Sequence, Set


@dataclass(frozen=True)
class AssistantArchetypeContract:
    """Runtime contract for an assistant archetype."""

    archetype_id: str
    required_capabilities: Sequence[str]
    required_tool_names: FrozenSet[str]


GENERAL_ASSISTANT_CONTRACT = AssistantArchetypeContract(
    archetype_id="general_assistant",
    required_capabilities=(
        "chat",
        "memory",
        "files",
        "projects",
        "tasks",
        "lightweight_research",
        "coding_help",
    ),
    required_tool_names=frozenset(
        {
            # Memory
            "memory_recall",
            # Files
            "read_file",
            "write_file",
            "search_files",
            "list_directory",
            # Projects
            "create_project",
            "get_project_info",
            "list_projects",
            # Tasks
            "create_task",
            "list_tasks",
            "update_task",
            "complete_task",
            # Lightweight research
            "lightweight_research",
            "web_search",
            "academic_search",
            # Coding help (bounded to file/project/git/github tools)
            "git_add",
            "git_branch",
            "git_checkout",
            "git_clone",
            "git_commit",
            "git_diff",
            "git_log",
            "git_pull",
            "git_push",
            "git_status",
            "github_add_comment",
            "github_create_issue",
            "github_create_pr",
            "github_get_file",
            "github_get_issue",
            "github_get_pr",
            "github_get_repo",
            "github_list_issues",
            "github_list_prs",
            "github_list_repos",
            "github_search_code",
        }
    ),
)


DEEP_RESEARCH_CONTRACT = AssistantArchetypeContract(
    archetype_id="deep_research",
    required_capabilities=(
        "web_research",
        "citations",
        "source_verification",
        "pdfs",
        "academic_papers",
        "synthesis",
    ),
    required_tool_names=frozenset(
        {
            "web_search",
            "academic_search",
            "citation_graph",
            "lightweight_research",
            "verify_sources",
            "research_pdf_extract",
        }
    ),
)


def is_general_assistant_mode(mode: Optional[str]) -> bool:
    """True when request should satisfy General Assistant minimum contract."""
    if mode is None:
        return True
    return mode.strip().upper() == "GENERAL_ASSISTANT"


def is_deep_research_mode(mode: Optional[str]) -> bool:
    """True when request should satisfy Deep Research minimum contract."""
    if mode is None:
        return False
    return mode.strip().upper() in {"RESEARCH", "DEEP_RESEARCH"}


def _tool_names_from_payload(tool_payload: Iterable[Dict[str, Any]]) -> Set[str]:
    names: Set[str] = set()
    for item in tool_payload:
        if not isinstance(item, dict):
            continue
        function = item.get("function")
        if not isinstance(function, dict):
            continue
        name = function.get("name")
        if isinstance(name, str) and name:
            names.add(name)
    return names


def missing_general_assistant_tools(tool_payload: List[Dict[str, Any]]) -> List[str]:
    """Return sorted missing required tool names for General Assistant."""
    present = _tool_names_from_payload(tool_payload)
    missing = GENERAL_ASSISTANT_CONTRACT.required_tool_names - present
    return sorted(missing)


def missing_deep_research_tools(tool_payload: List[Dict[str, Any]]) -> List[str]:
    """Return sorted missing required tool names for Deep Research."""
    present = _tool_names_from_payload(tool_payload)
    missing = DEEP_RESEARCH_CONTRACT.required_tool_names - present
    return sorted(missing)
