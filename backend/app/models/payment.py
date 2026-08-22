import uuid
from datetime import datetime, date as date_type

from sqlalchemy import String, DateTime, Date, ForeignKey, Numeric, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Sale(Base):
    """A finished-goods sale to a customer. Distinct from ProductionRun
    (which tracks his historical daily cost/revenue logs as imported) --
    Sale is the properly normalized, customer-linked record going
    forward, the same relationship ProductionBatch has to ProductionRun.

    channel free-text for now (e.g. "shop - Karachi", "wholesaler - X")
    rather than a foreign key to a Store/Location table -- add that
    normalization once there's enough real sales data to know it's
    worth it; don't build a table for zero rows."""

    __tablename__ = "sales"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True)

    date: Mapped[date_type] = mapped_column(Date, nullable=False, index=True)
    quantity: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    discount_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=True)
    total_amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    channel: Mapped[str] = mapped_column(String(255), nullable=True)

    source_upload_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("uploads.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())