"""Tests for product-facing labels layered over the internal departments."""

from __future__ import annotations

import pytest

from api.departments.models import DepartmentId
from api.departments.products import (
    get_product_info,
    list_featured_products,
    list_products,
    resolve_department_for_product,
)


class TestProductCatalog:
    def test_featured_products_expose_public_names(self):
        names = [product.display_name for product in list_featured_products()]
        assert names == [
            "Research Goblin",
            "Coding Goblin",
            "Finance Goblin",
            "Strategy Goblin",
            "Operations Goblin",
        ]

    def test_products_list_includes_general_fallback(self):
        products = list_products()
        assert any(product.product_id == "general" for product in products)
        assert any(product.display_name == "General Goblin" for product in products)

    def test_product_lookup_returns_internal_department(self):
        assert get_product_info("finance").department_id is DepartmentId.REASONING
        assert get_product_info("operations").department_id is DepartmentId.TOOL_USE
        assert get_product_info("research").department_id is DepartmentId.RESEARCH

    def test_invalid_lookup_returns_none(self):
        assert get_product_info("imaginary") is None

    def test_department_resolution_is_deterministic(self):
        assert resolve_department_for_product("finance") is DepartmentId.REASONING
        assert resolve_department_for_product("operations") is DepartmentId.TOOL_USE

    def test_invalid_department_resolution_raises(self):
        with pytest.raises(KeyError):
            resolve_department_for_product("imaginary")
