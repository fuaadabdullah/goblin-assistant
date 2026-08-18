# Architecture Evidence

`make architecture-evidence` is the canonical release-evidence command for API
architecture debt.

It writes `artifacts/architecture-evidence.json`, which is intentionally
machine-readable and contains:

- `commit_sha`
- `generation_timestamp`
- `tool_version`
- `parser_failure_count`
- `scanned_file_count`
- `violation_count`
- `skipped_file_count`
- `violations`
- `skipped_files`
- `unresolved_parsing_failures`

Historical narrative reports such as `docs/gap-analysis.md`,
`docs/tech-debt-report.md`, and `docs/architecture/ARCHITECTURE_RULES_TRACKER.md`
may explain prior snapshots, but they must not be used as current release
evidence when they conflict with the generated report.

## Release Use

1. Run `make architecture-evidence`.
2. Inspect `artifacts/architecture-evidence.json`.
3. Treat any unresolved parsing failure as an analyzer-blocking defect until it
   is fixed or explicitly reviewed.
4. Use `make check-api-boundaries`, `make check-api-cycles`, and
   `make check-capability-boundaries` for blocking gate behavior.
