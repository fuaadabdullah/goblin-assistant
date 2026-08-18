# Critical-First Testing Policy

## Risk Tiers

- Tier 0 (must-pass): auth, API contracts, job execution, sandboxing, state persistence, trading/risk logic, and flows that move money or sensitive data.
- Tier 1+: secondary workflows and UX improvements with standard quality gates.

## Pyramid Requirements

- Unit tests: majority of test volume; pure logic and behavior-focused assertions.
- Integration tests: targeted boundaries only (DB/API/queues/filesystem/external services).
- E2E tests: small, intentional set of critical journeys only.

## Tier 0 Contract Rules

- API boundary tests must pin status codes and response shape for critical endpoints.
- Consumer contract tests in web clients must validate expected payload handling and error behavior.
- Contract changes require explicit test updates in both API and consumer layers.

## E2E Budget Rule

- Critical journey list lives in `apps/web/e2e/critical-journeys.txt`.
- Hard cap: 8 journeys (`tooling/quality/check-e2e-budget.sh`, compatibility wrapper remains at `scripts/check-e2e-budget.sh`).
- Exceeding cap requires explicit exception and rationale in PR.
- The release gate now also runs the brutal browser suite in `apps/web/e2e/brutal-release-gate.spec.ts`.
- The release gate also runs the intelligence and memory benchmark suites through `make benchmark-gates`.

## CI Enforcement

- `make test-critical` enforces the API critical-path suites and the brutal browser release gate without coverage percentage gates.
- `make test-brutal` runs the browser gate directly when you want the frontend validation alone.
- `make test-e2e-budget` enforces critical E2E journey cap.
- Critical-path test updates are required when touching Tier 0 surfaces.
