# Release Process

This runbook describes the minimal release flow for the repository.

## Inputs

- `CHANGELOG.md` is the public release summary.
- Git tags are the immutable release markers.
- `.github/workflows/release.yml` is the release publish gate.

## Checklist

1. Update `CHANGELOG.md` for the intended release version.
2. Run `scripts/release/verify_release_history.sh`.
3. Create the tag for the release commit, for example `v1.0.0`.
4. Push the tag to trigger the release workflow.
5. Confirm the GitHub release and release artifacts were created.

## Notes

- Never rewrite a published tag unless the release is explicitly superseded.
- If the changelog and tags diverge, fix the repository history before cutting the next release.
- Backfilled tags should match the historical release boundary, not the current branch head.
