#!/usr/bin/env sh
set -eu
exec "${PYTHON:-python}" "$(dirname "$0")/bootstrap-env.py" "$@"
