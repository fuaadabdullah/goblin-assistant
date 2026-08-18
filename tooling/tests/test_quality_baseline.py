from __future__ import annotations

from pathlib import Path

from tooling.quality.quality_baseline import (
    GovernanceIssue,
    classify_suppressions,
    collect_source_metrics,
    compare_to_baseline,
    find_new_suppression_governance_issues,
    find_suppression_governance_issues,
    find_xfail_governance_issues,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_collect_source_metrics_counts_occurrences_and_files(tmp_path: Path) -> None:
    _write(
        tmp_path / "apps" / "web" / "src" / "example.ts",
        "const a = foo as any;\nconst b = bar as unknown;\n",
    )
    _write(
        tmp_path / "apps" / "web" / "lint.ts",
        "// eslint-disable-next-line\nconst a = 1;\n",
    )
    _write(
        tmp_path / "apps" / "api" / "demo.py",
        "from something import thing  # noqa: F401\n",
    )
    _write(
        tmp_path / "tests" / "test_demo.py",
        "@pytest.mark.xfail\ndef test_demo():\n    assert False\n",
    )

    metrics = collect_source_metrics(tmp_path)

    assert metrics["web_assertions"] == 2
    assert metrics["web_eslint_suppression_files"] == 1
    assert metrics["python_noqa_files"] == 1
    assert metrics["xfail_tests"] == 1
    assert metrics["suppression_justified_interop_typing_issue"] == 2
    assert metrics["suppression_clearly_removable"] == 2


def test_suppression_classification_requires_reasons(tmp_path: Path) -> None:
    _write(
        tmp_path / "apps" / "api" / "registration.py",
        "from plugin import adapter  # noqa: F401  # imported for plugin registration\n"
        "from legacy import adapter  # noqa\n",
    )
    _write(
        tmp_path / "apps" / "web" / "src" / "interop.ts",
        "// eslint-disable-next-line @typescript-eslint/no-explicit-any -- legacy SDK shape\n"
        "const ok = value as any;\n"
        "// @ts-ignore\n"
        "const bad = missingGlobal;\n",
    )

    findings = classify_suppressions(tmp_path, tmp_path / ".tmp" / "cache.json")
    issues = find_suppression_governance_issues(tmp_path)

    assert any(
        finding.path == "apps/api/registration.py"
        and finding.category == "legacy_debt"
        for finding in findings
    )
    assert GovernanceIssue(
        path="apps/api/registration.py",
        line=2,
        message="python_noqa suppression missing reason",
    ) in issues
    assert GovernanceIssue(
        path="apps/web/src/interop.ts",
        line=3,
        message="web_ts_ignore suppression missing reason",
    ) in issues


def test_new_suppression_governance_checks_added_lines(
    tmp_path: Path, monkeypatch
) -> None:
    diff = """diff --git a/apps/api/demo.py b/apps/api/demo.py
index 1111111..2222222 100644
--- a/apps/api/demo.py
+++ b/apps/api/demo.py
@@ -1,0 +1,2 @@
+from plugin import adapter  # noqa: F401
+from plugin import ok  # noqa: F401  # imported for plugin registration
diff --git a/apps/web/src/demo.ts b/apps/web/src/demo.ts
index 1111111..2222222 100644
--- a/apps/web/src/demo.ts
+++ b/apps/web/src/demo.ts
@@ -1,0 +1,2 @@
+// @ts-ignore
+// @ts-expect-error legacy SDK type gap
"""

    class Completed:
        returncode = 0
        stdout = diff
        stderr = ""

    monkeypatch.setattr(
        "tooling.quality.quality_baseline.subprocess.run",
        lambda *args, **kwargs: Completed(),
    )

    assert find_new_suppression_governance_issues(tmp_path) == [
        GovernanceIssue(
            path="apps/api/demo.py",
            line=1,
            message="new python_noqa suppression missing reason",
        ),
        GovernanceIssue(
            path="apps/web/src/demo.ts",
            line=1,
            message="new web_ts_ignore suppression missing reason",
        ),
    ]


def test_find_xfail_governance_issues_requires_metadata(tmp_path: Path) -> None:
    _write(
        tmp_path / "tests" / "test_xfail.py",
        "# reason: flaky external dependency\n"
        "# issue: GH-123\n"
        "# subsystem: search\n"
        "@pytest.mark.xfail\n"
        "def test_demo():\n"
        "    assert False\n",
    )

    issues = find_xfail_governance_issues(tmp_path)

    assert issues == [
        GovernanceIssue(
            path="tests/test_xfail.py",
            line=4,
            message="xfail metadata missing: removal, expires: or review:",
        )
    ]


def test_compare_to_baseline_flags_increases_only() -> None:
    failures = compare_to_baseline(
        {"web_assertions": 5, "xfail_tests": 0},
        {"web_assertions": 4, "xfail_tests": 0},
    )

    assert failures == ["web_assertions increased: 5 > 4"]
