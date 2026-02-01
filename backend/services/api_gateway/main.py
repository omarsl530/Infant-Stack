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
    alerts, audit, cameras, gates, health, infants, mothers, pairings, rtls, users, websocket, zones, config, roles
)
from services.alert_escalation import start_alert_escalation_worker
import asyncio

# ...

# Admin Dashboard routes
app.include_router(users.router, prefix=f"{settings.api_prefix}/users", tags=["Users"])
app.include_router(roles.router, prefix=f"{settings.api_prefix}/roles", tags=["Roles"])
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
