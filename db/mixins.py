from sqlalchemy import Column, DateTime
from sqlalchemy.sql import func


class TimestampMixin:
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def formatted_created_at(self, date_format: str = "%d.%m.%Y %H:%M") -> str:
        if self.created_at:
            return self.created_at.strftime(date_format)
        return ""

    def formatted_updated_at(self, date_format: str = "%d.%m.%Y %H:%M") -> str:
        if self.updated_at:
            return self.updated_at.strftime(date_format)
        return ""


class SoftDeleteMixin:
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def soft_delete(self):
        self.deleted_at = datetime.utcnow()

    def restore(self):
        self.deleted_at = None
