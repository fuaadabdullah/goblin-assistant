# FRICTION

**During use, you log — you do not fix.**

One line per pain: what you asked | what happened | what you expected.

Rules:

- Log product friction here while the run is active.
- If the environment bails out, record the blocked step and stop. Do not turn
  the session into repair work.
- Do not write retrospective "findings" from predictions, guesses, or prior
  opinions.
- If there are no entries, the result is "no entries," not a synthesized brief.

---

## 2026-07-24 — Docker + frontend integration run

**Environment bailout — Docker zombie process.**

`make api-docker-up` (6:17 AM run) spawned a `docker compose up -d redis goblin-assistant-backend` process (PID 1225) that ran for 1 h 30+ min, doing a full pip install including PyTorch 906 MB inside the Docker VM. The BuildKit `# syntax=docker/dockerfile:1.7-labs` line in `Dockerfile` caused the initial gRPC frontend crash but the BuildKit server job continued running. Multiple attempts to bring up the stack launched competing `docker compose` processes. The backend containers repeatedly reached healthy state (`curl http://127.0.0.1:8001/health → {overall: healthy}`) but were immediately displaced by whichever zombie build finished next. Environment: PID 1225 must be killed before the stack is stable.

**Severity:** Tier 0 blocker (environment, not product). Blocked ritual.

**What fixed in this run:**

- `Dockerfile` line 1: removed `# syntax=docker/dockerfile:1.7-labs` (gRPC frontend crash). New: no syntax directive.
- `.env` line 17: `BACKEND_URL=http://localhost:8004` → `http://localhost:8001` (port mismatch with compose config).
- `Dockerfile` user added `INSTALL_VECTOR_DEPS` arg with conditional to allow lean local builds (skips torch/chromadb/transformers).

**Proxy / frontend (separate issue):**
`make web-dev` started Next.js 16.2.6 (Turbopack, 2.7 min compile). Server printed "ready" on `[::]:3000` but all HTTP requests hung indefinitely — TCP connections established, no HTTP response, even to `/_next/static/`. No request log lines appeared in the dev server output after "ready". Fresh restart exhibited same behaviour. System under concurrent load (vitest workers, Docker VM pip install). Not confirmed whether this is an external-drive I/O issue, memory pressure, or a Turbopack on-demand compilation deadlock.

**Severity:** Dogfood blocker — resolved after identifying root cause.

**Root causes found and addressed this run:**

1. **Slow filesystem for `.next` cache** — `/Volumes/GOBLINOS/.../.next/dev` is an external USB drive. Turbopack benchmark: 3613ms. Cache compaction: 20.8min. This blocked every HTTP response during compaction and caused apparent hangs.

   Fix: symlink `.next` to **fresh** local cache and set TMPDIR:

   ```bash
   rm -rf apps/web/.next/
   rm -rf /tmp/nextcache && mkdir /tmp/nextcache
   ln -s /tmp/nextcache apps/web/.next
   cd apps/web && TMPDIR=/tmp NEXT_TELEMETRY_DISABLED=1 pnpm dev
   ```

   Critical: **use webpack mode (`--turbo=false`)** — Turbopack's RocksDB cache corrupts after restarts AND after serving a few requests, causing complete server lockup (TCP connects, HTTP never responds, no error in log). Webpack mode is stable: first request ~43s (full build), second ~2s, third+ ~107ms indefinitely.

2. **Port 3000 silently displaced to 3001** — an orphaned Next.js process held port 3000; the new server fell back to 3001 with only a warning in the log (not an error). All proxy tests targeted port 3000 and got ECONNREFUSED. Fix: `pkill -f "next dev"` before starting.

3. **Next.js patched `fetch` hangs on ECONNREFUSED** — Next.js's instrumented global `fetch` does not fast-fail on connection refused to localhost, unlike native Node.js `fetch` (which fails in ~74ms). The health route's `fetchWithTimeout` with 5s AbortController is the correct mitigation; it fires once the backend is up.

**Verified working (end of run):**

- `curl http://127.0.0.1:8001/api/v1/health` → `status: healthy` (api, redis, db, routing all green)
- `http://[::1]:3000/api/health` → `200 healthy` (proxy → backend round-trip confirmed)
- `http://[::1]:3000/api/auth/validate` → `200` (auth endpoint reachable)

**Outstanding (not tested this run):**

- Login UI flow in browser (Supabase OAuth redirect)
- Chat end-to-end (requires provider keys in env)
- Mobile / tablet viewport
