"""
Traceability Event CRUD operations.

Handles cryptographic hashing and anchoring into the blockchain provider abstraction.
"""

from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.traceability_event import TraceEventType, TraceabilityEvent
from app.services.blockchain import BlockchainProvider, compute_event_hash, get_blockchain_provider


def record_event(
    db: Session,
    event_type: TraceEventType,
    description: str,
    entity_code: str,
    batch_id: Optional[int] = None,
    product_id: Optional[int] = None,
    location: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    provider: Optional[BlockchainProvider] = None,
) -> TraceabilityEvent:
    """
    Record an immutable traceability event.

    - Computes a deterministic SHA-256 hash of the canonical payload.
    - Anchors the hash via the blockchain provider.
    - Saves the real transaction hash only if returned by a live on-chain provider.
    - Never fabricates a transaction hash when using a mock provider.
    """
    if provider is None:
        provider = get_blockchain_provider()

    event_time = datetime.now(timezone.utc)
    timestamp_iso = event_time.isoformat()

    event_hash = compute_event_hash(
        event_type=event_type.value,
        entity_code=entity_code,
        timestamp_iso=timestamp_iso,
        metadata=metadata,
    )

    receipt = provider.record_event_proof(event_hash, metadata)

    # Real blockchain transaction hash only when confirmed on a real network
    real_tx_hash = receipt.tx_hash if not receipt.is_mock and receipt.is_success else None
    is_on_chain = bool(not receipt.is_mock and receipt.is_success and receipt.tx_hash)

    payload_json = json.dumps(metadata) if metadata else None

    event = TraceabilityEvent(
        event_type=event_type,
        batch_id=batch_id,
        product_id=product_id,
        event_date=event_time,
        description=description,
        location=location,
        metadata_payload=payload_json,
        event_hash=event_hash,
        blockchain_tx_hash=real_tx_hash,
        is_on_chain=is_on_chain,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def list_events_for_product(db: Session, product_id: int) -> List[TraceabilityEvent]:
    """Return all traceability events recorded directly for *product_id*."""
    return (
        db.query(TraceabilityEvent)
        .filter(TraceabilityEvent.product_id == product_id)
        .order_by(TraceabilityEvent.event_date.asc())
        .all()
    )


def list_events_for_batch(db: Session, batch_id: int) -> List[TraceabilityEvent]:
    """Return all traceability events recorded for *batch_id*."""
    return (
        db.query(TraceabilityEvent)
        .filter(TraceabilityEvent.batch_id == batch_id)
        .order_by(TraceabilityEvent.event_date.asc())
        .all()
    )
