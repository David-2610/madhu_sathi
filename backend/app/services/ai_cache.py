import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from fastapi import BackgroundTasks

from app.services.ai import get_ai_provider
from app.core.websockets import manager

# Per hive: { last_run: datetime, is_running: bool, result: Any }
AI_CACHE: Dict[int, Dict[str, Any]] = {}

def trigger_ai_analysis(
    hive_id: int, 
    hive_code: str, 
    metrics: Dict[str, Any], 
    anomalies: List[str],
    is_simulated: bool = False,
    background_tasks: Optional[BackgroundTasks] = None
):
    """
    Triggers AI analysis adhering to strict rules:
    - cooldown = 10s
    - skip if already running
    - skip useless simulation (no alerts/anomalies)
    """
    
    # Check rule: skip useless simulation (no alerts)
    if is_simulated and not anomalies:
        return

    # Check rule: skip if already running or within cooldown
    now = datetime.now(timezone.utc)
    hive_cache = AI_CACHE.get(hive_id, {"last_run": None, "is_running": False, "result": None})
    
    if hive_cache["is_running"]:
        return
        
    if hive_cache["last_run"] is not None:
        elapsed = (now - hive_cache["last_run"]).total_seconds()
        if elapsed < 10.0:
            return

    # Set lock
    hive_cache["is_running"] = True
    hive_cache["last_run"] = now
    AI_CACHE[hive_id] = hive_cache

    if background_tasks:
        background_tasks.add_task(_run_ai_and_broadcast, hive_id, hive_code, metrics, anomalies)
    else:
        # If no background tasks provided (e.g. called from a sync context without one), 
        # use asyncio.create_task to fire and forget
        loop = asyncio.get_running_loop()
        loop.create_task(_run_ai_and_broadcast(hive_id, hive_code, metrics, anomalies))

async def _run_ai_and_broadcast(hive_id: int, hive_code: str, metrics: Dict[str, Any], anomalies: List[str]):
    try:
        # Run AI synchronously in a thread pool to avoid blocking the async loop if the provider is sync
        ai_provider = get_ai_provider()
        
        loop = asyncio.get_running_loop()
        explanation = await loop.run_in_executor(
            None, 
            ai_provider.generate_explanation,
            hive_id,
            hive_code,
            metrics,
            anomalies,
            None
        )
        
        # Format the result payload
        result_payload = {
            "condition_summary": explanation.condition_summary,
            "explanation": explanation.explanation,
            "recommended_steps": explanation.recommended_steps,
            "is_mock": explanation.is_mock,
            "provider": explanation.provider
        }
        
        # Save to cache
        AI_CACHE[hive_id]["result"] = result_payload
        
        # Broadcast the AI analysis
        await manager.broadcast_kvic("ai-analysis", hive_id, result_payload)
        
    finally:
        # Release lock
        if hive_id in AI_CACHE:
            AI_CACHE[hive_id]["is_running"] = False
