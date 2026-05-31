"""
File tools for Goblin Assistant.

Registers tools for reading, writing, searching, and listing files on the
local filesystem. All operations are sandboxed to a configurable base
directory (GOBLIN_FILE_WORKSPACE env var, defaults to ~/goblin-workspace)
to prevent directory traversal.
"""

from __future__ import annotations

import asyncio
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

from ..registry import ToolDefinition, ToolParameter, register_tool

# ---------------------------------------------------------------------------
# Path sandboxing
# ---------------------------------------------------------------------------


def _get_base_dir() -> Path:
    """Return the resolved sandbox base directory."""
    raw = os.environ.get("GOBLIN_FILE_WORKSPACE", "~/goblin-workspace")
    return Path(raw).expanduser().resolve()


def _read_text_content(file_path: Path) -> Optional[str]:
    """Read a file as text; return None if it is binary or unreadable."""
    try:
        raw = file_path.read_bytes()
    except OSError:
        return None
    if b"\x00" in raw:
        return None
    try:
        return raw.decode("utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        return None


def _resolve_path(user_path: str) -> Path:
    """Resolve user_path inside the sandbox base dir.

    Raises ValueError if the resolved path escapes the base directory.
    """
    base = _get_base_dir()
    candidate = (base / user_path).resolve()
    if base not in candidate.parents and candidate != base:
        raise ValueError(
            f"Path '{user_path}' resolves outside the workspace. "
            "All file operations must stay within the goblin workspace."
        )
    return candidate


# ---------------------------------------------------------------------------
# read_file
# ---------------------------------------------------------------------------


async def _handle_read_file(path: str) -> Dict[str, Any]:
    def _read() -> Dict[str, Any]:
        try:
            resolved = _resolve_path(path)
        except ValueError as exc:
            return {"error": str(exc)}

        if not resolved.exists():
            return {"error": f"File not found: {path}"}
        if not resolved.is_file():
            return {"error": f"Path is not a file: {path}"}

        content = resolved.read_text(encoding="utf-8", errors="replace")
        return {
            "content": content,
            "path": str(resolved),
            "size_bytes": resolved.stat().st_size,
        }

    return await asyncio.to_thread(_read)


register_tool(
    ToolDefinition(
        name="read_file",
        description=(
            "Use when the user wants to read, view, or inspect the contents of "
            "a file. Returns the full text content of the file, its resolved "
            "path, and size in bytes. Only works within the goblin workspace "
            "directory; use list_directory first if unsure of the exact filename."
        ),
        parameters=[
            ToolParameter(
                name="path",
                type="string",
                description=(
                    "Path to the file, relative to the goblin workspace root. "
                    "For example: 'notes/ideas.txt' or 'reports/q1.md'."
                ),
            ),
        ],
        handler=_handle_read_file,
        category="files",
    )
)


# ---------------------------------------------------------------------------
# write_file
# ---------------------------------------------------------------------------


async def _handle_write_file(path: str, content: str) -> Dict[str, Any]:
    def _write() -> Dict[str, Any]:
        try:
            resolved = _resolve_path(path)
        except ValueError as exc:
            return {"error": str(exc)}

        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding="utf-8")
        return {
            "written": True,
            "path": str(resolved),
            "size_bytes": resolved.stat().st_size,
        }

    return await asyncio.to_thread(_write)


register_tool(
    ToolDefinition(
        name="write_file",
        description=(
            "Use when the user wants to create, save, or overwrite a file with "
            "new content. Creates parent directories automatically if they do "
            "not exist. Returns the resolved path and written size. Only works "
            "within the goblin workspace directory."
        ),
        parameters=[
            ToolParameter(
                name="path",
                type="string",
                description=(
                    "Destination path for the file, relative to the goblin "
                    "workspace root. For example: 'notes/meeting.md' or "
                    "'scripts/run.sh'."
                ),
            ),
            ToolParameter(
                name="content",
                type="string",
                description="Full text content to write to the file.",
            ),
        ],
        handler=_handle_write_file,
        category="files",
    )
)


# ---------------------------------------------------------------------------
# search_files
# ---------------------------------------------------------------------------


async def _handle_search_files(
    directory: str,
    pattern: str,
    max_results: int = 50,
) -> Dict[str, Any]:
    def _search() -> Dict[str, Any]:
        try:
            resolved_dir = _resolve_path(directory)
        except ValueError as exc:
            return {"error": str(exc)}

        if not resolved_dir.exists():
            return {"error": f"Directory not found: {directory}"}
        if not resolved_dir.is_dir():
            return {"error": f"Path is not a directory: {directory}"}

        try:
            regex = re.compile(pattern, re.IGNORECASE)
        except re.error as exc:
            return {"error": f"Invalid pattern '{pattern}': {exc}"}

        matches = []
        total = 0
        for file_path in sorted(resolved_dir.rglob("*")):
            if not file_path.is_file():
                continue
            text = _read_text_content(file_path)
            if text is None:
                continue
            for line_no, line in enumerate(text.splitlines(), start=1):
                if regex.search(line):
                    total += 1
                    if len(matches) < max_results:
                        matches.append(
                            {
                                "file": str(file_path.relative_to(_get_base_dir())),
                                "line": line_no,
                                "text": line.rstrip(),
                            }
                        )

        return {"matches": matches, "total": total}

    return await asyncio.to_thread(_search)


register_tool(
    ToolDefinition(
        name="search_files",
        description=(
            "Use when the user wants to find text, a keyword, or a pattern "
            "across files in a directory. Recursively searches all text files "
            "under the given directory (skips binary files), matching each line "
            "against the pattern. Returns matching lines with their file path "
            "and line number. Supports plain text and regular expression patterns."
        ),
        parameters=[
            ToolParameter(
                name="directory",
                type="string",
                description=(
                    "Directory to search in, relative to the goblin workspace "
                    "root. Use '.' to search the entire workspace."
                ),
            ),
            ToolParameter(
                name="pattern",
                type="string",
                description=(
                    "Text substring or regular expression to search for. "
                    "Matching is case-insensitive."
                ),
            ),
            ToolParameter(
                name="max_results",
                type="integer",
                description=(
                    "Maximum number of matching lines to return. Defaults to 50."
                ),
                required=False,
                default=50,
            ),
        ],
        handler=_handle_search_files,
        category="files",
    )
)


# ---------------------------------------------------------------------------
# list_directory
# ---------------------------------------------------------------------------


async def _handle_list_directory(path: str = ".") -> Dict[str, Any]:
    def _list() -> Dict[str, Any]:
        try:
            resolved = _resolve_path(path)
        except ValueError as exc:
            return {"error": str(exc)}

        if not resolved.exists():
            return {"error": f"Path not found: {path}"}
        if not resolved.is_dir():
            return {"error": f"Path is not a directory: {path}"}

        entries = []
        for entry in sorted(resolved.iterdir(), key=lambda e: (e.is_file(), e.name)):
            try:
                size = entry.stat().st_size if entry.is_file() else 0
            except OSError:
                size = 0
            entries.append(
                {
                    "name": entry.name,
                    "type": "file" if entry.is_file() else "directory",
                    "size_bytes": size,
                }
            )

        return {
            "entries": entries,
            "path": str(resolved),
            "count": len(entries),
        }

    return await asyncio.to_thread(_list)


register_tool(
    ToolDefinition(
        name="list_directory",
        description=(
            "Use when the user wants to see what files and folders exist in a "
            "directory, browse the workspace, or find a filename before reading "
            "or searching. Returns each entry's name, type (file or directory), "
            "and size in bytes. Directories are listed before files."
        ),
        parameters=[
            ToolParameter(
                name="path",
                type="string",
                description=(
                    "Directory path relative to the goblin workspace root. "
                    "Defaults to '.' (the workspace root) if omitted."
                ),
                required=False,
                default=".",
            ),
        ],
        handler=_handle_list_directory,
        category="files",
    )
)


# ---------------------------------------------------------------------------
# delete_file
# ---------------------------------------------------------------------------


async def _handle_delete_file(path: str) -> Dict[str, Any]:
    def _delete() -> Dict[str, Any]:
        try:
            resolved = _resolve_path(path)
        except ValueError as exc:
            return {"error": str(exc)}

        if not resolved.exists():
            return {"error": f"File not found: {path}"}
        if not resolved.is_file():
            return {"error": f"Path is not a file: {path}"}

        resolved.unlink()
        return {"deleted": True, "path": str(resolved)}

    return await asyncio.to_thread(_delete)


register_tool(
    ToolDefinition(
        name="delete_file",
        description=(
            "Use when the user wants to delete or remove a file from the "
            "workspace. Only deletes files (not directories). Returns "
            "confirmation of the deleted path. Only works within the goblin "
            "workspace directory."
        ),
        parameters=[
            ToolParameter(
                name="path",
                type="string",
                description=(
                    "Path to the file to delete, relative to the goblin "
                    "workspace root. For example: 'notes/old.txt'."
                ),
            ),
        ],
        handler=_handle_delete_file,
        category="files",
    )
)


# ---------------------------------------------------------------------------
# move_file
# ---------------------------------------------------------------------------


async def _handle_move_file(source: str, destination: str) -> Dict[str, Any]:
    import shutil

    def _move() -> Dict[str, Any]:
        try:
            src = _resolve_path(source)
            dst = _resolve_path(destination)
        except ValueError as exc:
            return {"error": str(exc)}

        if not src.exists():
            return {"error": f"Source not found: {source}"}

        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        return {
            "moved": True,
            "source": str(src),
            "destination": str(dst),
        }

    return await asyncio.to_thread(_move)


register_tool(
    ToolDefinition(
        name="move_file",
        description=(
            "Use when the user wants to move or rename a file or directory "
            "within the workspace. Creates destination parent directories "
            "automatically. Both source and destination must stay within the "
            "goblin workspace."
        ),
        parameters=[
            ToolParameter(
                name="source",
                type="string",
                description=(
                    "Current path of the file or directory, relative to "
                    "workspace root."
                ),
            ),
            ToolParameter(
                name="destination",
                type="string",
                description="Target path, relative to workspace root.",
            ),
        ],
        handler=_handle_move_file,
        category="files",
    )
)


# ---------------------------------------------------------------------------
# copy_file
# ---------------------------------------------------------------------------


async def _handle_copy_file(source: str, destination: str) -> Dict[str, Any]:
    import shutil

    def _copy() -> Dict[str, Any]:
        try:
            src = _resolve_path(source)
            dst = _resolve_path(destination)
        except ValueError as exc:
            return {"error": str(exc)}

        if not src.exists():
            return {"error": f"Source not found: {source}"}
        if not src.is_file():
            return {"error": f"Source is not a file: {source}"}

        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(src), str(dst))
        return {
            "copied": True,
            "source": str(src),
            "destination": str(dst),
            "size_bytes": dst.stat().st_size,
        }

    return await asyncio.to_thread(_copy)


register_tool(
    ToolDefinition(
        name="copy_file",
        description=(
            "Use when the user wants to duplicate a file to a new location "
            "within the workspace. Creates destination parent directories "
            "automatically. Only copies files (not directories). Both paths "
            "must stay within the goblin workspace."
        ),
        parameters=[
            ToolParameter(
                name="source",
                type="string",
                description=(
                    "Path of the file to copy, relative to workspace root."
                ),
            ),
            ToolParameter(
                name="destination",
                type="string",
                description=(
                    "Destination path for the copy, relative to workspace "
                    "root."
                ),
            ),
        ],
        handler=_handle_copy_file,
        category="files",
    )
)


# ---------------------------------------------------------------------------
# make_directory
# ---------------------------------------------------------------------------


async def _handle_make_directory(path: str) -> Dict[str, Any]:
    def _mkdir() -> Dict[str, Any]:
        try:
            resolved = _resolve_path(path)
        except ValueError as exc:
            return {"error": str(exc)}

        if resolved.exists() and resolved.is_dir():
            return {
                "created": False,
                "path": str(resolved),
                "note": "Already exists",
            }

        resolved.mkdir(parents=True, exist_ok=True)
        return {"created": True, "path": str(resolved)}

    return await asyncio.to_thread(_mkdir)


register_tool(
    ToolDefinition(
        name="make_directory",
        description=(
            "Use when the user wants to create a new directory (folder) in "
            "the workspace. Creates all intermediate parent directories "
            "automatically. Safe to call even if the directory already exists."
        ),
        parameters=[
            ToolParameter(
                name="path",
                type="string",
                description=(
                    "Directory path to create, relative to the goblin "
                    "workspace root. For example: "
                    "'projects/new-project/data'."
                ),
            ),
        ],
        handler=_handle_make_directory,
        category="files",
    )
)
