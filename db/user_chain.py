from decimal import Decimal
from sqlalchemy import (
    Column, Integer, BigInteger, Boolean, Numeric,
    ForeignKey, UniqueConstraint, Index, CheckConstraint
)
from sqlalchemy.orm import relationship

from .base import Base
from .mixins import TimestampMixin


class UserChainSettings(Base, TimestampMixin):
    __tablename__ = "user_chain_settings"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chain_id = Column(
        Integer,
        ForeignKey("chains.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    is_enabled = Column(
        Boolean,
        default=True,
        nullable=False,
    ) # active status for user

    buy_slippage = Column(
        Numeric(6, 2), 
        default=Decimal("10.00"),
        nullable=False,
    ) # slippage for buy (%)
    sell_slippage = Column(
        Numeric(6, 2), 
        default=Decimal("10.00"),
        nullable=False,
    ) # slippage for sell (%)
    buy_price_impact = Column(
        Numeric(5, 2), 
        default=Decimal("25.00"),
        nullable=False,
    ) # slippage for buy (%)
    sell_price_impact = Column(
        Numeric(5, 2), 
        default=Decimal("50.00"),
        nullable=False,
    ) # slippage for sell (%)
    buy_gas_delta = Column(
        Numeric(9, 2),
        default=Decimal("3.0"),
        nullable=False,
    ) # gas delta for buy (gwei)
    sell_gas_delta = Column(
        Numeric(9, 2),
        default=Decimal("3.0"),
        nullable=False,
    ) # gas delta for sell (gwei)
    approve_gas_delta = Column(
        Numeric(9, 2),
        default=Decimal("3.0"),
        nullable=False,
    ) # gas delta for approve (gwei)

    max_gas_price = Column(
        BigInteger,
        default=300,
        nullable=False,
    ) # gwei
    max_gas_limit = Column(
        BigInteger,
        default=5_000_000,
        nullable=False,
    )

    auto_approve = Column(
        Boolean,
        default=False,
        nullable=False,
    )

    user = relationship("User", back_populates="chain_settings")
    chain = relationship("Chain", back_populates="user_settings")

    __table_args__ = (
        UniqueConstraint('user_id', 'chain_id', name='uq_user_chain'),
        Index('idx_user_chain_enabled', 'user_id', 'chain_id', 'is_enabled'),
        CheckConstraint('buy_slippage >= 0.10 AND buy_slippage <= 1000', name='check_buy_slippage'),
        CheckConstraint('sell_slippage >= 0.10 AND sell_slippage <= 1000', name='check_sell_slippage'),
        CheckConstraint('buy_price_impact >= 0.10 AND sell_slippage <= 100', name='check_buy_price_impact'),
        CheckConstraint('sell_price_impact >= 0.10 AND sell_slippage <= 100', name='check_sell_price_impact'),
        CheckConstraint('buy_gas_delta >= 0.10 AND buy_gas_delta <= 1000000', name='check_buy_gas_delta'),
        CheckConstraint('sell_gas_delta >= 0.10 AND sell_gas_delta <= 1000000', name='check_sell_gas_delta'),
        CheckConstraint('approve_gas_delta >= 0.10 AND approve_gas_delta <= 1000000', name='check_approve_gas_delta'),
        CheckConstraint('max_gas_price >= 5 AND max_gas_price <= 1000000', name='check_max_gas_price'),
        CheckConstraint('max_gas_limit >= 1000000 AND max_gas_limit <= 30000000', name='check_max_gas_limit'),
    )

    def __repr__(self) -> str:
        return (
            f"<UserChainSettings(id={self.id}, user_id={self.user_id}, "
            f"chain_id={self.chain_id}, is_enabled={self.is_enabled})>"
        )

    # @property
    # def buy_slippage_percent(self) -> str:
    #     return f"{float(self.buy_slippage):.2f}%"

    # @property
    # def sell_slippage_percent(self) -> str:
    #     return f"{float(self.sell_slippage):.2f}%"
    
    # @validates('buy_slippage', 'sell_slippage')
    # def validate_slippage(self, key: str, value: Decimal) -> Decimal:
    #     if not (Decimal("0.1") <= value <= Decimal("1000")):
    #         raise ValueError(f"{key} slippage must be between 0.1 and 1000%")
    #     return value

    # @validates('buy_gas_delta', 'sell_gas_delta', 'approve_gas_delta')
    # def validate_gas_delta(self, key: str, value: Decimal) -> Decimal:
    #     if not (Decimal("1.5") <= value <= Decimal("1000000")):
    #         raise ValueError(f"{key} gas delta must be between 1.5 and 1000000")
    #     return value
    
    # @validates('max_gas_price')
    # def validate_gas_price(self, key: str, value: int) -> int:
    #     if not (5 <= value <= 1_000_000):
    #         raise ValueError(f"{key} gas price must be between 5 and 1000000")
    #     return value
    
    # @validates('max_gas_limit')
    # def validate_gas_limit(self, key: str, value: int) -> int:
    #     if not (1_000_000 <= value <= 30_000_000):
    #         raise ValueError(f"{key} gas limit must be between 1000000 and 30000000")
    #     return value

    # def reset_to_defaults(self):
    #     self.buy_slippage = Decimal("10.00")
    #     self.sell_slippage = Decimal("10.00")
    #     self.buy_gas_delta = Decimal("3.0")
    #     self.sell_gas_delta = Decimal("3.0")
    #     self.approve_gas_delta = Decimal("3.0")
    #     self.max_gas_price = 300
    #     self.max_gas_limit = 5_000_000
    #     self.auto_approve = False
