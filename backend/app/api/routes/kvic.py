"""
API routes for KVIC Administrators.

Provides aggregate data, alerts, and system-wide overviews for KVIC dashboard.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect, status
from jose import JWTError
from sqlalchemy import func, distinct, desc, case
from sqlalchemy.orm import Session

from app.core.dependencies import require_role
from app.core.security import decode_access_token
from app.crud.user import get_user_by_id
from app.core.websockets import manager
from app.services.ai_cache import AI_CACHE
from app.db import get_db
from app.models.apiary import Apiary
from app.models.hive import Hive
from app.models.hive_alert import HiveAlert, AlertStatus, AlertSeverity
from app.models.hive_telemetry import HiveTelemetry
from app.models.user import User, UserRole

router = APIRouter(prefix="/kvic", tags=["KVIC Dashboard"])

# Require KVIC_ADMIN role
kvic_admin_only = Depends(require_role(UserRole.KVIC_ADMIN))


@router.get("/overview", summary="Get KVIC system overview")
def get_kvic_overview(
    db: Session = Depends(get_db),
    user: User = kvic_admin_only,
) -> Dict[str, Any]:
    """Retrieve aggregate statistics for the KVIC monitoring dashboard."""
    
    total_hives = db.query(Hive).count()
    
    # Averages from telemetry
    avg_metrics = db.query(
        func.avg(HiveTelemetry.temperature_c).label("avg_temp"),
        func.avg(HiveTelemetry.humidity_percent).label("avg_hum")
    ).first()
    
    avg_temperature = float(avg_metrics.avg_temp) if avg_metrics and avg_metrics.avg_temp else 0.0
    avg_humidity = float(avg_metrics.avg_hum) if avg_metrics and avg_metrics.avg_hum else 0.0

    # Alerts analytics
    active_alerts = db.query(func.count(HiveAlert.id)).filter(HiveAlert.status == AlertStatus.OPEN).scalar() or 0
    critical_alerts = db.query(func.count(HiveAlert.id)).filter(
        HiveAlert.status == AlertStatus.OPEN,
        HiveAlert.severity == AlertSeverity.CRITICAL
    ).scalar() or 0
    
    # Risk Hives (Hives with open alerts)
    risk_hives_query = (
        db.query(
            HiveAlert.hive_id,
            func.max(
                case(
                    (HiveAlert.severity == AlertSeverity.CRITICAL, 3),
                    (HiveAlert.severity == AlertSeverity.HIGH, 2),
                    (HiveAlert.severity == AlertSeverity.MEDIUM, 2),
                    (HiveAlert.severity == AlertSeverity.LOW, 2),
                    else_=1
                )
            ).label("risk_score")
        )
        .filter(HiveAlert.status == AlertStatus.OPEN)
        .group_by(HiveAlert.hive_id)
        .all()
    )
    
    risk_hives = []
    for r in risk_hives_query:
        risk_level = "HIGH" if r.risk_score == 3 else "MEDIUM"
        risk_hives.append({"hive_id": r.hive_id, "risk": risk_level})

    # Hive distribution by status
    status_distribution_query = db.query(Hive.status, func.count(Hive.id)).group_by(Hive.status).all()
    hive_distribution_by_status = {
        status.value if hasattr(status, "value") else str(status): count 
        for status, count in status_distribution_query
    }

    return {
        "total_hives": total_hives,
        "active_alerts": active_alerts,
        "critical_alerts": critical_alerts,
        "avg_temperature": round(avg_temperature, 2),
        "avg_humidity": round(avg_humidity, 2),
        "risk_hives": risk_hives,
        "hive_distribution_by_status": hive_distribution_by_status
    }


@router.get("/hives", summary="List all hives with advanced filtering")
def get_kvic_hives(
    location: Optional[str] = Query(None, description="Filter by location name"),
    beekeeper_id: Optional[int] = Query(None, description="Filter by beekeeper ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    user: User = kvic_admin_only,
) -> List[Dict[str, Any]]:
    """Return a paginated list of all hives with risk classifications and filters."""
    
    # We want to calculate the maximum severity of open alerts per hive to determine risk
    risk_score_case = case(
        (HiveAlert.severity == AlertSeverity.CRITICAL, 3),
        (HiveAlert.severity == AlertSeverity.HIGH, 2),
        (HiveAlert.severity == AlertSeverity.MEDIUM, 2),
        (HiveAlert.severity == AlertSeverity.LOW, 2),
        else_=1
    )
    
    query = (
        db.query(
            Hive.id,
            Apiary.beekeeper_id,
            Apiary.location_name,
            func.count(HiveAlert.id).label("alert_count"),
            func.max(risk_score_case).label("max_risk_score")
        )
        .join(Apiary, Hive.apiary_id == Apiary.id)
        .outerjoin(
            HiveAlert, 
            (HiveAlert.hive_id == Hive.id) & (HiveAlert.status == AlertStatus.OPEN)
        )
    )
    
    # Apply optional filters
    if location:
        query = query.filter(Apiary.location_name.ilike(f"%{location}%"))
    if beekeeper_id is not None:
        query = query.filter(Apiary.beekeeper_id == beekeeper_id)
        
    results = (
        query
        .group_by(Hive.id, Apiary.beekeeper_id, Apiary.location_name)
        .order_by(desc("max_risk_score"), desc("alert_count"))
        .offset(skip)
        .limit(limit)
        .all()
    )
    
    response = []
    for r in results:
        # Determine risk classification
        risk_class = "LOW"
        if r.max_risk_score == 3:
            risk_class = "HIGH"
        elif r.max_risk_score == 2:
            risk_class = "MEDIUM"
            
        # Fetch AI summary from cache if available
        ai_summary = None
        hive_cache = AI_CACHE.get(r.id)
        if hive_cache and hive_cache.get("result"):
            ai_summary = hive_cache["result"]

        response.append({
            "hive_id": r.id,
            "beekeeper_id": r.beekeeper_id,
            "location": r.location_name,
            "active_alerts_count": r.alert_count,
            "risk_classification": risk_class,
            "ai_summary": ai_summary,
        })
        
    return response


@router.get("/alerts", summary="List all active alerts with filtering")
def get_kvic_alerts(
    severity: Optional[str] = Query(None, description="Filter by severity (e.g., CRITICAL, HIGH)"),
    location: Optional[str] = Query(None, description="Filter by location name"),
    beekeeper_id: Optional[int] = Query(None, description="Filter by beekeeper ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    user: User = kvic_admin_only,
) -> List[Dict[str, Any]]:
    """Return active alerts sorted by severity with optional filters."""
    
    query = (
        db.query(
            HiveAlert,
            Hive.id.label("hive_id_val"),
            Apiary.beekeeper_id,
            Apiary.location_name
        )
        .join(Hive, HiveAlert.hive_id == Hive.id)
        .join(Apiary, Hive.apiary_id == Apiary.id)
        .filter(HiveAlert.status == AlertStatus.OPEN)
    )
    
    if severity:
        # Match enum or fallback to string cast
        try:
            sev_enum = AlertSeverity[severity.upper()]
            query = query.filter(HiveAlert.severity == sev_enum)
        except KeyError:
            query = query.filter(HiveAlert.severity.cast(str) == severity.upper())
            
    if location:
        query = query.filter(Apiary.location_name.ilike(f"%{location}%"))
    if beekeeper_id is not None:
        query = query.filter(Apiary.beekeeper_id == beekeeper_id)
        
    severity_order = case(
        (HiveAlert.severity == AlertSeverity.CRITICAL, 1),
        (HiveAlert.severity == AlertSeverity.HIGH, 2),
        (HiveAlert.severity == AlertSeverity.MEDIUM, 3),
        (HiveAlert.severity == AlertSeverity.LOW, 4),
        else_=5
    )
    
    results = (
        query
        .order_by(severity_order, desc(HiveAlert.created_at))
        .offset(skip)
        .limit(limit)
        .all()
    )
    
    return [
        {
            "hive_id": r.hive_id_val,
            "type": r.HiveAlert.alert_type,
            "severity": r.HiveAlert.severity.value if hasattr(r.HiveAlert.severity, "value") else str(r.HiveAlert.severity),
            "message": r.HiveAlert.message,
            "created_at": r.HiveAlert.created_at.isoformat() if r.HiveAlert.created_at else None,
            "location": r.location_name,
            "beekeeper_id": r.beekeeper_id
        } for r in results
    ]


@router.websocket("/ws")
async def websocket_kvic(websocket: WebSocket, token: str, db: Session = Depends(get_db)):
    """Real-time WebSocket endpoint for KVIC dashboard."""
    
    # 1. Authenticate token
    try:
        user_id = decode_access_token(token)
        user = get_user_by_id(db, user_id)
        if not user or user.role != UserRole.KVIC_ADMIN.value:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
    except JWTError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # 2. Accept connection
    await manager.connect_kvic(websocket)
    try:
        # 3. Send initial state snapshot
        # Note: get_kvic_overview and get_kvic_hives are sync functions, 
        # but since we are just doing it once on connect, it's acceptable.
        overview = get_kvic_overview(db=db, user=user)
        hives = get_kvic_hives(location=None, beekeeper_id=None, skip=0, limit=1000, db=db, user=user)
        
        await websocket.send_json({
            "type": "initial-data",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "overview": overview,
                "hives": hives
            }
        })
        
        # 4. Keep alive and wait for client disconnect
        while True:
            await websocket.receive_text()
            
    except WebSocketDisconnect:
        manager.disconnect_kvic(websocket)

