"""
API Gateway - Main entry point for all REST API requests.

Provides routing, authentication, and request handling for the Infant-Stack system.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import sys
sys.path.insert(0, str(__file__).rsplit("/", 3)[0])

from shared_libraries.config import get_settings
from shared_libraries.logging import get_logger, setup_logging
from shared_libraries.database import init_db, close_db
from services.api_gateway.routes import (
    alerts, audit, cameras, gates, health, infants, mothers, pairings, rtls, users, websocket, zones
)

# Initialize
setup_logging("api-gateway", "INFO")
logger = get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    logger.info("api_gateway_starting", environment=settings.environment)
    # Initialize database tables
    await init_db()
    logger.info("database_initialized")
    yield
    # Cleanup
    await close_db()
    logger.info("api_gateway_stopping")


# Create FastAPI application
app = FastAPI(
    title="Infant-Stack API",
    description="API for hospital infant security ecosystem",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:3002"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Audit Logging Middleware
from services.api_gateway.middleware.audit import AuditMiddleware
app.add_middleware(AuditMiddleware)


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    logger.error("unhandled_exception", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(infants.router, prefix=f"{settings.api_prefix}/infants", tags=["Infants"])
app.include_router(mothers.router, prefix=f"{settings.api_prefix}/mothers", tags=["Mothers"])
app.include_router(pairings.router, prefix=f"{settings.api_prefix}/pairings", tags=["Pairings"])
app.include_router(alerts.router, prefix=f"{settings.api_prefix}/alerts", tags=["Alerts"])
app.include_router(audit.router, prefix=f"{settings.api_prefix}/audit-logs", tags=["Audit Logs"])

# Security Dashboard routes
app.include_router(gates.router, prefix=f"{settings.api_prefix}/gates", tags=["Gates"])
app.include_router(rtls.router, prefix=f"{settings.api_prefix}/rtls", tags=["RTLS"])
app.include_router(cameras.router, prefix=f"{settings.api_prefix}/cameras", tags=["Cameras"])
app.include_router(zones.router, prefix=f"{settings.api_prefix}", tags=["Zones & Floorplans"])

# Admin Dashboard routes
app.include_router(users.router, prefix=f"{settings.api_prefix}/users", tags=["Users"])

# WebSocket streaming
app.include_router(websocket.router, prefix="/ws", tags=["WebSocket"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    )
