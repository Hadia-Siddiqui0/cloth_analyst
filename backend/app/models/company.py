import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Company(Base):
    """The tenant. Every other table (except User, which belongs to a
    Company) is scoped by company_id -- this is what makes the platform
    multi-tenant from day one instead of needing a rewrite later."""

    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    industry: Mapped[str] = mapped_column(String(100), default="textile_apparel")
    country: Mapped[str] = mapped_column(String(100), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="PKR")
    business_type: Mapped[str] = mapped_column(String(100), nullable=True)  # e.g. manufacturer, wholesale, hybrid
    fiscal_year_start_month: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
