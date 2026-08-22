import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import String, DateTime, ForeignKey, Enum, func, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UploadStatus(str, PyEnum):
    UPLOADED = "uploaded"
    MAPPED = "mapped"          # column mapping confirmed by user
    VALIDATED = "validated"
    IMPORTED = "imported"
    FAILED = "failed"


class Upload(Base):
    """Every file the customer sends in gets one row here, regardless of
    whether it's the old messy reference file or his real ongoing data.
    This is the audit trail: every number on the dashboard should be
    traceable back to one of these. `column_mapping` stores exactly what
    the ingestion engine decided (or the user confirmed) so re-imports
    of a similarly-shaped file can reuse it."""

    __tablename__ = "uploads"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)

    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    status: Mapped[UploadStatus] = mapped_column(Enum(UploadStatus), default=UploadStatus.UPLOADED)

    column_mapping: Mapped[dict] = mapped_column(JSON, nullable=True)   # {sheet_name: {source_col: canonical_field}}
    validation_issues: Mapped[dict] = mapped_column(JSON, nullable=True)  # missing values, dup rows, invalid dates etc.
    rows_imported: Mapped[int] = mapped_column(nullable=True)

    uploaded_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
