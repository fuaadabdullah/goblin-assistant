#!/usr/bin/env python3
"""
Run Rovo Dev autofix directly in CircleCI on job failure via ACLI.
ACLI is installed by the trigger-autofix CircleCI command before this runs.
"""

import os
import subprocess


def sh(cmd: str) -> str:
    try:
        return subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL).strip()
    except subprocess.CalledProcessError:
        return ""


def main() -> None:
    # Loop guard: don't autofix an autofix commit.
    if "[autofix]" in sh("git log -1 --format=%B"):
        print("Last commit was already an autofix — skipping to prevent loop.")
        return

    branch = os.environ.get("CIRCLE_BRANCH", "")
    job = os.environ.get("CIRCLE_JOB", "unknown")
    build_url = os.environ.get("CIRCLE_BUILD_URL", "")
    owner = os.environ.get("CIRCLE_PROJECT_USERNAME", "")
    repo = os.environ.get("CIRCLE_PROJECT_REPONAME", "")
    github_token = os.environ.get("GITHUB_TOKEN", "")

    diff_stat = sh("git diff origin/main...HEAD --stat") or sh("git diff HEAD~1 --stat")
    recent_commits = sh("git log --oneline -5")

    failure_output = ""
    try:
        with open("/tmp/ci_failure_output.txt") as f:
            failure_output = f.read()[-6000:]
    except OSError:
        pass

    # Configure git to push via GITHUB_TOKEN
    if github_token and owner and repo:
        subprocess.run(
            f"git remote set-url origin https://{github_token}@github.com/{owner}/{repo}.git",
            shell=True, check=False,
        )
    subprocess.run('git config user.email "ci-autofix@goblin-assistant.app"', shell=True)
    subprocess.run('git config user.name "Goblin CI Autofix"', shell=True)

    prompt = f"""CI job `{job}` failed on branch `{branch}`.
Build: {build_url}

## Changed files vs main
```
{diff_stat}
```

## Recent commits
```
{recent_commits}
```

## Test / lint output
```
{failure_output or "(not captured — read the relevant source files to diagnose)"}
```

Fix the failure with the minimum code change needed.
- Do NOT modify test assertions unless the test itself is clearly wrong.
- Do NOT refactor beyond the minimum needed to fix the failure.
- After making changes, commit with message: fix(ci): autofix {job} failure [autofix]
- Then push to branch `{branch}`.
"""

    print(f"Running Rovo Dev autofix for '{job}' on '{branch}'...")
    result = subprocess.run(["acli", "rovodev", "run", "--yolo", prompt], check=False)

    if result.returncode != 0:
        print(f"Rovo Dev exited with code {result.returncode} — manual fix required.")
        return

    # Commit if Rovo made changes but didn't commit (belt-and-suspenders)
    if sh("git status --porcelain"):
        subprocess.run(
            f'git add -A && git commit -m "fix(ci): autofix {job} failure [autofix]"',
            shell=True, check=False,
        )

    # Push if there are unpushed commits
    if sh(f"git log origin/{branch}..HEAD --oneline 2>/dev/null"):
        result = subprocess.run(f"git push origin {branch}", shell=True, check=False)
        if result.returncode == 0:
            print(f"Fix pushed to {branch} — CircleCI will re-run automatically.")
        else:
            print("Push failed — check GITHUB_TOKEN permissions.")


if __name__ == "__main__":
    main()
