"""
Abstract base class and data structures for Honey Chain blockchain integration.

SECURITY INVARIANTS:
- No private keys are exposed to client devices or web frontends.
- No PII (names, emails, phone numbers) or large documents are ever written to chain.
- Only SHA-256 cryptographic hashes / proofs of traceability events are submitted.
- Blockchain transaction hashes are recorded ONLY when a verified on-chain transaction succeeds.
- Fake / fabricated transaction hashes must NEVER be generated.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class BlockchainReceipt(BaseModel):
    """Result of attempting to anchor an event hash into a blockchain provider."""

    is_success: bool = Field(..., description="Whether anchoring was accepted")
    tx_hash: Optional[str] = Field(
        None,
        description="Real on-chain transaction hash. Must be None if mock or unconfirmed.",
    )
    is_mock: bool = Field(
        True,
        description="Explicit flag declaring if the receipt is from a local mock provider",
    )
    network: str = Field(..., description="Target network name, e.g., 'MOCK_LOCAL' or 'POLYGON_MAINNET'")
    block_number: Optional[int] = Field(None, description="Block number if on-chain")
    recorded_hash: str = Field(..., description="The SHA-256 event hash anchored")
    timestamp: datetime = Field(..., description="Timestamp of recording")


class BlockchainProvider(ABC):
    """Abstract interface for blockchain notarization and verification."""

    @abstractmethod
    def record_event_proof(
        self,
        event_hash: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> BlockchainReceipt:
        """
        Record a cryptographic event hash into the blockchain ledger.

        Must NEVER fabricate a transaction hash if mock or offline.
        """
        pass

    @abstractmethod
    def verify_event_proof(
        self,
        event_hash: str,
        tx_hash: Optional[str] = None,
    ) -> bool:
        """
        Verify whether an event hash exists in the ledger.
        """
        pass

    def record_event_hash(
        self,
        event_hash: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> BlockchainReceipt:
        """Record an event hash proof (alias for record_event_proof)."""
        return self.record_event_proof(event_hash, metadata)

    def verify_event(
        self,
        event_hash: str,
        tx_hash: Optional[str] = None,
    ) -> bool:
        """Verify presence of an event proof (alias for verify_event_proof)."""
        return self.verify_event_proof(event_hash, tx_hash)

