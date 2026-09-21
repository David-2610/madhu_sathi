"""
EVM / Polygon blockchain provider integration.

Stub implementation designed to connect to Polygon or Ethereum via JSON-RPC.
Isolates web3 / smart contract interactions from core business logic.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.services.blockchain.base import BlockchainProvider, BlockchainReceipt


class EVMBlockchainProvider(BlockchainProvider):
    """EVM-compatible blockchain provider (e.g. Polygon PoS / Amoy testnet)."""

    def __init__(
        self,
        rpc_url: str,
        contract_address: Optional[str] = None,
        network: str = "POLYGON_AMOY",
    ) -> None:
        self.rpc_url = rpc_url
        self.contract_address = contract_address
        self.network = network

    def record_event_proof(
        self,
        event_hash: str,
        metadata: Optional[Dict[str, Any]] = None,  # noqa: ARG002
    ) -> BlockchainReceipt:
        """
        Broadcast proof to EVM contract.

        In production, executes a signed transaction sending event_hash to the registry contract.
        If credentials or connectivity fail, returns is_success=False without fabricating a tx_hash.
        """
        # Placeholder for full Web3.py transaction pipeline in future on-chain deployment phase
        return BlockchainReceipt(
            is_success=False,
            tx_hash=None,
            is_mock=False,
            network=self.network,
            block_number=None,
            recorded_hash=event_hash,
            timestamp=datetime.now(timezone.utc),
        )

    def verify_event_proof(
        self,
        event_hash: str,
        tx_hash: Optional[str] = None,
    ) -> bool:
        """Query contract state or receipt log to verify event hash."""
        return False
