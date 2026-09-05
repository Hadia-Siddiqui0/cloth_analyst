import uuid
from datetime import datetime, date as date_type
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Date, ForeignKey, Numeric, Enum, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PayableStatus(str, PyEnum):
    UPCOMING = "upcoming"
    DUE_SOON = "due_soon"
    DUE_TODAY = "due_today"
    OVERDUE = "overdue"
    PAID = "paid"


class Payable(Base):
    """A payable (money owed to a supplier) and its payment status.

    Mirrors the Payment (receivable) model but for the payable side.
    Links to Supplier and optionally to a Purchase record.
    """

    __tablename__ = "payables"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)
    supplier_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("suppliers.id"), nullable=False)
    purchase_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("purchases.id"), nullable=True)

    # Reference/invoice number from the supplier
    reference: Mapped[str] = mapped_column(String(100), nullable=True)

    amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    due_date: Mapped[date_type] = mapped_column(Date, nullable=True, index=True)
    paid_date: Mapped[date_type] = mapped_column(Date, nullable=True)
    status: Mapped[PayableStatus] = mapped_column(
        Enum(PayableStatus, values_callable=lambda x: [e.value for e in x]),
        default=PayableStatus.UPCOMING,
        index=True,
    )

    source_upload_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("uploads.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())