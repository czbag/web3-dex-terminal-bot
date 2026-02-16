from dataclasses import dataclass


@dataclass
class WalletData:
    private_key: bytes
    address: str
    mnemonic: str | None = None
