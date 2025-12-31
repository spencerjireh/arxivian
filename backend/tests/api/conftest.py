"""API test configuration - applies api marker to all tests in this directory."""

import pytest


def pytest_collection_modifyitems(items):
    """Apply api marker to all tests in this directory."""
    for item in items:
        if "/api/" in str(item.fspath):
            item.add_marker(pytest.mark.api)
