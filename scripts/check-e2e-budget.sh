#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CRITICAL_E2E_FILE="${ROOT_DIR}/apps/web/e2e/critical-journeys.txt"
MAX_CRITICAL_JOURNEYS="${MAX_CRITICAL_JOURNEYS:-8}"

if [[ ! -f "${CRITICAL_E2E_FILE}" ]]; then
  echo "Missing ${CRITICAL_E2E_FILE}"
  exit 1
fi

journey_count="$(grep -v '^\s*#' "${CRITICAL_E2E_FILE}" | grep -v '^\s*$' | wc -l | tr -d ' ')"
if [[ "${journey_count}" -gt "${MAX_CRITICAL_JOURNEYS}" ]]; then
  echo "Critical E2E journey budget exceeded: ${journey_count} > ${MAX_CRITICAL_JOURNEYS}"
  exit 1
fi

echo "Critical E2E journey budget OK: ${journey_count}/${MAX_CRITICAL_JOURNEYS}"
