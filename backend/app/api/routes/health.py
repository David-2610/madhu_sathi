"""
Health check endpoint.

GET /health  →  {"status": "ok"}

This endpoint is intentionally lightweight — it does not hit the database.
A separate readiness check (with DB ping) can be added in Phase 2.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get(
    "/health",
    summary="Health check",
    response_description="Returns service status",
    tags=["Health"],
)
async def health_check() -> dict[str, str]:
    """
    Simple liveness probe.

    Returns **{"status": "ok"}** when the application process is running.
    """
    return {"status": "ok"}
