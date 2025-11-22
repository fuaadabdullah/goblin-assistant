#!/usr/bin/env bash
set -euo pipefail

# Goblin Assistant release builder
# - Builds the Tauri app for macOS, Windows, and Linux (where supported)
# - Collects artifacts in releases/ directory
# NOTE: Run this on the platform you want to build for. Cross-compilation of Tauri
# requires platform-specific toolchains and signing keys.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
RELEASE_DIR="${REPO_ROOT}/releases"

mkdir -p "${RELEASE_DIR}"

echo "Building Goblin Assistant..."
cd "${REPO_ROOT}"

# Install JS deps first
if command -v pnpm >/dev/null 2>&1; then
  pnpm install
else
  echo "Warning: pnpm not found. Falling back to npm install. Install pnpm for consistent results."
  npm install
fi

# Build web assets
pnpm build

# Build Tauri bundle(s)
# macOS universal build example
if [[ "$(uname -s)" == "Darwin" ]]; then
  echo "Detected macOS — building universal macOS binary"
  pnpm run build:mac
  # Move artifacts to releases
  find src-tauri/target -name "*.dmg" -or -name "*.app" -or -name "*.tar.gz" -print0 | xargs -0 -I {} cp {} "${RELEASE_DIR}/" || true
else
  echo "Building Tauri bundle for current OS"
  pnpm run build
  find src-tauri/target -name "*.AppImage" -or -name "*.deb" -or -name "*.AppImage" -or -name "*.msi" -print0 | xargs -0 -I {} cp {} "${RELEASE_DIR}/" || true
fi

echo "Build complete. Artifacts copied to ${RELEASE_DIR}."

# Optional: compress quick release for manual upload
cd "${REPO_ROOT}"
zip -r "${RELEASE_DIR}/goblin-assistant-release-$(date +%Y%m%d-%H%M%S).zip" releases/* || true

echo "Release packaging done."
