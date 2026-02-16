from cryptography.fernet import Fernet
from mnemonic import Mnemonic
from eth_account import Account
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from db.repositories.wallet import WalletRepository
from services.dto import WalletData

class WalletService:
    _cipher: Fernet | None = None
    
    @classmethod
    def get_cipher(cls) -> Fernet:
        if cls._cipher is None:
            encryption_key = settings.WALLET_ENCRYPTION_KEY
            if not encryption_key:
                raise ValueError("WALLET_ENCRYPTION_KEY not set")
            cls._cipher = Fernet(encryption_key.encode())
        return cls._cipher
    
    @staticmethod
    def encrypt_private_key(private_key: str) -> bytes:
        clean_key = private_key.replace("0x", "").strip()
        cipher = WalletService.get_cipher()
        return cipher.encrypt(clean_key.encode())
    
    @staticmethod
    def generate_mnemonic() -> str:
        result = Mnemonic("english")
        return result.generate()

    @staticmethod
    def derive_private_key(mnemonic: str) -> str:
        Account.enable_unaudited_hdwallet_features()

        account = Account.from_mnemonic(mnemonic)

        return account.key.hex()

    @staticmethod
    def get_address(private_key: str) -> str:
        if not private_key.startswith("0x"):
            private_key = f"0x{private_key}"

        account = Account.from_key(private_key)
        return account.address
    
    @staticmethod
    def validate_private_key(private_key: str) -> bool:
        try:
            if not private_key.startswith("0x"):
                private_key = f"0x{private_key}"
            Account.from_key(private_key)
            return True
        except Exception:
            return False

    @staticmethod
    async def create_wallet() -> WalletData:
        mnemonic = WalletService.generate_mnemonic()
        
        private_key = WalletService.derive_private_key(mnemonic)
        address = WalletService.get_address(private_key)

        encrypted_key = WalletService.encrypt_private_key(private_key)

        return WalletData(mnemonic=mnemonic, private_key=encrypted_key, address=address)
    
    @staticmethod
    async def import_wallet(session: AsyncSession, private_key: str, chain_id: int) -> WalletData:
        wallet_repo = WalletRepository(session)
        
        if not WalletService.validate_private_key(private_key):
            raise ValueError("Invalid private key")
        
        address = WalletService.get_address(private_key)

        existing = await wallet_repo.get_by_address(address, chain_id)
        if existing:
            raise ValueError(f"Wallet with address {address} already exists")
        
        encrypted_key = WalletService.encrypt_private_key(private_key)
        
        return WalletData(private_key=encrypted_key, address=address)
