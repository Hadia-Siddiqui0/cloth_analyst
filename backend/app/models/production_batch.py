import uuid
from datetime import datetime, date as date_type

from sqlalchemy import String, DateTime, Date, ForeignKey, Numeric, Enum, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.production_run import ProductionStream  # reuse -- same DB enum, don't duplicate the type


class ProductionBatch(Base):
    """One production run/batch, e.g. 'Batch #1048'. This is the
    header-level record; its journey through individual departments
    (Cutting -> Stitch 1-5 -> Embroidery -> Packaging for self-made, or
    a single contractor step for CMT) lives in BatchDepartmentStep.

    Expected values (expected_output_quantity, expected_waste) should
    be derived from Product.cloth_meters_per_piece and similar standard-
    costing fields where possible -- don't hand-enter an expectation
    that's already computable, or the two will drift out of sync.

    Note: production_runs (from the Day 2-3 ingested data) predates this
    table and is NOT the same thing -- those are the customer's original
    daily cost/revenue logs, kept as-is for traceability. ProductionBatch
    is the properly normalized model going forward for anything entered
    through the app directly (vs. imported from his historical files)."""

    __tablename__ = "production_batches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True)

    batch_code: Mapped[str] = mapped_column(String(50), nullable=True)  # e.g. "Batch #1048"
    stream: Mapped[ProductionStream] = mapped_column(Enum(ProductionStream, name="productionstream"), default=ProductionStream.UNSPECIFIED)

    material_input_quantity: Mapped[float] = mapped_column(Numeric(12, 3), nullable=True)  # e.g. meters of fabric in
    expected_output_quantity: Mapped[float] = mapped_column(Numeric(12, 2), nullable=True)
    actual_output_quantity: Mapped[float] = mapped_column(Numeric(12, 2), nullable=True)
    expected_waste: Mapped[float] = mapped_column(Numeric(12, 3), nullable=True)
    actual_waste: Mapped[float] = mapped_column(Numeric(12, 3), nullable=True)
    production_cost: Mapped[float] = mapped_column(Numeric(14, 2), nullable=True)

    date_started: Mapped[date_type] = mapped_column(Date, nullable=True, index=True)
    date_completed: Mapped[date_type] = mapped_column(Date, nullable=True)

    source_upload_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("uploads.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())