import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, Integer, Boolean, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Department(Base):
    """Production departments. For Customer #1 these are the 8 real
    departments confirmed in discovery: Cutting, Stitching 1-5,
    Embroidery, Packaging.

    Kept as a per-company table (not a hardcoded enum) from the start,
    since Phase 8 of the roadmap generalizes this to arbitrary
    department lists for future customers -- no rework needed later,
    just don't seed the same 8 for someone else.

    `sequence_order` preserves the physical workflow order
    (Cutting -> Stitch 1..5 -> Embroidery -> Packaging) so the waste
    table can be displayed left-to-right in production order, not
    alphabetically."""

    __tablename__ = "departments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Set when this department belongs to the in-house ("self_made") flow
    # vs. one reported back by an external CMT contractor -- see the
    # ProductionStream distinction found during the Day 2-3 data audit.
    # Left nullable until confirmed with the CEO (open question #2).
    applies_to_stream: Mapped[str] = mapped_column(String(20), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())