from pathlib import Path

import scripts.policy_guard as policy_guard


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_flags_ambiguous_names(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    file_path = _write(root / "apps/web/src/utils/example.ts", "const data = 1;\nfunction process() { return data; }\n")
    monkeypatch.setattr(policy_guard, "ROOT", root)
    monkeypatch.setattr(policy_guard, "PURE_ZONE_PATTERNS", ("apps/web/src/utils/**/*.{ts,tsx,js,jsx}",))
    monkeypatch.setattr(policy_guard, "PURE_ZONE_EXCLUDES", ())

    violations = policy_guard.scan_file(file_path)
    rules = {v.rule for v in violations}

    assert "ambiguous-variable" in rules
    assert "generic-process-fn" in rules


def test_flags_side_effects_in_pure_zone(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    file_path = _write(
        root / "apps/api/src/api/core/calc.py",
        "import os\n"
        "global cache_state\n"
        "def calc():\n"
        "  open('x.txt', 'w')\n"
        "  requests.get('https://example.com')\n"
        "  os.environ['A'] = '1'\n",
    )
    monkeypatch.setattr(policy_guard, "ROOT", root)
    monkeypatch.setattr(policy_guard, "PURE_ZONE_PATTERNS", ("apps/api/src/api/core/**/*.py",))
    monkeypatch.setattr(policy_guard, "PURE_ZONE_EXCLUDES", ())

    violations = policy_guard.scan_file(file_path)
    rules = {v.rule for v in violations}

    assert "global-mutation" in rules
    assert "file-write" in rules
    assert "http-call" in rules
    assert "env-mutation" in rules


def test_allows_boundary_exemption(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    file_path = _write(
        root / "apps/api/src/api/services/network_adapter.py",
        "def send():\n  requests.get('https://example.com')\n",
    )
    monkeypatch.setattr(policy_guard, "ROOT", root)
    monkeypatch.setattr(policy_guard, "PURE_ZONE_PATTERNS", ("apps/api/src/api/services/**/*.py",))
    monkeypatch.setattr(policy_guard, "PURE_ZONE_EXCLUDES", ("apps/api/src/api/services/**/*adapter*.py",))

    violations = policy_guard.scan_file(file_path)
    rules = {v.rule for v in violations}

    assert "http-call" not in rules
