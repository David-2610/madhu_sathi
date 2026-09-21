"""
Blockchain provider factory for Honey Chain.
"""

from functools import lru_cache

from app.core.config import get_settings
from app.services.blockchain.base import BlockchainProvider
from app.services.blockchain.evm_provider import EVMBlockchainProvider
from app.services.blockchain.mock_provider import MockBlockchainProvider


@lru_cache
def get_blockchain_provider() -> BlockchainProvider:
    """
    Resolve and return the configured blockchain provider instance.

    Defaults safely to MockBlockchainProvider if not in EVM mode or if credentials are unset.
    """
    settings = get_settings()

    if (
        settings.BLOCKCHAIN_PROVIDER.lower() == "evm"
        and settings.BLOCKCHAIN_RPC_URL
    ):
        return EVMBlockchainProvider(
            rpc_url=settings.BLOCKCHAIN_RPC_URL,
            contract_address=settings.BLOCKCHAIN_CONTRACT_ADDRESS,
        )

    return MockBlockchainProvider()
