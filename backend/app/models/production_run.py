import uuid
from datetime import datetime, date as date_type
from enum import Enum as PyEnum

from sqlalchemy import String, DateTime, Date, ForeignKey, Numeric, Enum, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ProductionStream(str, PyEnum):
    SELF_MADE = "self_made"     # in-house production
    CMT = "cmt"                 # outsourced to a Cut-Make-Trim contractor
    UNSPECIFIED = "unspecified"  # stream not yet confirmed with the customer


class ProductionRun(Base):
    """One day's production/cost/revenue record. Generalized from what
    the customer's real file actually contained: no reliable department
    breakdown yet (see Product.article_code / future Department model),
    but daily cost -> revenue -> profit is solid.

    `source_sheet` and `stream` are kept because the customer's own file
    tracked self-made and outsourced (CMT) production separately with
    different cost structures -- don't silently merge them until that's
    confirmed with him."""

    __tablename__ = "production_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True)

    date: Mapped[date_type] = mapped_column(Date, nullable=False, index=True)
    stream: Mapped[ProductionStream] = mapped_column(Enum(ProductionStream), default=ProductionStream.UNSPECIFIED)
    article_label: Mapped[str] = mapped_column(String(100), nullable=True)  # raw article code as given, pre-mapping
    quantity: Mapped[float] = mapped_column(Numeric(12, 2), nullable=True)

    cost_total: Mapped[float] = mapped_column(Numeric(14, 2), nullable=True)
    sale_price_piece: Mapped[float] = mapped_column(Numeric(12, 2), nullable=True)
    revenue_total: Mapped[float] = mapped_column(Numeric(14, 2), nullable=True)
    profit: Mapped[float] = mapped_column(Numeric(14, 2), nullable=True)

    # traceability back to the exact upload/sheet this row came from
    source_upload_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("uploads.id"), nullable=True)
    source_sheet: Mapped[str] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
