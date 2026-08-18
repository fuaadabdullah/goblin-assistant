"""Validation helpers for user-submitted source code.

Used by sandbox paths and shared sanitization wrappers.
"""

from __future__ import annotations

import re
from typing import Any

from fastapi import HTTPException


def validate_source_code(source: str, language: str) -> tuple[str, dict[str, Any]]:
    """Validate source code for dangerous patterns before sandbox execution.

    Returns (sanitized_source, validation_report) where validation_report
    includes severity, blocked patterns, and warnings. Blocked sources raise
    HTTPException(400).
    """
    if not source or not isinstance(source, str):
        raise HTTPException(status_code=400, detail="Source code is required")

    report: dict[str, Any] = {
        "language": language,
        "length": len(source),
        "blocked_patterns": [],
        "warnings": [],
        "severity": "ok",
    }

    if language == "python":
        py_critical_patterns = [
            (r"\bimport\s+os\b", "os module import — potential filesystem escape"),
            (r"\bimport\s+subprocess\b", "subprocess module — process spawning"),
            (r"\bimport\s+socket\b", "socket module — network access"),
            (r"\bimport\s+ctypes\b", "ctypes module — native code execution"),
            (r"\bimport\s+multiprocessing\b", "multiprocessing — process spawning"),
            (
                r"\bimport\s+http\.server\b|\bimport\s+flask\b|\bimport\s+fastapi\b|\bimport\s+django\b",
                "web server import",
            ),
            (r"\b__import__\s*\(", "__import__ — dynamic module loading"),
            (r"\bcompile\s*\(.*,\s*.*,\s*[\"']exec[\"']", "compile with exec mode"),
            (r"\bexec\s*\(", "exec function — arbitrary code execution"),
            (r"\beval\s*\(", "eval function — arbitrary code execution"),
            (r"\bopen\s*\(.*[\"'](?:/etc|/proc|/sys|/dev)", "open() with system path"),
            (r"\bos\.(?:system|popen|exec|spawn)", "os.system/popen/exec/spawn"),
            (r"\bsubprocess\.(?:call|run|Popen|check_output)", "subprocess invocation"),
            (r"\bsocket\.(?:socket|connect|bind|listen)", "socket operations"),
            (r"\burllib\.|\brequests\.", "network request"),
        ]
        py_warning_patterns = [
            (r"\bimport\s+sys\b", "sys module import"),
            (r"\bsys\.(?:stdin|stdout|stderr)", "sys stdio access"),
            (r"\bwhile\s+True\s*:", "unbounded while loop"),
            (r"\b__del__\b", "__del__ destructor — side effects at GC"),
        ]
        for pattern, desc in py_critical_patterns:
            if re.search(pattern, source):
                report["blocked_patterns"].append(desc)
        for pattern, desc in py_warning_patterns:
            if re.search(pattern, source):
                report["warnings"].append(desc)
    elif language == "javascript":
        js_critical_patterns = [
            (r"\brequire\s*\(\s*[\"']child_process[\"']", "child_process require"),
            (r"\brequire\s*\(\s*[\"']net[\"']", "net module — network access"),
            (
                r"\brequire\s*\(\s*[\"']http[\"']|\brequire\s*\(\s*[\"']https[\"']",
                "http/https module",
            ),
            (r"\brequire\s*\(\s*[\"']express[\"']", "express — web server"),
            (r"\brequire\s*\(\s*[\"']vm[\"']", "vm module — code execution"),
            (r"\beval\s*\(", "eval — arbitrary code execution"),
            (r"\bnew\s+Function\s*\(", "new Function — arbitrary code execution"),
            (r"\bprocess\.(?:exit|kill|abort|cwd|chdir)", "process control"),
            (r"\bfetch\s*\(", "fetch — network request"),
            (r"\bXMLHttpRequest\b", "XMLHttpRequest — network request"),
            (r"\bWebSocket\b", "WebSocket — persistent network connection"),
            (r"\brequire\s*\(\s*[\"']os[\"']", "os module require"),
        ]
        js_warning_patterns = [
            (r"\bwhile\s*\(\s*true\s*\)", "unbounded while loop"),
            (r"\bsetTimeout\s*\(.*,\s*\d{5,}", "long-running setTimeout"),
            (r"\bsetInterval\b", "setInterval — may cause infinite loops"),
        ]
        for pattern, desc in js_critical_patterns:
            if re.search(pattern, source, re.IGNORECASE):
                report["blocked_patterns"].append(desc)
        for pattern, desc in js_warning_patterns:
            if re.search(pattern, source, re.IGNORECASE):
                report["warnings"].append(desc)

    if report["blocked_patterns"]:
        report["severity"] = "blocked"
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Source code contains blocked patterns",
                "blocked": report["blocked_patterns"],
                "severity": "blocked",
            },
        )

    if report["warnings"]:
        report["severity"] = "warning"

    return source, report


__all__ = ["validate_source_code"]
