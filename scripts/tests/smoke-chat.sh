#!/usr/bin/env sh
set -eu
exec "${PYTHON:-python}" "$(dirname "$0")/smoke-chat.py" "$@"
