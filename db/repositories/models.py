from dataclasses import dataclass

from enums.chain import ChainStatus


@dataclass
class ChainWithStatus:
    chain_id: int
    evm_chain_id: int
    is_active: bool

    settings_id: int | None
    is_enabled: bool | None

    status: ChainStatus
