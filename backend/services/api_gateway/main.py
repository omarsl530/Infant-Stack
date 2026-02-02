"""
API Gateway - Main entry point for all REST API requests.

Provides routing, authentication, and request handling for the Infant-Stack system.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from fastapi.responses import JSONResponse

import sys
sys.path.insert(0, str(__file__).rsplit("/", 3)[0])

from shared_libraries.config import get_settings
from shared_libraries.logging import get_logger, setup_logging
from shared_libraries.database import init_db, close_db
from services.api_gateway.routes import (
    alerts, audit, cameras, gates, health, infants, mothers, pairings, rtls, users, websocket, zones, config, roles, stats
)
from services.alert_escalation import start_alert_escalation_worker
import asyncio

# Load settings
settings = get_settings()

# Setup logging
setup_logging(
    log_level="DEBUG" if settings.debug else "INFO",
    service_name="api-gateway"
)
logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Startup and shutdown events for the FastAPI application."""
    # Initialize database
    await init_db()
    
    # Start background workers
    # asyncio.create_task(start_alert_escalation_worker())
    
    logger.info("api_gateway_started", host=settings.api_host, port=settings.api_port)
    yield
    
    # Shutdown
    await close_db()
    logger.info("api_gateway_shutdown")

app = FastAPI(
    title="Infant-Stack API Gateway",
    description="Backend API for the Infant-Stack hospital infant tracking system.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=f"{settings.api_prefix}/docs",
    openapi_url=f"{settings.api_prefix}/openapi.json",
)

# Instrument Prometheus
Instrumentator().instrument(app).expose(app)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Production should be more restrictive
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("unhandled_exception", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error_type": type(exc).__name__},
    )

# Health checks
@app.get("/health", tags=["System"])
async def root_health():
    return {"status": "ok"}

# Routes
app.include_router(health.router, prefix=f"{settings.api_prefix}/health", tags=["System"])
app.include_router(infants.router, prefix=f"{settings.api_prefix}/infants", tags=["Patients"])
app.include_router(mothers.router, prefix=f"{settings.api_prefix}/mothers", tags=["Patients"])
app.include_router(pairings.router, prefix=f"{settings.api_prefix}/pairings", tags=["Patients"])
app.include_router(alerts.router, prefix=f"{settings.api_prefix}/alerts", tags=["Security"])
app.include_router(rtls.router, prefix=f"{settings.api_prefix}/rtls", tags=["RTLS"])
app.include_router(gates.router, prefix=f"{settings.api_prefix}/gates", tags=["Security"])
app.include_router(zones.router, prefix=f"{settings.api_prefix}", tags=["Security"])
app.include_router(cameras.router, prefix=f"{settings.api_prefix}/cameras", tags=["Security"])
app.include_router(audit.router, prefix=f"{settings.api_prefix}/audit", tags=["Security"])

# Admin Dashboard routes
app.include_router(users.router, prefix=f"{settings.api_prefix}/users", tags=["Users"])
app.include_router(roles.router, prefix=f"{settings.api_prefix}/roles", tags=["Roles"])
app.include_router(stats.router, prefix=f"{settings.api_prefix}/stats", tags=["Statistics"])
app.include_router(config.router, prefix=f"{settings.api_prefix}", tags=["Configuration"])

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
