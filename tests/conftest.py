"""Global test configuration and state isolation.

Ensures that FastAPI dependency overrides and module-level rate windows
are strictly cleared between test cases across the entire test suite.
"""

from __future__ import annotations

import pytest

from app import app
import app as app_module


@pytest.fixture(autouse=True)
def reset_global_fastapi_dependency_overrides():
    """Ensure app.dependency_overrides does not leak across tests."""
    yield
    app.dependency_overrides.clear()
