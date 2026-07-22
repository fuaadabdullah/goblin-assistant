# Release Process

This runbook describes the minimal release flow for the repository.

## Inputs

- `CHANGELOG.md` is the public release summary.
- Git tags are the immutable release markers.
- `.github/workflows/release.yml` is the release publish gate.

## Checklist

1. Update `CHANGELOG.md` for the intended release version.
2. Run `make test-critical` for named Tier 0 journeys.
3. Run architecture freeze gates: `make check-api-boundaries`,
   `make check-api-cycles`, `make check-capability-boundaries`, and
   `make check-operational-policy`.
4. Create the tag for the release commit, for example `v0.3.0`.
5. Run `scripts/release/verify_release_history.sh`.
6. Push the tag to trigger the release workflow.
7. Confirm the GitHub release and release artifacts were created.
8. For dogfood releases, follow `DOGFOODING_V0_3.md` before widening access.

## Notes

- Never rewrite a published tag unless the release is explicitly superseded.
- If the changelog and tags diverge, fix the repository history before cutting the next release.
- Backfilled tags should match the historical release boundary, not the current branch head.
