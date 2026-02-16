from sqlalchemy import Column, Integer, String, Boolean, Index, Text
from sqlalchemy.orm import relationship

from .base import Base
from .mixins import TimestampMixin


class Chain(Base, TimestampMixin):
    __tablename__ = "chains"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    chain_id = Column(
        Integer,
        unique=True,
        nullable=False,
        index=True,
    )
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )

    user_settings = relationship(
        "UserChainSettings", back_populates="chain", cascade="all, delete-orphan"
    )
    wallets = relationship(
        "Wallet", back_populates="chain", cascade="all, delete-orphan"
    )
    tokens = relationship(
        "Token", back_populates="chain", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("idx_chain_active", "is_active"),)

    def __repr__(self) -> str:
        return (
            f"<Chain(id={self.id}, chain_id={self.chain_id}, is_active={self.is_active})>"
        )
