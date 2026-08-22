import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Customer(Base):
    """Buyers of finished goods -- shops, wholesalers, or direct
    customers. This is the biggest confirmed gap from the Day 2-3 audit:
    nothing about who buys his product or who owes him money existed
    anywhere in his uploaded file. This table (and Sale, Payment below)
    stay empty for Customer #1 until he confirms where that record
    actually lives today (open question #3 from the audit) and it gets
    imported or entered.

    `customer_type` distinguishes shop/wholesaler/direct since his
    original ask specifically separated 'products in shops' from
    'products with wholesalers' -- that split needs to exist here, not
    just be inferred later."""

    __tablename__ = "customers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_type: Mapped[str] = mapped_column(String(50), nullable=True)  # "shop" | "wholesaler" | "direct"
    contact_info: Mapped[str] = mapped_column(String(500), nullable=True)
    credit_terms_days: Mapped[int] = mapped_column(Integer, nullable=True)  # e.g. 30 = net-30

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())