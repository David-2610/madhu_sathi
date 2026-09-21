"""
Mock blockchain provider for development and testing environments.

RULES:
- Explicitly sets is_mock = True and network = 'MOCK_LOCAL'.
- NEVER generates fake transaction hashes (tx_hash is strictly None).
- Keeps an in-memory ledger of hashes for local verification during unit tests.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional, Set

from app.services.blockchain.base import BlockchainProvider, BlockchainReceipt


class MockBlockchainProvider(BlockchainProvider):
    """Local, in-memory mock blockchain provider for testing and development."""

    def __init__(self) -> None:
        self._recorded_hashes: Set[str] = set()

    def record_event_proof(
        self,
        event_hash: str,
        metadata: Optional[Dict[str, Any]] = None,  # noqa: ARG002
    ) -> BlockchainReceipt:
        """
        Record the hash into the local mock store.

        Crucially, tx_hash is None because no real on-chain transaction occurred.
        """
        self._recorded_hashes.add(event_hash)
        return BlockchainReceipt(
            is_success=True,
            tx_hash=None,  # NEVER fabricate fake transaction hashes
            is_mock=True,
            network="MOCK_LOCAL",
            block_number=None,
            recorded_hash=event_hash,
            timestamp=datetime.now(timezone.utc),
        )

    def verify_event_proof(
        self,
        event_hash: str,
        tx_hash: Optional[str] = None,  # noqa: ARG002
    ) -> bool:
        """Verify presence in the local mock ledger."""
        return event_hash in self._recorded_hashes
