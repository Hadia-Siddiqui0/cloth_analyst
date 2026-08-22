import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Supplier(Base):
    """Raw material suppliers. No supplier data was present in the
    customer's uploaded file (confirmed gap from the Day 2-3 audit) --
    this table is ready to receive it once he provides purchase
    records, but starts empty for Customer #1."""

    __tablename__ = "suppliers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_info: Mapped[str] = mapped_column(String(500), nullable=True)
    lead_time_days: Mapped[int] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())