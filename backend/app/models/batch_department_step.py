import uuid
from datetime import datetime, date as date_type

from sqlalchemy import DateTime, Date, ForeignKey, Numeric, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class BatchDepartmentStep(Base):
    """One department's leg of a batch's journey. This is what makes the
    5-stitching-departments requirement real: a self-made batch gets one
    row per department it passes through (Cutting, Stitch 1, Stitch 2...),
    each with its own quantity in/out and waste -- not one pooled number.

    `department_id` is nullable because a CMT (outsourced) batch likely
    has no internal department breakdown at all -- it may get a single
    step row with department_id=NULL representing "sent to contractor,
    came back finished". This still needs confirming with the CEO
    (open question from the Day 2-3 audit) before self-made batches are
    entered for real -- don't assume the 5-way split applies to CMT."""

    __tablename__ = "batch_department_steps"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)
    batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("production_batches.id"), nullable=False, index=True)
    department_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("departments.id"), nullable=True)

    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_in: Mapped[float] = mapped_column(Numeric(12, 3), nullable=True)
    quantity_out: Mapped[float] = mapped_column(Numeric(12, 3), nullable=True)
    expected_waste: Mapped[float] = mapped_column(Numeric(12, 3), nullable=True)
    actual_waste: Mapped[float] = mapped_column(Numeric(12, 3), nullable=True)
    cost_at_step: Mapped[float] = mapped_column(Numeric(14, 2), nullable=True)

    date_started: Mapped[date_type] = mapped_column(Date, nullable=True)
    date_completed: Mapped[date_type] = mapped_column(Date, nullable=True)
    notes: Mapped[str] = mapped_column(String(1000), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())