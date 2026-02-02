"""
Tests for API Gateway health endpoints.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(async_client: AsyncClient) -> None:
    """Test the root health check endpoint."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_api_health_check(async_client: AsyncClient) -> None:
    """Test the API v1 health check endpoint."""
    response = await async_client.get("/api/v1/health/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "api-gateway"


@pytest.mark.asyncio
async def test_readiness_check(async_client: AsyncClient) -> None:
    """Test the readiness endpoint returns ready status."""
    response = await async_client.get("/api/v1/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
