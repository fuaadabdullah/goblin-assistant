"""Tests for the file_tool skill."""

from __future__ import annotations

import pytest

from api.assistant_tools import file_tool  # noqa: F401 — triggers registration
from api.assistant_tools.registry import TOOL_REGISTRY

# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


class TestFileToolRegistration:
    EXPECTED = {
        "read_file",
        "write_file",
        "search_files",
        "list_directory",
        "delete_file",
        "move_file",
        "copy_file",
        "make_directory",
    }

    def test_all_tools_registered(self):
        assert self.EXPECTED.issubset(TOOL_REGISTRY.keys())

    def test_all_tools_have_valid_openai_schema(self):
        for name in self.EXPECTED:
            schema = TOOL_REGISTRY[name].to_openai_schema()
            assert schema["type"] == "function"
            assert "name" in schema["function"]
            assert "description" in schema["function"]
            assert "parameters" in schema["function"]

    def test_all_tools_have_files_category(self):
        for name in self.EXPECTED:
            assert TOOL_REGISTRY[name].category == "files"


# ---------------------------------------------------------------------------
# read_file
# ---------------------------------------------------------------------------


class TestReadFile:
    @pytest.mark.asyncio
    async def test_reads_existing_file(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GOBLIN_FILE_WORKSPACE", str(tmp_path))
        (tmp_path / "hello.txt").write_text("hello world")

        result = await TOOL_REGISTRY["read_file"].handler("hello.txt")

        body = "hello world"
        assert result["content"] == body
        assert result["size_bytes"] == len(body)

    @pytest.mark.asyncio
    async def test_file_not_found(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GOBLIN_FILE_WORKSPACE", str(tmp_path))

        result = await TOOL_REGISTRY["read_file"].handler("missing.txt")

        assert "error" in result
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_path_traversal_rejected(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GOBLIN_FILE_WORKSPACE", str(tmp_path))

        result = await TOOL_REGISTRY["read_file"].handler("../../etc/passwd")

        assert "error" in result
        assert "outside" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_reading_directory_returns_error(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GOBLIN_FILE_WORKSPACE", str(tmp_path))
        (tmp_path / "subdir").mkdir()

        result = await TOOL_REGISTRY["read_file"].handler("subdir")

        assert "error" in result


# ---------------------------------------------------------------------------
# write_file
# ---------------------------------------------------------------------------


class TestWriteFile:
    @pytest.mark.asyncio
    async def test_creates_new_file(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GOBLIN_FILE_WORKSPACE", str(tmp_path))

        result = await TOOL_REGISTRY["write_file"].handler("new.txt", "content here")

        assert result["written"] is True
        assert (tmp_path / "new.txt").read_text() == "content here"

    @pytest.mark.asyncio
    async def test_overwrites_existing_file(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GOBLIN_FILE_WORKSPACE", str(tmp_path))
        (tmp_path / "existing.txt").write_text("old")

        result = await TOOL_REGISTRY["write_file"].handler("existing.txt", "new")

        assert result["written"] is True
        assert (tmp_path / "existing.txt").read_text() == "new"

    @pytest.mark.asyncio
    async def test_creates_parent_directories(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GOBLIN_FILE_WORKSPACE", str(tmp_path))

        result = await TOOL_REGISTRY["write_file"].handler("a/b/c.txt", "nested")

        assert result["written"] is True
        assert (tmp_path / "a" / "b" / "c.txt").exists()

    @pytest.mark.asyncio
    async def test_path_traversal_rejected(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GOBLIN_FILE_WORKSPACE", str(tmp_path))

        result = await TOOL_REGISTRY["write_file"].handler("../../evil.txt", "bad")

        assert "error" in result
        assert "outside" in result["error"].lower()


# ---------------------------------------------------------------------------
# search_files
# ---------------------------------------------------------------------------


class TestSearchFiles:
    @pytest.mark.asyncio
    async def test_finds_matching_lines(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GOBLIN_FILE_WORKSPACE", str(tmp_path))
        (tmp_path / "notes.txt").write_text("line one\nfind me\nline three")

        result = await TOOL_REGISTRY["search_files"].handler(".", "find me")

        assert result["total"] == 1
        assert len(result["matches"]) == 1
        match_line = 2  # "find me" is the second line of the test content
        assert result["matches"][0]["line"] == match_line
        assert "find me" in result["matches"][0]["text"]

    @pytest.mark.asyncio
    async def test_no_matches_returns_empty(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GOBLIN_FILE_WORKSPACE", str(tmp_path))
        (tmp_path / "notes.txt").write_text("nothing relevant here")

        result = await TOOL_REGISTRY["search_files"].handler(".", "xyzzy")

        assert result["total"] == 0
        assert result["matches"] == []

    @pytest.mark.asyncio
    async def test_skips_binary_files(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GOBLIN_FILE_WORKSPACE", str(tmp_path))
        (tmp_path / "binary.bin").write_bytes(b"\x00\x01\x02find\x00")
        (tmp_path / "text.txt").write_text("find me")

        result = await TOOL_REGISTRY["search_files"].handler(".", "find")

        # Binary file skipped; only text.txt matches
        assert all("binary.bin" not in m["file"] for m in result["matches"])
        assert result["total"] == 1

    @pytest.mark.asyncio
    async def test_max_results_limits_output(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GOBLIN_FILE_WORKSPACE", str(tmp_path))
        lines = "\n".join(f"match {i}" for i in range(100))
        (tmp_path / "big.txt").write_text(lines)

        limit = 10
        total_lines = 100
        result = await TOOL_REGISTRY["search_files"].handler(".", "match", max_results=limit)

        assert len(result["matches"]) == limit
        assert result["total"] == total_lines

    @pytest.mark.asyncio
    async def test_invalid_regex_returns_error(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GOBLIN_FILE_WORKSPACE", str(tmp_path))

        result = await TOOL_REGISTRY["search_files"].handler(".", "[invalid(")

        assert "error" in result

    @pytest.mark.asyncio
    async def test_path_traversal_rejected(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GOBLIN_FILE_WORKSPACE", str(tmp_path))

        result = await TOOL_REGISTRY["search_files"].handler("../../etc", "passwd")

        assert "error" in result


# ---------------------------------------------------------------------------
# list_directory
# ---------------------------------------------------------------------------


class TestListDirectory:
    @pytest.mark.asyncio
    async def test_lists_files_and_dirs(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GOBLIN_FILE_WORKSPACE", str(tmp_path))
        (tmp_path / "file.txt").write_text("hi")
        (tmp_path / "subdir").mkdir()

        result = await TOOL_REGISTRY["list_directory"].handler(".")

        names = {e["name"] for e in result["entries"]}
        assert "file.txt" in names
        assert "subdir" in names
        assert result["count"] == len(names)

    @pytest.mark.asyncio
    async def test_entry_types_are_correct(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GOBLIN_FILE_WORKSPACE", str(tmp_path))
        (tmp_path / "a.txt").write_text("x")
        (tmp_path / "d").mkdir()

        result = await TOOL_REGISTRY["list_directory"].handler(".")

        types = {e["name"]: e["type"] for e in result["entries"]}
        assert types["a.txt"] == "file"
        assert types["d"] == "directory"

    @pytest.mark.asyncio
    async def test_directories_listed_before_files(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GOBLIN_FILE_WORKSPACE", str(tmp_path))
        (tmp_path / "z_file.txt").write_text("z")
        (tmp_path / "a_dir").mkdir()

        result = await TOOL_REGISTRY["list_directory"].handler(".")

        types = [e["type"] for e in result["entries"]]
        # All directories should come before files
        first_file = next((i for i, t in enumerate(types) if t == "file"), len(types))
        last_dir = next(
            (len(types) - 1 - i for i, t in enumerate(reversed(types)) if t == "directory"),
            -1,
        )
        assert last_dir < first_file

    @pytest.mark.asyncio
    async def test_missing_path_returns_error(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GOBLIN_FILE_WORKSPACE", str(tmp_path))

        result = await TOOL_REGISTRY["list_directory"].handler("nonexistent")

        assert "error" in result

    @pytest.mark.asyncio
    async def test_path_traversal_rejected(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GOBLIN_FILE_WORKSPACE", str(tmp_path))

        result = await TOOL_REGISTRY["list_directory"].handler("../../")

        assert "error" in result
