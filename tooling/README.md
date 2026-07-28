# Tooling Map

`tooling/` is the canonical home for repository automation and developer tooling that is not part of runtime app startup paths.

## Ownership Lanes

- `tooling/codemods`: codemods and migration transforms.
- `tooling/generators`: code/config/schema generation scripts.
- `tooling/automation`: CI/policy/repo automation checks.
- `tooling/quality`: quality/test/guard scripts.

## Runtime Boundary

- Keep runtime startup/deploy/ops execution entrypoints under `scripts/`.
- Legacy paths in `scripts/` may be thin wrappers for compatibility during migration.
- New non-runtime utilities should be added in `tooling/*`, not directly in `scripts/`.
