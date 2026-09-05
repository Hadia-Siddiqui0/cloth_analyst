import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_company_id, get_current_user_id
from app.db.session import get_db
from app.schemas.notification import NotificationOut, NotificationsResponse, NotificationMarkRead
from app.services import reminder_service

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("", response_model=NotificationsResponse)
def get_notifications(
    unread_only: bool = False,
    limit: int = 50,
    company_id: uuid.UUID = Depends(get_current_company_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Get notifications for the current user."""
    notifications = reminder_service.get_user_notifications(db, user_id, unread_only, limit)
    unread_count = len([n for n in notifications if not n.is_read])

    return NotificationsResponse(
        notifications=notifications,
        unread_count=unread_count,
    )


@router.get("/company", response_model=NotificationsResponse)
def get_company_notifications(
    unread_only: bool = False,
    limit: int = 50,
    company_id: uuid.UUID = Depends(get_current_company_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Get all notifications for the company (CEO view)."""
    # Verify user is CEO or admin
    # For now, allow all authenticated users to see company notifications
    notifications = reminder_service.get_company_notifications(db, company_id, unread_only, limit)
    unread_count = len([n for n in notifications if not n.is_read])

    return NotificationsResponse(
        notifications=notifications,
        unread_count=unread_count,
    )


@router.post("/mark-read", response_model=dict)
def mark_read(
    payload: NotificationMarkRead,
    company_id: uuid.UUID = Depends(get_current_company_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Mark a notification as read."""
    success = reminder_service.mark_notification_read(db, payload.notification_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"success": True}


@router.post("/mark-all-read", response_model=dict)
def mark_all_read(
    company_id: uuid.UUID = Depends(get_current_company_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Mark all notifications as read for the current user."""
    count = reminder_service.mark_all_read(db, user_id)
    return {"success": True, "marked_read": count}


@router.post("/run-reminders", response_model=dict)
def run_reminders(
    company_id: uuid.UUID = Depends(get_current_company_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Manually trigger reminder generation for the company.
    Normally this would run on a schedule (cron job).
    """
    result = reminder_service.run_all_reminders(db, company_id)
    return {"success": True, **result}