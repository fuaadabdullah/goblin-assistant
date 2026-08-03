# Docker & PC Optimization Notes

Generated during a tuning pass for the goblin-assistant repo on a Windows 11 Pro
workstation with an AMD Ryzen 7 5700X (8C/16T), 64 GB RAM, and Docker Desktop
(WSL2 backend).

## What changed

### 1. WSL2 resource allocation (`C:\Users\Admin\.wslconfig`)

Before the change, Docker Desktop only exposed **4 CPUs / ~8 GB RAM** to
countainers. The new config allocates:

- `memory=32GB` — half the physical RAM, leaving 32 GB for Windows + games.
- `processors=12` — 12 of 16 logical processors for WSL2/Docker.
- `swap=0` — prevents WSL2 from swapping into the Windows pagefile.
- `pageReporting=false` — games won't see WSL2 swap as available memory.
- `guiApplications=false` — WSLg is disabled to reduce overhead.

Apply it:

```powershell
wsl --shutdown
# Then restart Docker Desktop from the system tray or Start menu
```

### 2. Docker daemon configuration (`C:\Users\Admin\.docker\daemon.json`)

- Enables BuildKit explicitly.
- Caps container logs at 10 MB × 3 files per container to prevent disk bloat.
- Enables build-cache garbage collection with a 50 GB default keep storage.

Restart Docker Desktop after editing.

### 3. Project Dockerfile optimizations

- Added `PIP_NO_CACHE_DIR=1` and `PYTHONDONTWRITEBYTECODE=1` globally.
- Converted `apt` and `pip` layers to use BuildKit cache mounts:
  - `/var/cache/apt`
  - `/var/lib/apt/lists`
  - `/root/.cache/pip`
- Removed redundant `rm -rf /var/lib/apt/lists/*` because cache mounts handle
  cleanup.
- Deduplicated `PYTHONDONTWRITEBYTECODE` env var.

These changes make repeated builds significantly faster without changing image
contents.

### 4. Docker Compose profiles

Three compose files are now available:

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Default dev stack (Redis + backend), conservative limits. |
| `docker-compose.performance.yml` | Higher limits + reservations for heavy coding/testing sessions. |
| `docker-compose.gaming.yml` | Low limits so games get the resources while keeping the backend alive. |

Usage:

```bash
# Coding / heavy testing
docker compose -f docker-compose.yml -f docker-compose.performance.yml up -d

# Gaming session
docker compose -f docker-compose.yml -f docker-compose.gaming.yml up -d

# Standard lean dev
docker compose up -d
```

`docker-compose.yml` also gained explicit tmpfs sizes (`/tmp:size=256m`) to
prevent unbounded in-memory growth.

### 5. Windows PC tuning script

`scripts/ops/optimize-windows.ps1` applies reversible gaming/coding tweaks:

- High-performance power plan.
- Game Mode enabled.
- Best-performance visual effects.
- Hibernation disabled (frees disk space equal to RAM size).
- Fixed-size pagefile on the system drive.
- SysMain (Superfetch) and non-essential telemetry/search services disabled.
- Developer Mode enabled.

Run as Administrator:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/ops/optimize-windows.ps1
```

Then restart Windows.

### 6. `.dockerignore` additions

Excludes more build caches, local SSL certs, OS artifacts, and the new compose
override/tuning files so Docker build context stays lean.

## Quick verification

After restarting Docker Desktop/WSL2:

```powershell
docker info --format "CPUs: {{.NCPU}}, Memory: {{.MemTotal}}"
# Should show ~12 CPUs and ~32 GB

# Test a lean build
docker build --target deps -t goblin-assistant-deps .

# Test the default stack
docker compose up -d redis goblin-assistant-backend
curl http://127.0.0.1:8001/api/v1/health
```

## Undo / rollback

- WSL2: edit `C:\Users\Admin\.wslconfig` or delete it, then `wsl --shutdown`.
- Docker daemon: edit/delete `C:\Users\Admin\.docker\daemon.json`, restart
  Docker Desktop.
- Windows tuning: re-enable services in `services.msc`, restore power plan via
  Settings, and set the pagefile back to "System managed size".
- Compose limits: remove the `-f docker-compose.performance.yml` / `-f
  docker-compose.gaming.yml` override or adjust `.env` values.
