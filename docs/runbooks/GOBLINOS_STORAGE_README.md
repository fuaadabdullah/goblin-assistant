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
ls -la src/node_modules
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
