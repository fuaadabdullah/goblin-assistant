#!/usr/bin/env python3
"""
Run Claude autofix directly inside CircleCI on job failure.
No GitHub Actions dependency — installs anthropic, runs an agentic loop,
commits the fix, and pushes to the PR branch.
"""

import json
import os
import subprocess
import sys

MAX_TURNS = 8

TOOLS = [
    {
        "name": "read_file",
        "description": "Read the contents of a file in the repo",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Relative path from repo root"}},
            "required": ["path"],
        },
    },
    {
        "name": "str_replace",
        "description": "Replace an exact string in a file (first occurrence)",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "old_str": {"type": "string"},
                "new_str": {"type": "string"},
            },
            "required": ["path", "old_str", "new_str"],
        },
    },
    {
        "name": "write_file",
        "description": "Overwrite a file with new content",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "run_command",
        "description": "Run a shell command and return combined stdout+stderr (max 4k chars)",
        "input_schema": {
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"],
        },
    },
]

_BLOCKED_CMDS = ["rm -rf /", "git push --force", "git reset --hard", "dd if="]


def handle_tool(name: str, inp: dict) -> str:
    if name == "read_file":
        try:
            with open(inp["path"]) as f:
                return f.read()
        except OSError as e:
            return f"Error: {e}"

    if name == "str_replace":
        path, old, new = inp["path"], inp["old_str"], inp["new_str"]
        try:
            with open(path) as f:
                text = f.read()
            if old not in text:
                return f"Error: old_str not found in {path}"
            with open(path, "w") as f:
                f.write(text.replace(old, new, 1))
            return f"Replaced in {path}"
        except OSError as e:
            return f"Error: {e}"

    if name == "write_file":
        path = inp["path"]
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w") as f:
            f.write(inp["content"])
        return f"Written {path}"

    if name == "run_command":
        cmd = inp["command"]
        for blocked in _BLOCKED_CMDS:
            if blocked in cmd:
                return f"Blocked: '{blocked}' is not allowed"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
        out = (result.stdout + result.stderr).strip()
        return out[:4000] if out else f"(exit {result.returncode}, no output)"

    return f"Unknown tool: {name}"


def sh(cmd: str) -> str:
    try:
        return subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL).strip()
    except subprocess.CalledProcessError:
        return ""


def main() -> None:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("ANTHROPIC_API_KEY not set — skipping autofix.")
        return

    # Loop guard: don't autofix an autofix commit.
    if "[autofix]" in sh("git log -1 --format=%B"):
        print("Last commit was already an autofix — skipping to prevent loop.")
        return

    branch = os.environ.get("CIRCLE_BRANCH", "")
    job = os.environ.get("CIRCLE_JOB", "unknown")
    build_url = os.environ.get("CIRCLE_BUILD_URL", "")
    owner = os.environ.get("CIRCLE_PROJECT_USERNAME", "")
    repo = os.environ.get("CIRCLE_PROJECT_REPONAME", "")

    diff_stat = sh("git diff origin/main...HEAD --stat") or sh("git diff HEAD~1 --stat")
    recent_commits = sh("git log --oneline -5")

    failure_output = ""
    try:
        with open("/tmp/ci_failure_output.txt") as f:
            failure_output = f.read()[-6000:]
    except OSError:
        pass

    # Configure git to push via GITHUB_TOKEN
    github_token = os.environ.get("GITHUB_TOKEN", "")
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

Fix the failure with the minimum code change needed:
1. Read the relevant source files first
2. Apply the fix using str_replace or write_file
3. Verify with run_command (re-run the failing check)
4. Commit: run_command("git add -A && git commit -m 'fix(ci): autofix {job} failure [autofix]'")
5. Push: run_command("git push origin {branch}")

Do NOT modify test assertions unless the test is clearly wrong.
Do NOT refactor beyond the minimum needed to fix the failure.
"""

    try:
        import anthropic  # installed by trigger-autofix command
    except ImportError:
        print("anthropic package not available — skipping autofix.")
        return

    client = anthropic.Anthropic(api_key=api_key)
    messages: list = [{"role": "user", "content": prompt}]

    for turn in range(MAX_TURNS):
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            tools=TOOLS,
            messages=messages,
        )

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            print("Autofix agent finished.")
            break

        if response.stop_reason != "tool_use":
            print(f"Unexpected stop_reason: {response.stop_reason}")
            break

        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                preview = json.dumps(block.input)[:100]
                print(f"  [{block.name}] {preview}")
                result = handle_tool(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

        messages.append({"role": "user", "content": tool_results})
    else:
        print(f"Reached max turns ({MAX_TURNS}) without finishing.")


if __name__ == "__main__":
    main()
