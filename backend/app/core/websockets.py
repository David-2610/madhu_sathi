import asyncio
from typing import Dict, List, Any
from fastapi import WebSocket
from datetime import datetime, timezone

class ConnectionManager:
    def __init__(self):
        # Store connections. We can keep it simple: just a list for KVIC.
        self.active_kvic_connections: List[WebSocket] = []

    async def connect_kvic(self, websocket: WebSocket):
        await websocket.accept()
        self.active_kvic_connections.append(websocket)

    def disconnect_kvic(self, websocket: WebSocket):
        if websocket in self.active_kvic_connections:
            self.active_kvic_connections.remove(websocket)

    async def broadcast_kvic(self, event_type: str, hive_id: int, payload: Any):
        """
        Broadcasts an event strictly adhering to the mandated format:
        {
          "type": event_type,
          "hive_id": hive_id,
          "timestamp": isoformat(),
          "payload": payload
        }
        """
        event = {
            "type": event_type,
            "hive_id": hive_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": payload
        }
        
        # Avoid concurrent iteration issues by iterating over a copy
        for connection in list(self.active_kvic_connections):
            try:
                await connection.send_json(event)
            except Exception:
                # Disconnection handled in main websocket loop
                pass

# Singleton instance
manager = ConnectionManager()
