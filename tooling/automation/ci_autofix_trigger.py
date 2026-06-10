#!/usr/bin/env python3
"""Called on CI failure — fires repository_dispatch to invoke Rovo Dev autofix."""

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request


def run(cmd: str) -> str:
    try:
        return subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL).strip()
    except subprocess.CalledProcessError:
        return ""


def main() -> None:
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        print("GITHUB_TOKEN not set — skipping autofix trigger.")
        return

    # Loop guard: skip if the commit that just failed was itself an autofix.
    last_msg = run("git log -1 --format=%B")
    if "[autofix]" in last_msg:
        print("Last commit was already an autofix — skipping to prevent infinite loop.")
        return

    owner = os.environ.get("CIRCLE_PROJECT_USERNAME", "")
    repo_name = os.environ.get("CIRCLE_PROJECT_REPONAME", "")
    branch = os.environ.get("CIRCLE_BRANCH", "")
    job = os.environ.get("CIRCLE_JOB", "unknown")
    build_url = os.environ.get("CIRCLE_BUILD_URL", "")
    workflow_id = os.environ.get("CIRCLE_WORKFLOW_ID", "")

    if not all([owner, repo_name, branch]):
        print("Missing CircleCI env vars — skipping autofix trigger.")
        return

    diff_stat = run("git diff origin/main...HEAD --stat") or run("git diff HEAD~1 --stat")
    recent_commits = run("git log --oneline -5")

    # Capture test/lint output if a previous step wrote it to this file.
    failure_output_section = ""
    output_file = os.environ.get("FAILURE_OUTPUT_FILE", "")
    if output_file:
        try:
            with open(output_file) as f:
                tail = f.read()[-6000:]
            failure_output_section = f"\n## Captured output (last portion)\n```\n{tail}\n```\n"
        except OSError:
            pass

    prompt = f"""CI job `{job}` failed on branch `{branch}`.

Build: {build_url}

## Files changed vs main
```
{diff_stat}
```

## Recent commits on this branch
```
{recent_commits}
```
{failure_output_section}
Steps:
1. Read the relevant source files and failing tests/lint errors
2. Apply the minimal fix to make `{job}` pass — do not change test assertions unless the test itself is wrong
3. Commit with message: `fix(ci): autofix {job} failure [autofix]` and push to branch `{branch}`
"""

    payload = {
        "event_type": "goblin-coder",
        "client_payload": {
            "prompt": prompt,
            "task_id": workflow_id,
            "branch": branch,
            "job": job,
        },
    }

    url = f"https://api.github.com/repos/{owner}/{repo_name}/dispatches"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"token {token}",
            "Content-Type": "application/json",
            "Accept": "application/vnd.github.v3+json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            print(f"Autofix triggered for '{job}' on '{branch}' (HTTP {resp.status}).")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"Dispatch failed: {e.code} — {body}")
        sys.exit(1)


if __name__ == "__main__":
    main()
