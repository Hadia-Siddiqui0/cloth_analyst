import uuid
from datetime import datetime, date as date_type
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Date, ForeignKey, Numeric, String, Enum, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class InventoryType(str, PyEnum):
    RAW_MATERIAL = "raw_material"
    WORK_IN_PROGRESS = "work_in_progress"
    FINISHED_GOODS = "finished_goods"


class InventoryLocation(str, PyEnum):
    WAREHOUSE = "warehouse"
    SHOP = "shop"
    WHOLESALER = "wholesaler"


class InventorySnapshot(Base):
    """Point-in-time stock count. No inventory data exists in the
    customer's file yet (confirmed gap, Day 2-3 audit) -- this is a
    snapshot model rather than a running ledger deliberately, since
    without real stock-take data there's no reliable way to compute a
    continuous balance; a snapshot only claims to know what was true
    on `snapshot_date`, nothing more, which matches the 'never invent
    missing data' principle from the spec.

    Once real stock-take data arrives, `days_of_inventory` and
    turnover metrics (Phase 3 of the roadmap, inventory_service.py)
    get computed between two snapshots -- they don't live on this
    model directly."""

    __tablename__ = "inventory_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)

    # exactly one of these two should be set, depending on inventory_type
    raw_material_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("raw_materials.id"), nullable=True)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True)

    inventory_type: Mapped[InventoryType] = mapped_column(
        Enum(InventoryType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    location: Mapped[InventoryLocation] = mapped_column(
        Enum(InventoryLocation, values_callable=lambda x: [e.value for e in x]),
        nullable=True,
    )  # null for raw material/WIP, set for finished goods
    location_detail: Mapped[str] = mapped_column(String(255), nullable=True)  # e.g. which shop, which wholesaler

    quantity: Mapped[float] = mapped_column(Numeric(14, 3), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    snapshot_date: Mapped[date_type] = mapped_column(Date, nullable=False, index=True)

    source_upload_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("uploads.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())