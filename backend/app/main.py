"""
FastAPI application entry point for Honey Chain backend.

Responsibilities:
- Create and configure the FastAPI app instance
- Register routers
- Configure structured logging
- Add global exception handlers
- Probe DB connectivity on startup (non-blocking warning if unavailable)
"""

import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes import auth as auth_router
from app.api.routes import beekeeper as beekeeper_router
from app.api.routes import buyer as buyer_router
from app.api.routes import health as health_router
from app.api.routes import iot as iot_router
from app.api.routes import kvic as kvic_router
from app.api.routes import marketplace as marketplace_router
from app.api.routes import trace as trace_router
from app.core.config import get_settings
from app.api.routes import bridge as bridge_router
from app.db import check_db_connection
from app.services.iot_bridge import run_iot_bridge


# ── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

settings = get_settings()


# ── Lifespan (startup / shutdown) ──────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:  # noqa: ARG001
    # ── startup ────────────────────────────────────────────────────────────
    logger.info(
        "Starting %s v%s [%s]",
        settings.APP_NAME,
        settings.APP_VERSION,
        settings.APP_ENV,
    )
    if check_db_connection():
        logger.info("Database connection: OK")
    else:
        logger.warning(
            "Database connection: FAILED — server will continue running "
            "but DB-dependent routes will not work until the database is reachable."
        )

    # ── IoT Bridge ─────────────────────────────────────────────────────────
    # Start background task that polls IoT Mock Server and forwards telemetry
    # to our own pipeline, establishing: IoT Server → Backend → Frontend flow.
    bridge_task = None
    if settings.IOT_BRIDGE_ENABLED:
        logger.info("IoT Bridge: Starting background polling task...")
        bridge_task = asyncio.create_task(run_iot_bridge())
    else:
        logger.info("IoT Bridge: Disabled (IOT_BRIDGE_ENABLED=False)")

    yield  # application runs here

    # ── shutdown ───────────────────────────────────────────────────────────
    if bridge_task and not bridge_task.done():
        bridge_task.cancel()
        logger.info("IoT Bridge: Stopped.")
    logger.info("Shutting down %s", settings.APP_NAME)


# ── OpenAPI Tags Metadata ──────────────────────────────────────────────────
TAGS_METADATA = [
    {
        "name": "Health",
        "description": "System liveness, readiness, and database probe endpoints.",
    },
    {
        "name": "Authentication",
        "description": "User registration, JWT token generation, password management, and role-based access control.",
    },
    {
        "name": "Beekeeper",
        "description": "Beekeeper profile, apiary and hive management, honey harvests, batch aggregation, packaging, and traceability milestones.",
    },
    {
        "name": "Traceability",
        "description": "Public, consumer-facing QR trace lookup and cryptographic event verification.",
    },
    {
        "name": "Marketplace",
        "description": "Public honey catalog browsing, product filtering, and seller attribution.",
    },
    {
        "name": "Buyer",
        "description": "Buyer shopping cart, atomic checkout, order history, and payment processing.",
    },
    {
        "name": "IoT Devices & Hive Health",
        "description": "Hardware device registration, authenticated sensor telemetry ingestion, anomaly detection, alert lifecycle, and AI explanations.",
    },
]


# ── App factory ────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Honey Chain — blockchain-based honey traceability and smart "
        "beekeeping platform. Phase 8: Hardened IoT authentication, telemetry idempotency, "
        "production-safe health engine, strict alert lifecycle, RBAC enforcement, and OpenAPI contract."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    openapi_tags=TAGS_METADATA,
    lifespan=lifespan,
)


# ── Global exception handler ───────────────────────────────────────────────
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again later."},
    )


# ── Routers ────────────────────────────────────────────────────────────────
from app.api.routes import dev as dev_router

app.include_router(health_router.router)
app.include_router(auth_router.router)
app.include_router(beekeeper_router.router)
app.include_router(trace_router.router)
app.include_router(marketplace_router.router)
app.include_router(buyer_router.router)
app.include_router(iot_router.router)
app.include_router(kvic_router.router)
app.include_router(dev_router.router)
app.include_router(bridge_router.router)

