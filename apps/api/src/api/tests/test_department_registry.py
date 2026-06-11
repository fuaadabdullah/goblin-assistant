"""Tests for departments/registry.py — DEPARTMENT_REGISTRY singleton and DepartmentRegistry."""

from __future__ import annotations

import pytest

from api.departments.models import DepartmentId, DepartmentPolicy
from api.departments.registry import DEPARTMENT_REGISTRY, DepartmentRegistry

# ── DepartmentRegistry.list_ids ───────────────────────────────────────────────


class TestListIds:
    def test_returns_list_of_strings(self):
        ids = DEPARTMENT_REGISTRY.list_ids()
        assert isinstance(ids, list)
        assert all(isinstance(i, str) for i in ids)

    def test_contains_all_seven_departments(self):
        ids = DEPARTMENT_REGISTRY.list_ids()
        assert len(ids) == 7

    def test_contains_expected_ids(self):
        ids = DEPARTMENT_REGISTRY.list_ids()
        for expected in (
            "general",
            "reasoning",
            "coding",
            "creative",
            "recall",
            "tool_use",
            "research",
        ):
            assert expected in ids

    def test_ids_are_lowercase(self):
        for id_ in DEPARTMENT_REGISTRY.list_ids():
            assert id_ == id_.lower()


# ── DepartmentRegistry.list_public ───────────────────────────────────────────


class TestListPublic:
    def test_returns_list_of_dicts(self):
        result = DEPARTMENT_REGISTRY.list_public()
        assert isinstance(result, list)
        assert all(isinstance(item, dict) for item in result)

    def test_each_item_has_required_keys(self):
        for item in DEPARTMENT_REGISTRY.list_public():
            for key in (
                "department",
                "name",
                "description",
                "supports_streaming",
                "supports_tools",
            ):
                assert key in item, f"missing key {key!r} in {item}"

    def test_no_provider_chain_leakage(self):
        for item in DEPARTMENT_REGISTRY.list_public():
            assert "provider_chain" not in item
            assert "provider" not in " ".join(item.keys())

    def test_count_matches_list_ids(self):
        assert len(DEPARTMENT_REGISTRY.list_public()) == len(DEPARTMENT_REGISTRY.list_ids())

    def test_department_values_are_valid_department_ids(self):
        for item in DEPARTMENT_REGISTRY.list_public():
            assert item["department"] in DEPARTMENT_REGISTRY.list_ids()


# ── DepartmentRegistry.list_policies ─────────────────────────────────────────


class TestListPolicies:
    def test_returns_list_of_policies(self):
        policies = DEPARTMENT_REGISTRY.list_policies()
        assert isinstance(policies, list)
        assert all(isinstance(p, DepartmentPolicy) for p in policies)

    def test_count_matches_ids(self):
        assert len(DEPARTMENT_REGISTRY.list_policies()) == len(DEPARTMENT_REGISTRY.list_ids())


# ── DepartmentRegistry.get ────────────────────────────────────────────────────


class TestGet:
    def test_get_general_returns_policy(self):
        policy = DEPARTMENT_REGISTRY.get(DepartmentId.GENERAL)
        assert isinstance(policy, DepartmentPolicy)
        assert policy.department_id is DepartmentId.GENERAL

    def test_get_reasoning_has_tools(self):
        policy = DEPARTMENT_REGISTRY.get(DepartmentId.REASONING)
        assert policy.supports_tools is True

    def test_get_each_department_id_succeeds(self):
        for dept_id in DepartmentId:
            policy = DEPARTMENT_REGISTRY.get(dept_id)
            assert policy.department_id is dept_id

    def test_get_unknown_raises_key_error(self):
        fake_registry = DepartmentRegistry({})
        with pytest.raises(KeyError):
            fake_registry.get(DepartmentId.GENERAL)

    def test_each_policy_has_non_empty_chain(self):
        for dept_id in DepartmentId:
            policy = DEPARTMENT_REGISTRY.get(dept_id)
            assert len(policy.provider_chain) > 0, f"{dept_id.value} has empty provider_chain"


# ── DepartmentRegistry.get_by_id_str ─────────────────────────────────────────


class TestGetByIdStr:
    def test_lowercase_string_returns_correct_policy(self):
        policy = DEPARTMENT_REGISTRY.get_by_id_str("general")
        assert policy.department_id is DepartmentId.GENERAL

    def test_uppercase_string_succeeds(self):
        policy = DEPARTMENT_REGISTRY.get_by_id_str("GENERAL")
        assert policy.department_id is DepartmentId.GENERAL

    def test_mixed_case_string_succeeds(self):
        policy = DEPARTMENT_REGISTRY.get_by_id_str("Reasoning")
        assert policy.department_id is DepartmentId.REASONING

    def test_whitespace_stripped(self):
        policy = DEPARTMENT_REGISTRY.get_by_id_str("  coding  ")
        assert policy.department_id is DepartmentId.CODING

    def test_matches_get_result(self):
        assert DEPARTMENT_REGISTRY.get_by_id_str("general") == DEPARTMENT_REGISTRY.get(
            DepartmentId.GENERAL
        )

    def test_unknown_string_raises_value_error(self):
        with pytest.raises(ValueError):
            DEPARTMENT_REGISTRY.get_by_id_str("nonexistent")

    def test_all_department_strings_work(self):
        for id_ in DEPARTMENT_REGISTRY.list_ids():
            policy = DEPARTMENT_REGISTRY.get_by_id_str(id_)
            assert policy.department_id.value == id_


# ── DepartmentRegistry.provider_supports_tools ───────────────────────────────


class TestProviderSupportsTools:
    def test_provider_in_tools_dept_chain_returns_true(self):
        # Get the primary provider of a dept that supports tools
        tools_policy = DEPARTMENT_REGISTRY.get(DepartmentId.TOOL_USE)
        assert tools_policy.supports_tools is True
        primary_pid, _ = tools_policy.primary_provider
        assert DEPARTMENT_REGISTRY.provider_supports_tools(primary_pid) is True

    def test_nonexistent_provider_returns_false(self):
        assert DEPARTMENT_REGISTRY.provider_supports_tools("completely_fake_provider_xyz") is False

    def test_provider_in_tools_only_dept_detects_correctly(self):
        # Any provider that appears in a tools-enabled dept should return True
        for policy in DEPARTMENT_REGISTRY.list_policies():
            if policy.supports_tools:
                for pid, _ in policy.provider_chain:
                    result = DEPARTMENT_REGISTRY.provider_supports_tools(pid)
                    assert result is True, (
                        f"expected True for {pid} (in {policy.department_id.value})"
                    )
                break  # one dept is enough
