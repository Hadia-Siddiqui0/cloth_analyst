import uuid
from datetime import datetime, date as date_type

from sqlalchemy import String, DateTime, Date, ForeignKey, Numeric, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Expense(Base):
    """General petty-cash / expense ledger entries -- from the
    customer's 'Balance Sheet' style sheets. `category` is assigned by
    the ingestion service using keyword rules for now (see
    services/ingestion_service.py); flag for review if it should
    become a proper user-editable category list later."""

    __tablename__ = "expenses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)

    date: Mapped[date_type] = mapped_column(Date, nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(500), nullable=True)
    category: Mapped[str] = mapped_column(String(100), nullable=True)
    amount_received: Mapped[float] = mapped_column(Numeric(14, 2), nullable=True)
    amount_used: Mapped[float] = mapped_column(Numeric(14, 2), nullable=True)
    running_balance: Mapped[float] = mapped_column(Numeric(14, 2), nullable=True)

    source_upload_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("uploads.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
