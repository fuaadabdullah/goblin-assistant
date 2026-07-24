#!/usr/bin/env bash
set -euo pipefail

# SDK generation depends on toolchain behavior validated in CI (Node 20).
# We allow Node 20 and 22 locally and fail fast for newer majors that
# currently break openapi-typescript transitive parsing.
REQUIRED_NODE_MAJORS="20|22"

get_node_major() {
  if [[ -n "${GOBLIN_NODE_MAJOR_OVERRIDE:-}" ]]; then
    echo "${GOBLIN_NODE_MAJOR_OVERRIDE}"
    return 0
  fi

  local version
  version="$(node -v 2>/dev/null || true)"
  if [[ -z "${version}" ]]; then
    echo ""
    return 0
  fi

  version="${version#v}"
  echo "${version%%.*}"
}

NODE_MAJOR="$(get_node_major)"
if [[ -z "${NODE_MAJOR}" ]]; then
  echo "Node.js is required for SDK generation. Install Node 20.x (or 22.x) and retry." >&2
  exit 1
fi

if ! [[ "${NODE_MAJOR}" =~ ^(${REQUIRED_NODE_MAJORS})$ ]]; then
  echo "Unsupported Node.js major version: ${NODE_MAJOR}" >&2
  echo "SDK generation requires Node 20.x (CI baseline) or 22.x." >&2
  echo "Switch Node version (for example: nvm use 20) and rerun make sdk-generate/make sdk-check." >&2
  exit 1
fi