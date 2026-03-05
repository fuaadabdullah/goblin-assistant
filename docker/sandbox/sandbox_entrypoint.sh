#!/usr/bin/env bash
# Runs a provided command (via args) with a hard timeout using timeout(1).
# This script runs as non-root inside the container.

set -euo pipefail

# max seconds inside container (double-guard; runner enforces outer timeout too)
INNER_TIMEOUT="${INNER_TIMEOUT:-20}"

if [ "$#" -eq 0 ]; then
  echo "No command provided"
  exit 2
fi

# use timeout to kill runaway processes
exec timeout --preserve-status "${INNER_TIMEOUT}" "$@"
