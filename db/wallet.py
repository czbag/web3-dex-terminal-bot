from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    ForeignKey,
    Index,
    LargeBinary,
    Text,
    CheckConstraint,
)
from sqlalchemy.orm import relationship
from cryptography.fernet import Fernet
import os

from .base import Base
from .mixins import TimestampMixin, SoftDeleteMixin


class Wallet(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "wallets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    chain_id = Column(
        Integer,
        ForeignKey("chains.id", ondelete="CASCADE"),
        nullable=False,
    )
    address = Column(
        String(42), nullable=False
    )
    encrypted_private_key = Column(
        LargeBinary, nullable=True
    )
    name = Column(
        String(10), nullable=True
    )
    is_active = Column(
        Boolean, default=True, nullable=False
    )

    user = relationship("User", back_populates="wallets")
    chain = relationship("Chain", back_populates="wallets")

    def __repr__(self) -> str:
        return (
            f"<Wallet(id={self.id}, user_id={self.user_id}, "
            f"chain_id={self.chain_id}, address={self.address[:10]}..., "
            f"is_active={self.is_active})>"
        )

    def decrypt_private_key(self, cipher: Fernet) -> str:
        if not self.encrypted_private_key:
            raise ValueError("No encrypted private key found")

        decrypted = cipher.decrypt(self.encrypted_private_key).decode()

        if not decrypted.startswith("0x"):
            decrypted = f"0x{decrypted}"

        return decrypted
