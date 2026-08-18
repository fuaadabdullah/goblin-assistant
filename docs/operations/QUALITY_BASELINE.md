# Quality Baseline

`make check-quality-baseline` is the debt-ratchet gate for source suppressions,
xfails, and architecture analyzer counts.

## Suppression Classes

Suppressions are measured by category:

- `justified_interop_typing_issue`
- `framework_limitation`
- `legacy_debt`
- `temporary_suppression`
- `clearly_removable`

The baseline forbids increases in any checked metric. Existing debt can be
burned down without changing policy; new suppressions must either include an
inline reason that classifies them or they increase `clearly_removable` and fail
the ratchet.

Examples:

```python
from plugin import adapter  # noqa: F401  # imported for plugin registration
```

```python
from plugin import adapter  # noqa
```

The first suppression has a reason. The second is counted as clearly removable.

## Analyzer Behavior

The quality gate runs architecture analyzers in subprocesses with a timeout, so
a stuck analyzer returns a tool failure instead of freezing CI.

Exit codes:

- `0`: baseline passed
- `1`: violations, xfail governance issues, or baseline regressions
- `2`: analyzer failure or timeout

Use `python3.11 tooling/quality/quality_baseline.py --partial-output .tmp/quality-baseline-partial.json`
when debugging a failing run. Partial output includes source metrics, analyzer
commands, elapsed time, analyzer status, and any governance issues found before
failure.
