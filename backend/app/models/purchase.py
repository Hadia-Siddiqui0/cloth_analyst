import uuid
from datetime import datetime, date as date_type

from sqlalchemy import DateTime, Date, ForeignKey, Numeric, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Purchase(Base):
    """Raw material purchase transactions. No purchase records existed
    in the customer's uploaded file (confirmed gap, Day 2-3 audit) --
    this table is ready to receive them the moment he provides purchase
    data, whether that's a supplier invoice export or manual entry
    (the paper-register fallback discussed on Day 1).

    This is also what the material-consumption service (Phase 3 of the
    roadmap) will eventually subtract actual consumption from, to get
    "expected remaining" material -- so quantity/unit here must stay in
    the same unit as RawMaterial.unit for a given material."""

    __tablename__ = "purchases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)
    supplier_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("suppliers.id"), nullable=True)
    raw_material_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("raw_materials.id"), nullable=False)

    date: Mapped[date_type] = mapped_column(Date, nullable=False, index=True)
    quantity: Mapped[float] = mapped_column(Numeric(12, 3), nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    total_amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)

    source_upload_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("uploads.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())