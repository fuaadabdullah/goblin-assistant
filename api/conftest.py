import pytest
from fastapi.testclient import TestClient
import sys
import os

# Ensure the package root (apps/goblin-assistant) is on sys.path so relative imports work
pkg_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, pkg_root)


@pytest.fixture
def client():
    # Import using package name so relative imports resolve inside the 'api' package
    from importlib import import_module

    mod = import_module("api.main")
    app = getattr(mod, "app")

    with TestClient(app) as client:
        yield client
