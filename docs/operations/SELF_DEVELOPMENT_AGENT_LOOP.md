# Self-Development Agent Loop

This repository exposes a dogfooding loop for code-agent tasks. The backend owns task state, and a Fly.io Sprite worker owns repo checkout, Aider execution, tests, commits, and PR creation.

## Runtime Flow

1. A user submits a task from the `/agent` UI or a GitHub issue webhook.
2. The backend normalizes the request into `/api/v1/agent/task` and derives a persistent workspace identity from the repo and base branch.
3. The Sprite worker receives the task payload, restores or creates the matching workspace, and keeps `node_modules` / `venv` warm between runs.
4. The worker runs Aider in architect mode:
   - architect model: `router-reason`
   - editor model: `router-code`
5. Each coherent edit batch is auto-committed to the working branch.
6. The worker runs the Phase 0 CI set inside the Sprite:
   - `pytest`
   - `lint`
   - `build`
7. On failure, the worker captures the command output, feeds it back to Aider, and retries the loop up to the configured repair cap.
8. The worker uploads logs/artifacts, pushes the branch, and opens a PR with PyGithub when the run succeeds.
9. The backend remains the source of truth for task status, events, failure details, and the final PR URL.

## API Contract

- `POST /api/v1/agent/task`
  - Creates a task with `queued` status.
  - Accepts task text, optional repo and branch overrides, optional test command, and issue metadata.
- `GET /api/v1/agent/task/{task_id}`
  - Returns the persisted task record, including workspace identity and worker profile.
- `GET /api/v1/agent/task/{task_id}/events`
  - Returns the event history for polling or UI rendering.
- `POST /api/v1/agent/task/{task_id}/events`
  - Worker callback for progress updates and final task state.
  - When `AGENT_WORKER_CALLBACK_SECRET` is set, the worker must send `X-Agent-Worker-Token`.
- `POST /api/v1/agent/task/github-webhook`
  - Normalizes GitHub issue payloads into the same task schema.

## Required Environment

Backend:

- `GITHUB_REPOSITORY` or `AGENT_REPOSITORY_URL`
- `GITHUB_SERVER_URL` when the repo is not on `github.com`
- `AGENT_SPRITE_WORKER_URL`
- `AGENT_WORKER_SECRET`
- `AGENT_WORKER_CALLBACK_SECRET`
- `AGENT_BACKEND_URL`
- `AGENT_DEFAULT_BASE_BRANCH` and `AGENT_TEST_COMMAND` are optional defaults
- `AGENT_REPAIR_ATTEMPTS` caps the generate→test→repair loop

Worker:

- `FLY_API_TOKEN`
- `FLY_APP_NAME`
- `FLY_REGION`
- `GITHUB_TOKEN` as a fine-grained personal access token with branch, commit, and pull request permissions
- Repo checkout credentials for the target repository
- Provider access for `router-reason` and `router-code`
- Sprite networking is private-per-sandbox; host access stays blocked by hardware isolation

## Worker Contract

The worker payload includes:

- `task_id`, `task`, `repo_url`, `base_branch`, `branch_name`, and `tests_command`
- normalized `issue` metadata
- a persistent `workspace` object with the Sprite name, workspace family, and restore policy
- a `worker_profile` object that pins the Aider mode and model split
- a `phase0_ci_commands` list and repair-attempt cap for the generate→test→repair loop
- the callback URL and optional callback secret

The worker must:

- restore an existing Sprite when the workspace is healthy and compatible
- create a new Sprite when the workspace is missing or invalid
- ensure the repo checkout exists before planning or editing begins
- run Aider in architect mode with `router-reason` for planning and `router-code` for edits
- auto-commit each change batch to the working branch
- execute the Phase 0 CI commands, capture their output, and feed failures back to Aider
- push the branch and open a PR with `repo.create_pull(base=..., head=...)` through PyGithub when tests pass
- do not auto-merge to `main`; leave merge approval to a human reviewer
- report `planning`, `editing`, `testing`, `publishing`, `pr_opened`, `failed`, and `cancelled` progress states back to the callback URL

## Review Flow

- The worker opens the PR automatically once tests pass.
- A human reviews the diff, checks the test evidence, and merges.
- Failures stay visible in the task record so the UI can surface them without chasing worker logs.
- See [Phase Gates](./PHASE_GATES.md) for the recommended transition into the agent loop.
