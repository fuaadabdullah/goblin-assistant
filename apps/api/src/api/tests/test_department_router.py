from __future__ import annotations

from api.departments.models import DepartmentId
from api.departments.router import classify_department


def test_finance_analyst_mode_routes_to_reasoning():
    selection = classify_department(mode="FINANCE_ANALYST")
    assert selection.department_id is DepartmentId.REASONING


def test_trading_forge_mode_does_not_claim_finance_override():
    selection = classify_department(mode="TRADING_FORGE")
    assert selection.department_id is DepartmentId.GENERAL
