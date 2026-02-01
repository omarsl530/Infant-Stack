"""Health check endpoints."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check() -> dict:
    """Basic health check endpoint."""
    return {"status": "healthy", "service": "api-gateway"}


@router.get("/ready")
async def readiness_check() -> dict:
    """Readiness check for Kubernetes."""
    # TODO: Add database connectivity check
    return {"status": "ready"}
