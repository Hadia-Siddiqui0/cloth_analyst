import uuid
from datetime import datetime, date as date_type

from sqlalchemy import DateTime, Date, ForeignKey, Numeric, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ContractorLedgerEntry(Base):
    """Running balance of what's owed to an outsourced (CMT) production
    contractor -- this is a payable, not a receivable. Found as
    'Contractor Invoice' in the customer's file. Kept separate from the
    customer/receivables model (not yet built -- no data for it exists
    in what he's shared so far)."""

    __tablename__ = "contractor_ledger_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)

    date: Mapped[date_type] = mapped_column(Date, nullable=False, index=True)
    amount_billed: Mapped[float] = mapped_column(Numeric(14, 2), nullable=True)
    amount_paid: Mapped[float] = mapped_column(Numeric(14, 2), nullable=True)
    running_balance: Mapped[float] = mapped_column(Numeric(14, 2), nullable=True)

    source_upload_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("uploads.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
