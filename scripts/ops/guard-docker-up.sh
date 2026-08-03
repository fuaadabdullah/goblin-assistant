#!/usr/bin/env bash
# Compatibility entrypoint. The Python launcher is cross-platform, owns the
# single-flight lock for the entire compose command, and only targets stale
# compose processes that mention the Goblin backend service.
set -euo pipefail
exec "${PYTHON:-python}" "$(dirname "$0")/docker-compose-up.py" "$@"
