import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class NotificationOut(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    user_id: Optional[uuid.UUID]
    type: str
    channel: str
    idempotency_key: str
    reference_id: Optional[uuid.UUID]
    reference_type: Optional[str]
    title: str
    message: str
    is_read: bool
    read_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationMarkRead(BaseModel):
    notification_id: uuid.UUID


class NotificationsResponse(BaseModel):
    notifications: list[NotificationOut]
    unread_count: int