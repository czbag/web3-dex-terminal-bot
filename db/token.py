from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    Boolean,
    ForeignKey,
    Index,
    CheckConstraint,
)
from sqlalchemy.orm import relationship

from .base import Base
from .mixins import TimestampMixin


class Token(Base, TimestampMixin):
    __tablename__ = "tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chain_id = Column(
        Integer,
        ForeignKey("chains.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    address = Column(String(42), nullable=False)

    name = Column(String(100), nullable=False)
    ticker = Column(String(20), nullable=False)
    decimals = Column(Integer, nullable=False)
    total_supply = Column(BigInteger, nullable=False)

    view_count = Column(Integer, default=0, nullable=False)

    chain = relationship("Chain", back_populates="tokens")

    __table_args__ = (
        Index("idx_token_chain_address", "chain_id", "address", unique=True),
        Index("idx_token_popular", "view_count"),
        Index("idx_token_ticker", "ticker"),
        CheckConstraint("length(address) = 42", name="check_address_length"),
        CheckConstraint(
            "decimals > 0 AND decimals <= 18", name="check_decimals_range"
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Token(id={self.id}, ticker={self.ticker}, "
            f"address={self.address[:10]}..., chain_id={self.chain_id})>"
        )

    def increment_view_count(self):
        self.view_count += 1
