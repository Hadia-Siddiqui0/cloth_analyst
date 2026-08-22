import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, Numeric, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RawMaterial(Base):
    """Raw materials (fabric, thread, buttons, etc.). `last_known_unit_price`
    is a convenience snapshot -- the real price history should come from
    Purchase records once that table exists (Day 6 of the roadmap); this
    field just avoids a null UI on day one before any purchase has been
    imported.

    `unit` intentionally free-text (not an enum) since garment raw
    materials mix units in practice (meters of cloth, pieces of buttons,
    kg of thread) and a future customer's file may use a unit this one
    never did."""

    __tablename__ = "raw_materials"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)
    supplier_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("suppliers.id"), nullable=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    material_type: Mapped[str] = mapped_column(String(100), nullable=True)  # e.g. "cloth", "thread", "button"
    unit: Mapped[str] = mapped_column(String(20), nullable=False)  # e.g. "meter", "kg", "piece"
    last_known_unit_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())