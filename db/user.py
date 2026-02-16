from sqlalchemy import Boolean, Column, Index, Integer, BigInteger, String
from sqlalchemy.orm import relationship

from .base import Base
from .mixins import SoftDeleteMixin, TimestampMixin


class User(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    user_id = Column(
        BigInteger,
        unique=True,
        nullable=False,
        index=True,
    )
    username = Column(
        String(32),
        nullable=True,
    )
    first_name = Column(
        String(64),
        nullable=True,
    )
    last_name = Column(
        String(64),
        nullable=True,
    )
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
    )
    is_premium = Column(
        Boolean,
        default=False,
        nullable=False,
    )
    is_blocked = Column(
        Boolean,
        default=False,
        nullable=False,
    )

    chain_settings = relationship(
        "UserChainSettings",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    wallets = relationship(
        "Wallet",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index('idx_user_active', 'is_active', 'deleted_at'),
        Index('idx_user_username', 'username')
    )

    def __repr__(self) -> str:
        return (
            f"<User(id={self.id}, user_id={self.user_id}, "
            f"username={self.username}, is_active={self.is_active})>"
        )
