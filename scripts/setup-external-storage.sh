#!/bin/bash

# Setup External Storage on GOBLINOS Drive
# This script configures the project to use external storage for large artifacts

set -e

GOBLINOS_PATH="/Volumes/GOBLINOS 1/goblin-assistant"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "🚀 Setting up external storage on GOBLINOS drive..."
echo "   Project root: $PROJECT_ROOT"
echo "   Storage path: $GOBLINOS_PATH"

# Verify GOBLINOS drive is mounted
if [ ! -d "$GOBLINOS_PATH" ]; then
    echo "❌ ERROR: GOBLINOS drive not found at $GOBLINOS_PATH"
    echo "   Please ensure the GOBLINOS drive is mounted and try again."
    exit 1
fi

# Create .env.storage if it doesn't exist
echo ""
echo "📝 Creating .env.storage configuration..."
if [ ! -f "$PROJECT_ROOT/.env.storage" ]; then
    cat > "$PROJECT_ROOT/.env.storage" << 'EOF'
# External Storage Configuration
# This file configures paths for large artifacts on GOBLINOS drive

GOBLINOS_BASE="/Volumes/GOBLINOS 1/goblin-assistant"
STORAGE_NODE_MODULES="${GOBLINOS_BASE}/node_modules"
STORAGE_VENV="${GOBLINOS_BASE}/venv"
STORAGE_DOCKER_CACHE="${GOBLINOS_BASE}/docker-cache"
STORAGE_POSTGRES="${GOBLINOS_BASE}/postgres-data"
STORAGE_REDIS="${GOBLINOS_BASE}/redis-data"
STORAGE_BUILD="${GOBLINOS_BASE}/build-artifacts"
STORAGE_TESTS="${GOBLINOS_BASE}/test-reports"
STORAGE_LOGS="${GOBLINOS_BASE}/logs"

# Docker daemon configuration
DOCKER_BUILDKIT_CACHE_DIR="${GOBLINOS_BASE}/docker-cache"
BUILDKIT_PROGRESS=plain
EOF
    echo "✅ Created .env.storage"
else
    echo "ℹ️  .env.storage already exists, skipping..."
fi

# Setup node_modules symlink
echo ""
echo "🔗 Setting up node_modules symlink..."
if [ -d "$PROJECT_ROOT/apps/web/node_modules" ]; then
    echo "   Moving existing node_modules to GOBLINOS..."
    mv "$PROJECT_ROOT/apps/web/node_modules" "$GOBLINOS_PATH/node_modules.backup.$(date +%s)"
fi

if [ ! -L "$PROJECT_ROOT/apps/web/node_modules" ]; then
    mkdir -p "$GOBLINOS_PATH/node_modules"
    ln -s "$GOBLINOS_PATH/node_modules" "$PROJECT_ROOT/apps/web/node_modules"
    echo "✅ Created symlink: apps/web/node_modules → GOBLINOS"
else
    echo "ℹ️  Symlink already exists"
fi

# Setup Python venv
echo ""
echo "🐍 Setting up Python virtual environment on GOBLINOS..."
if [ ! -d "$GOBLINOS_PATH/venv/bin" ]; then
    python3 -m venv "$GOBLINOS_PATH/venv"
    echo "✅ Created Python venv at GOBLINOS"
fi

# Activate and install dependencies
source "$GOBLINOS_PATH/venv/bin/activate"
echo "✅ Activated venv"

if [ -f "$PROJECT_ROOT/apps/api/requirements.txt" ]; then
    echo "   Installing Python dependencies..."
    pip install -q -r "$PROJECT_ROOT/apps/api/requirements.txt"
    echo "✅ Python dependencies installed"
fi

deactivate

# Create docker-compose override for volumes
echo ""
echo "🐳 Creating Docker Compose override..."
cat > "$PROJECT_ROOT/docker-compose.goblinos-override.yml" << 'EOF'
# Docker Compose Override for External Storage
# Usage: docker-compose -f docker-compose.yml -f docker-compose.goblinos-override.yml up

version: '3.8'

services:
  postgres:
    volumes:
      - /Volumes/GOBLINOS\ 1/goblin-assistant/postgres-data:/var/lib/postgresql/data

  redis:
    volumes:
      - /Volumes/GOBLINOS\ 1/goblin-assistant/redis-data:/data

# BuildKit cache configuration
# Add to docker daemon.json: "builder": { "gc": { "policy": [{ "all": true, "maxUnusedBuildCacheSize": "10gb" }] } }
EOF
echo "✅ Created docker-compose.goblinos-override.yml"

# Create .gitignore updates documentation
echo ""
echo "📋 Creating storage-aware .gitignore guide..."
cat > "$PROJECT_ROOT/GOBLINOS_STORAGE_README.md" << 'EOF'
# External Storage Configuration

This project is configured to use a GOBLINOS external hard drive for large artifacts to prevent memory issues.

## Drive Location
- **Mount Path**: `/Volumes/GOBLINOS 1/goblin-assistant`

## Configured Directories

| Directory | Purpose | Size Impact |
|-----------|---------|------------|
| `node_modules/` | Frontend dependencies | ~500MB-1GB |
| `venv/` | Python virtual environment | ~200-400MB |
| `postgres-data/` | Database files | Variable (likely 100MB-1GB) |
| `redis-data/` | Cache and session store | Variable (100-500MB) |
| `build-artifacts/` | .next, dist, coverage | ~200-500MB |
| `docker-cache/` | Docker build cache | Variable (can reach 10GB+) |
| `test-reports/` | Jest, pytest, E2E results | ~50-200MB |
| `logs/` | Application logs | Variable |

## Setup Instructions

```bash
# 1. Run the setup script (one-time)
./scripts/setup-external-storage.sh

# 2. Source the storage configuration
source .env.storage

# 3. For Docker operations, use the override file
docker-compose -f docker-compose.yml -f docker-compose.goblinos-override.yml up

# 4. For Python development, activate the venv
source /Volumes/GOBLINOS\ 1/goblin-assistant/venv/bin/activate
```

## Verification

```bash
# Check storage usage
df -h /Volumes/GOBLINOS\ 1/

# Verify symlinks
ls -la apps/web/node_modules
ls -la .next

# Check venv
which python3  # Should show: /Volumes/GOBLINOS.../venv/bin/python3
```

## Environment Variables

The `.env.storage` file provides these variables:
- `GOBLINOS_BASE`: Base path on external drive
- `STORAGE_NODE_MODULES`: npm dependencies
- `STORAGE_VENV`: Python virtual environment
- `STORAGE_DOCKER_CACHE`: Docker build cache
- `DOCKER_BUILDKIT_CACHE_DIR`: BuildKit cache location

Load in your shell: `source .env.storage`

## CI/CD Considerations

When running in CI:
- Skip symlinking if GOBLINOS is unavailable
- Use local storage for CI environments
- Consider conditional configuration in scripts

## Troubleshooting

**Problem**: "GOBLINOS drive not found"
- Ensure the drive is mounted: `mount | grep GOBLINOS`
- Or manually mount: Check System Preferences → Devices

**Problem**: "Symlink permission denied"
- Run setup script with appropriate permissions

**Problem**: "Docker can't find volumes"
- Ensure docker-compose uses the override file
- Check mount paths in docker-compose.goblinos-override.yml

**Problem**: "venv activation fails"
- Verify Python installation: `python3 --version`
- Reinstall venv: `python3 -m venv /Volumes/GOBLINOS\ 1/goblin-assistant/venv`
EOF
echo "✅ Created docs/runbooks/GOBLINOS_STORAGE_README.md"

# Create a convenience activation script
echo ""
echo "⚙️  Creating convenience scripts..."
cat > "$PROJECT_ROOT/scripts/load-storage-env.sh" << 'EOF'
#!/bin/bash
# Load GOBLINOS storage environment variables

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ -f "$PROJECT_ROOT/.env.storage" ]; then
    set -a
    source "$PROJECT_ROOT/.env.storage"
    set +a
    echo "✅ Loaded storage configuration from .env.storage"
    echo "   GOBLINOS_BASE: $GOBLINOS_BASE"
else
    echo "❌ ERROR: .env.storage not found"
    echo "   Run: ./scripts/setup-external-storage.sh"
    exit 1
fi
EOF

chmod +x "$PROJECT_ROOT/scripts/load-storage-env.sh"
echo "✅ Created scripts/load-storage-env.sh"

# Final summary
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "✅ EXTERNAL STORAGE SETUP COMPLETE"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "📍 Storage Location: $GOBLINOS_PATH"
echo "💾 Available Directories:"
ls -lh "$GOBLINOS_PATH" | tail -n +2 | awk '{print "   • " $9 " (" $5 ")"}'
echo ""
echo "📚 Documentation: docs/runbooks/GOBLINOS_STORAGE_README.md"
echo ""
echo "🚀 Quick Start:"
echo "   1. Load config: source .env.storage"
echo "   2. Check setup: df -h /Volumes/GOBLINOS\ 1/"
echo "   3. Install deps: npm install && pip install -r apps/api/requirements.txt"
echo ""
echo "🐳 Docker: docker-compose -f docker-compose.yml -f docker-compose.goblinos-override.yml up"
echo ""
