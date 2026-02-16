from sqlalchemy import Column, Integer, String, Boolean, Index, Text
from sqlalchemy.orm import relationship

from .base import Base
from .mixins import TimestampMixin


class Network(Base, TimestampMixin):
    __tablename__ = "networks"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    name = Column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )
    display_name = Column(
        String(100),
        nullable=False,
    )
    chain_id = Column(
        Integer,
        unique=True,
        nullable=False,
        index=True,
    )
    rpc_url = Column(
        String(255),
        nullable=False,
    )
    weth_address = Column(
        String(42),
        nullable=False,
    )
    multicall3_address = Column(
        String(42),
        nullable=False,
    ) 
    native_currency_symbol = Column(
        String(10),
        nullable=False,
        default="ETH",
    )
    native_currency_decimals = Column(
        Integer,
        nullable=False,
        default=18,
    )
    block_explorer_url = Column(
        String(255),
        nullable=True,
    ) 
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )

    user_settings = relationship(
        "UserNetworkSettings", back_populates="network", cascade="all, delete-orphan"
    )
    wallets = relationship(
        "Wallet", back_populates="network", cascade="all, delete-orphan"
    )
    tokens = relationship(
        "Token", back_populates="network", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("idx_network_active", "is_active"),)

    def __repr__(self) -> str:
        return (
            f"<Network(id={self.id}, name={self.name}, "
            f"chain_id={self.chain_id}, is_active={self.is_active})>"
        )

    @property
    def explorer_address_url(self) -> str:
        if self.block_explorer_url:
            return f"{self.block_explorer_url}/address/"
        return ""

    @property
    def explorer_tx_url(self) -> str:
        if self.block_explorer_url:
            return f"{self.block_explorer_url}/tx/"
        return ""
