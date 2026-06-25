#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CHANGELOG="${ROOT_DIR}/CHANGELOG.md"

if [[ ! -f "${CHANGELOG}" ]]; then
  echo "ERROR: Missing CHANGELOG.md at ${CHANGELOG}" >&2
  exit 1
fi

CHANGELOG_VERSIONS=()
while IFS= read -r version; do
  [[ -n "${version}" ]] && CHANGELOG_VERSIONS+=("${version}")
done < <(
  grep -E '^## \[[0-9]+\.[0-9]+\.[0-9]+\] - ' "${CHANGELOG}" \
    | sed -E 's/^## \[([0-9]+\.[0-9]+\.[0-9]+)\] - .*/\1/'
)

if [[ ${#CHANGELOG_VERSIONS[@]} -eq 0 ]]; then
  echo "ERROR: No release headings found in CHANGELOG.md" >&2
  exit 1
fi

REPO_TAGS=()
while IFS= read -r tag; do
  [[ -n "${tag}" ]] && REPO_TAGS+=("${tag}")
done < <(git -C "${ROOT_DIR}" tag --list 'v*' --sort=version:refname)

echo "Release history check"
echo "====================="

missing=()
for version in "${CHANGELOG_VERSIONS[@]}"; do
  tag="v${version}"
  if git -C "${ROOT_DIR}" rev-parse -q --verify "refs/tags/${tag}" >/dev/null; then
    commit="$(git -C "${ROOT_DIR}" rev-list -n 1 "${tag}")"
    subject="$(git -C "${ROOT_DIR}" log -1 --format='%s' "${tag}")"
    echo "OK   ${tag} -> ${commit} | ${subject}"
  else
    echo "MISS ${tag} (present in changelog, missing tag)" >&2
    missing+=("${tag}")
  fi
done

extra=()
for tag in "${REPO_TAGS[@]}"; do
  version="${tag#v}"
  found=0
  for changelog_version in "${CHANGELOG_VERSIONS[@]}"; do
    if [[ "${version}" == "${changelog_version}" ]]; then
      found=1
      break
    fi
  done
  if [[ "${found}" -eq 0 ]]; then
    extra+=("${tag}")
  fi
done

if [[ ${#extra[@]} -gt 0 ]]; then
  echo "WARN extra tags not listed in CHANGELOG.md: ${extra[*]}"
fi

if [[ ${#missing[@]} -gt 0 ]]; then
  echo "ERROR: release history is incomplete" >&2
  exit 1
fi

echo "Release history is aligned."
