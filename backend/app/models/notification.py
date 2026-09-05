import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import DateTime, ForeignKey, Enum, String, Boolean, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class NotificationType(str, PyEnum):
    """Type of notification."""
    PAYABLE_DUE_SOON = "payable_due_soon"
    PAYABLE_DUE_TODAY = "payable_due_today"
    PAYABLE_OVERDUE = "payable_overdue"
    RECEIVABLE_DUE_SOON = "receivable_due_soon"
    RECEIVABLE_DUE_TODAY = "receivable_due_today"
    RECEIVABLE_OVERDUE = "receivable_overdue"
    CEO_ATTENTION = "ceo_attention"


class NotificationChannel(str, PyEnum):
    """Delivery channel for notification."""
    IN_APP = "in_app"
    EMAIL = "email"
    PUSH = "push"


class Notification(Base):
    """Notification/reminder for due dates, overdue items, and CEO attention items.

    Uses an idempotency_key to prevent duplicate notifications for the same
    entity + trigger combination. The key format:
    - payable:{payable_id}:{type} for payable reminders
    - receivable:{payment_id}:{type} for receivable reminders
    - ceo:{company_id}:{date}:{type} for CEO attention
    """

    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)

    type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True,
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        Enum(NotificationChannel, values_callable=lambda x: [e.value for e in x]),
        default=NotificationChannel.IN_APP,
    )

    # Idempotency key - unique per entity + trigger combination
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False, unique=True, index=True)

    # Reference to the entity that triggered this notification
    reference_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    reference_type: Mapped[str] = mapped_column(String(50), nullable=True)  # "payable", "receivable", "ceo"

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(String(1000), nullable=False)

    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    read_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)