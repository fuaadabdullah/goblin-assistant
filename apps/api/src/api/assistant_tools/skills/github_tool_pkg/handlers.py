from __future__ import annotations

import base64
from typing import Any, Dict, List, Optional

from .client import get, post


async def handle_github_get_repo(owner: str, repo: str) -> Dict[str, Any]:
    data = await get(f"/repos/{owner}/{repo}")
    if "error" in data:
        return data
    return {
        "full_name": data.get("full_name"),
        "description": data.get("description"),
        "url": data.get("html_url"),
        "stars": data.get("stargazers_count"),
        "forks": data.get("forks_count"),
        "open_issues": data.get("open_issues_count"),
        "default_branch": data.get("default_branch"),
        "language": data.get("language"),
        "private": data.get("private"),
        "topics": data.get("topics", []),
    }


async def handle_github_list_repos(
    owner: str,
    owner_type: str = "user",
    limit: int = 30,
) -> Dict[str, Any]:
    path = (
        f"/users/{owner}/repos"
        if owner_type == "user"
        else f"/orgs/{owner}/repos"
    )
    data = await get(path, {"per_page": min(limit, 100), "sort": "updated"})
    if isinstance(data, dict) and "error" in data:
        return data
    repos = [
        {
            "name": r.get("name"),
            "full_name": r.get("full_name"),
            "description": r.get("description"),
            "url": r.get("html_url"),
            "stars": r.get("stargazers_count"),
            "language": r.get("language"),
            "private": r.get("private"),
            "updated_at": r.get("updated_at"),
        }
        for r in (data if isinstance(data, list) else [])
    ]
    return {"repos": repos, "count": len(repos)}


async def handle_github_list_issues(
    owner: str,
    repo: str,
    state: str = "open",
    limit: int = 20,
) -> Dict[str, Any]:
    data = await get(
        f"/repos/{owner}/{repo}/issues",
        {"state": state, "per_page": min(limit, 100)},
    )
    if isinstance(data, dict) and "error" in data:
        return data
    issues = [
        {
            "number": i.get("number"),
            "title": i.get("title"),
            "state": i.get("state"),
            "url": i.get("html_url"),
            "user": i.get("user", {}).get("login"),
            "labels": [lb["name"] for lb in i.get("labels", [])],
            "created_at": i.get("created_at"),
            "comments": i.get("comments"),
        }
        for i in (data if isinstance(data, list) else [])
        if "pull_request" not in i
    ]
    return {"issues": issues, "count": len(issues)}


async def handle_github_get_issue(
    owner: str,
    repo: str,
    number: int,
) -> Dict[str, Any]:
    data = await get(f"/repos/{owner}/{repo}/issues/{number}")
    if "error" in data:
        return data
    return {
        "number": data.get("number"),
        "title": data.get("title"),
        "state": data.get("state"),
        "url": data.get("html_url"),
        "body": data.get("body"),
        "user": data.get("user", {}).get("login"),
        "labels": [lb["name"] for lb in data.get("labels", [])],
        "assignees": [a["login"] for a in data.get("assignees", [])],
        "created_at": data.get("created_at"),
        "updated_at": data.get("updated_at"),
        "comments": data.get("comments"),
    }


async def handle_github_create_issue(
    owner: str,
    repo: str,
    title: str,
    body: Optional[str] = None,
    labels: Optional[List[str]] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"title": title}
    if body:
        payload["body"] = body
    if labels:
        payload["labels"] = labels
    data = await post(f"/repos/{owner}/{repo}/issues", payload)
    if "error" in data:
        return data
    return {
        "number": data.get("number"),
        "title": data.get("title"),
        "url": data.get("html_url"),
        "state": data.get("state"),
    }


async def handle_github_add_comment(
    owner: str,
    repo: str,
    number: int,
    body: str,
) -> Dict[str, Any]:
    data = await post(
        f"/repos/{owner}/{repo}/issues/{number}/comments",
        {"body": body},
    )
    if "error" in data:
        return data
    return {
        "id": data.get("id"),
        "url": data.get("html_url"),
        "created_at": data.get("created_at"),
    }


async def handle_github_list_prs(
    owner: str,
    repo: str,
    state: str = "open",
    limit: int = 20,
) -> Dict[str, Any]:
    data = await get(
        f"/repos/{owner}/{repo}/pulls",
        {"state": state, "per_page": min(limit, 100)},
    )
    if isinstance(data, dict) and "error" in data:
        return data
    prs = [
        {
            "number": pr.get("number"),
            "title": pr.get("title"),
            "state": pr.get("state"),
            "url": pr.get("html_url"),
            "user": pr.get("user", {}).get("login"),
            "head": pr.get("head", {}).get("ref"),
            "base": pr.get("base", {}).get("ref"),
            "draft": pr.get("draft"),
            "created_at": pr.get("created_at"),
        }
        for pr in (data if isinstance(data, list) else [])
    ]
    return {"pull_requests": prs, "count": len(prs)}


async def handle_github_get_pr(
    owner: str,
    repo: str,
    number: int,
) -> Dict[str, Any]:
    data = await get(f"/repos/{owner}/{repo}/pulls/{number}")
    if "error" in data:
        return data
    return {
        "number": data.get("number"),
        "title": data.get("title"),
        "state": data.get("state"),
        "url": data.get("html_url"),
        "body": data.get("body"),
        "user": data.get("user", {}).get("login"),
        "head": data.get("head", {}).get("ref"),
        "base": data.get("base", {}).get("ref"),
        "draft": data.get("draft"),
        "mergeable": data.get("mergeable"),
        "commits": data.get("commits"),
        "additions": data.get("additions"),
        "deletions": data.get("deletions"),
        "changed_files": data.get("changed_files"),
        "created_at": data.get("created_at"),
        "updated_at": data.get("updated_at"),
    }


async def handle_github_create_pr(
    owner: str,
    repo: str,
    title: str,
    head: str,
    base: str,
    body: Optional[str] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"title": title, "head": head, "base": base}
    if body:
        payload["body"] = body
    data = await post(f"/repos/{owner}/{repo}/pulls", payload)
    if "error" in data:
        return data
    return {
        "number": data.get("number"),
        "title": data.get("title"),
        "url": data.get("html_url"),
        "state": data.get("state"),
        "draft": data.get("draft"),
    }


async def handle_github_get_file(
    owner: str,
    repo: str,
    path: str,
    ref: Optional[str] = None,
) -> Dict[str, Any]:
    params: Dict[str, str] = {}
    if ref:
        params["ref"] = ref
    data = await get(f"/repos/{owner}/{repo}/contents/{path}", params)
    if "error" in data:
        return data
    if data.get("type") != "file":
        return {"error": f"Path is not a file: {path}"}

    content_b64 = data.get("content", "")
    try:
        content = base64.b64decode(content_b64).decode("utf-8", errors="replace")
    except Exception:
        content = content_b64

    return {
        "path": data.get("path"),
        "name": data.get("name"),
        "size": data.get("size"),
        "sha": data.get("sha"),
        "url": data.get("html_url"),
        "content": content,
    }


async def handle_github_search_code(
    query: str,
    limit: int = 10,
) -> Dict[str, Any]:
    data = await get(
        "/search/code",
        {"q": query, "per_page": min(limit, 30)},
    )
    if "error" in data:
        return data
    items = data.get("items", [])
    results = [
        {
            "name": item.get("name"),
            "path": item.get("path"),
            "repo": item.get("repository", {}).get("full_name"),
            "url": item.get("html_url"),
            "sha": item.get("sha"),
        }
        for item in items
    ]
    return {
        "results": results,
        "total_count": data.get("total_count"),
        "returned": len(results),
    }


__all__ = [
    "handle_github_add_comment",
    "handle_github_create_issue",
    "handle_github_create_pr",
    "handle_github_get_file",
    "handle_github_get_issue",
    "handle_github_get_pr",
    "handle_github_get_repo",
    "handle_github_list_issues",
    "handle_github_list_prs",
    "handle_github_list_repos",
    "handle_github_search_code",
]
