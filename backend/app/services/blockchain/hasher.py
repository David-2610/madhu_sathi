"""
Deterministic event hashing utility for Honey Chain traceability.

Computes a canonical SHA-256 hash of event data.
Guarantees identical hash generation across distributed environments.
"""

import hashlib
import json
from typing import Any, Dict, Optional


def compute_event_hash(
    event_type: str,
    entity_code: str,
    timestamp_iso: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Compute a deterministic SHA-256 hash over canonical event fields.

    Keys in metadata are sorted to avoid nondeterministic serialization.
    """
    payload = {
        "event_type": event_type,
        "entity_code": entity_code,
        "timestamp": timestamp_iso,
        "metadata": metadata or {},
    }
    canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
