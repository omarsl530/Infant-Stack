"""
Pytest configuration and fixtures.
"""

import pytest
from fastapi.testclient import TestClient

import sys
sys.path.insert(0, str(__file__).rsplit("/", 2)[0])

from services.api_gateway.main import app


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the API."""
    return TestClient(app)
