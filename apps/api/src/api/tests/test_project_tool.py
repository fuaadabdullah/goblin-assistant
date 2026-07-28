"""Tests for the project_tool skill."""

from __future__ import annotations

import json

import pytest

from api.assistant_tools import project_tool  # noqa: F401 - triggers registration
from api.assistant_tools.registry import TOOL_REGISTRY


class TestProjectToolRegistration:
    EXPECTED = {"create_project", "list_projects", "get_project_info"}

    def test_project_tools_registered(self):
        assert self.EXPECTED.issubset(TOOL_REGISTRY.keys())

    def test_project_tools_have_projects_category(self):
        for name in self.EXPECTED:
            assert TOOL_REGISTRY[name].category == "projects"


class TestCreateProject:
    @pytest.mark.asyncio
    async def test_requires_confirmation(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GOBLIN_FILE_WORKSPACE", str(tmp_path))

        result = await TOOL_REGISTRY["create_project"].handler(
            name="Alpha",
            path="projects/alpha",
            confirm=False,
        )

        assert "error" in result
        assert "confirm=true" in result["error"]

    @pytest.mark.asyncio
    async def test_scaffolds_project_and_marker(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GOBLIN_FILE_WORKSPACE", str(tmp_path))

        result = await TOOL_REGISTRY["create_project"].handler(
            name="Alpha",
            path="projects/alpha",
            template="python-service",
            confirm=True,
        )

        assert result["created"] is True
        project_dir = tmp_path / "projects" / "alpha"
        assert (project_dir / "docs").is_dir()
        assert (project_dir / "src").is_dir()
        assert (project_dir / "data").is_dir()

        marker_path = project_dir / ".goblin-project.json"
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
        assert marker["name"] == "Alpha"
        assert marker["version"] == "1.0"
        assert marker["template"] == "python-service"

    @pytest.mark.asyncio
    async def test_rejects_path_traversal(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GOBLIN_FILE_WORKSPACE", str(tmp_path))
        result = await TOOL_REGISTRY["create_project"].handler(
            name="Escape",
            path="../../tmp/escape",
            confirm=True,
        )
        assert "error" in result
        assert "outside" in result["error"].lower()


class TestListProjects:
    @pytest.mark.asyncio
    async def test_lists_projects_by_marker(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GOBLIN_FILE_WORKSPACE", str(tmp_path))
        proj_dir = tmp_path / "projects" / "one"
        proj_dir.mkdir(parents=True)
        (proj_dir / ".goblin-project.json").write_text(
            json.dumps(
                {
                    "name": "One",
                    "created_at": "2026-05-30T00:00:00+00:00",
                    "version": "1.0",
                }
            ),
            encoding="utf-8",
        )

        result = await TOOL_REGISTRY["list_projects"].handler("projects", 4)
        assert result["count"] == 1
        assert result["projects"][0]["path"] == "projects/one"
        assert result["projects"][0]["name"] == "One"

    @pytest.mark.asyncio
    async def test_reports_invalid_marker(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GOBLIN_FILE_WORKSPACE", str(tmp_path))
        bad_dir = tmp_path / "badproj"
        bad_dir.mkdir(parents=True)
        (bad_dir / ".goblin-project.json").write_text('{"name":"Broken"}', encoding="utf-8")

        result = await TOOL_REGISTRY["list_projects"].handler(".", 4)
        assert result["count"] == 1
        assert "error" in result["projects"][0]


class TestGetProjectInfo:
    @pytest.mark.asyncio
    async def test_returns_project_info_and_stats(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GOBLIN_FILE_WORKSPACE", str(tmp_path))
        proj_dir = tmp_path / "projects" / "two"
        proj_dir.mkdir(parents=True)
        (proj_dir / "src").mkdir()
        (proj_dir / "src" / "main.py").write_text("print('hi')", encoding="utf-8")
        (proj_dir / ".goblin-project.json").write_text(
            json.dumps(
                {
                    "name": "Two",
                    "created_at": "2026-05-30T00:00:00+00:00",
                    "version": "1.0",
                    "tags": ["backend"],
                }
            ),
            encoding="utf-8",
        )

        result = await TOOL_REGISTRY["get_project_info"].handler("projects/two")
        assert result["marker"]["name"] == "Two"
        assert result["stats"]["file_count"] >= 2
        assert result["stats"]["directory_count"] >= 1

    @pytest.mark.asyncio
    async def test_returns_marker_validation_error(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GOBLIN_FILE_WORKSPACE", str(tmp_path))
        proj_dir = tmp_path / "projects" / "three"
        proj_dir.mkdir(parents=True)
        (proj_dir / ".goblin-project.json").write_text("[]", encoding="utf-8")

        result = await TOOL_REGISTRY["get_project_info"].handler("projects/three")
        assert "error" in result
        assert "expected an object" in result["error"]
