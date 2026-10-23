"""Prevent public scripts from exposing a personal cloud account identity."""
from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess


SCRIPT = Path(__file__).resolve().parents[1] / "infra" / "gcp-llm-setup.sh"


def test_gcp_setup_never_publishes_literal_account_emails():
    source = SCRIPT.read_text(encoding="utf-8")
    assert not re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}", source)
    assert 'ACCOUNT="${GCP_ACCOUNT_EMAIL:-}"' in source


def test_gcp_setup_requires_explicit_account_identity():
    env = os.environ.copy()
    env.pop("GCP_ACCOUNT_EMAIL", None)
    result = subprocess.run(
        ["bash", str(SCRIPT), "help"], env=env,
        text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        check=False,
    )
    assert result.returncode != 0
    assert "GCP_ACCOUNT_EMAIL" in result.stderr


def test_gcp_setup_passes_shell_syntax_check():
    subprocess.run(["bash", "-n", str(SCRIPT)], check=True)
