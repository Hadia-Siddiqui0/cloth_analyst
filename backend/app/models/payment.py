import uuid
from datetime import datetime, date as date_type
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Date, ForeignKey, Numeric, Enum, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PaymentStatus(str, PyEnum):
    UPCOMING = "upcoming"
    DUE_SOON = "due_soon"
    DUE_TODAY = "due_today"
    OVERDUE = "overdue"
    PAID = "paid"


class Payment(Base):
    """A receivable (money owed by a customer) and its payment status --
    this is the direct answer to 'who owes me money' / 'overdue
    payments', which was one of the CEO's explicit asks and one of the
    biggest confirmed gaps in his data (Day 2-3 audit found only
    contractor-payable data, nothing on the receivable side).

    `status` is stored rather than computed purely on read, since
    'due soon' vs 'due today' depends on a moving current-date
    comparison against due_date -- the receivables_service (Phase 3 of
    the roadmap) is responsible for keeping this in sync, not the model
    itself. Don't let the UI compute this independently or it'll drift
    from the alerts service that fires off the same status."""

    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    sale_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sales.id"), nullable=True)

    amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    due_date: Mapped[date_type] = mapped_column(Date, nullable=True, index=True)
    paid_date: Mapped[date_type] = mapped_column(Date, nullable=True)
    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus), default=PaymentStatus.UPCOMING, index=True)

    source_upload_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("uploads.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())