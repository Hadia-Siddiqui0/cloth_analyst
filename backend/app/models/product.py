import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, Numeric, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Product(Base):
    """Standard per-article costing -- maps to what was found in Sheet4
    of the customer's file (cloth type, meters/piece, cost breakdown,
    sale price, profit/piece). This doubles as the 'expected consumption'
    baseline for the waste-detection service later."""

    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)

    cloth_type: Mapped[str] = mapped_column(String(255), nullable=False)
    article_code: Mapped[str] = mapped_column(String(100), nullable=True)

    cost_per_meter: Mapped[float] = mapped_column(Numeric(12, 2), nullable=True)
    cloth_meters_per_piece: Mapped[float] = mapped_column(Numeric(10, 3), nullable=True)  # ← expected consumption/piece
    cloth_cost_per_piece: Mapped[float] = mapped_column(Numeric(12, 2), nullable=True)
    stitching_cost_per_piece: Mapped[float] = mapped_column(Numeric(12, 2), nullable=True)
    embroidery_cost_per_piece: Mapped[float] = mapped_column(Numeric(12, 2), nullable=True)
    washing_cost_per_piece: Mapped[float] = mapped_column(Numeric(12, 2), nullable=True)
    total_cost_per_piece: Mapped[float] = mapped_column(Numeric(12, 2), nullable=True)

    sale_price_per_piece: Mapped[float] = mapped_column(Numeric(12, 2), nullable=True)
    profit_per_piece: Mapped[float] = mapped_column(Numeric(12, 2), nullable=True)

    # provenance -- was this value read directly from a file, or estimated/entered manually?
    source: Mapped[str] = mapped_column(String(20), default="verified")  # verified | estimated | manual

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
