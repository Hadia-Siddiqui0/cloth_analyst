"""
Reminder/notification service for payment due dates and CEO attention.

Generates notifications for:
- Payables: 7/3/1 days before due, due today, overdue
- Receivables: 7/3/1 days before due, due today, overdue
- CEO Attention: Summary of items requiring executive review

Uses idempotency keys to prevent duplicate notifications on re-runs.
"""
import uuid
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models.notification import (
    Notification, NotificationType, NotificationChannel
)
from app.models.payable import Payable, PayableStatus
from app.models.payment import Payment, PaymentStatus
from app.models.user import User
from app.models.company import Company


# Reminder schedule: days before due date to send reminders
REMINDER_DAYS_BEFORE = [7, 3, 1]


def _generate_idempotency_key(reference_type: str, reference_id: uuid.UUID, trigger_type: str) -> str:
    """Generate a unique idempotency key for a notification."""
    return f"{reference_type}:{reference_id}:{trigger_type}"


def _get_company_ceo(db: Session, company_id: uuid.UUID) -> Optional[User]:
    """Get the CEO user for a company (first user with role 'ceo' or first user)."""
    # Try to find a user with CEO role
    ceo = db.query(User).filter(
        User.company_id == company_id,
        User.role == "ceo"
    ).first()
    if ceo:
        return ceo
    # Fallback: first user in company
    return db.query(User).filter(User.company_id == company_id).first()


def create_payable_reminders(db: Session, company_id: uuid.UUID, today: date = None) -> int:
    """Create reminder notifications for payables (money we owe suppliers).

    Returns count of notifications created.
    """
    today = today or date.today()
    created = 0

    # Get CEO for CEO attention notifications
    ceo = _get_company_ceo(db, company_id)
    ceo_id = ceo.id if ceo else None

    # --- 7/3/1 days before due ---
    for days_before in REMINDER_DAYS_BEFORE:
        target_date = today + timedelta(days=days_before)

        payables = db.query(Payable).filter(
            Payable.company_id == company_id,
            Payable.due_date == target_date,
            Payable.paid_date.is_(None),
            Payable.status.in_([PayableStatus.UPCOMING, PayableStatus.DUE_SOON]),
        ).all()

        for payable in payables:
            key = _generate_idempotency_key("payable", payable.id, f"due_in_{days_before}")
            existing = db.query(Notification).filter(Notification.idempotency_key == key).first()
            if existing:
                continue

            notification = Notification(
                company_id=company_id,
                user_id=ceo_id,
                type=NotificationType.PAYABLE_DUE_SOON,
                channel=NotificationChannel.IN_APP,
                idempotency_key=key,
                reference_id=payable.id,
                reference_type="payable",
                title=f"Payment due in {days_before} day{'s' if days_before > 1 else ''}",
                message=f"Payable to {payable.supplier_id} (ref: {payable.reference or 'N/A'}) "
                        f"of ${payable.amount:,.2f} is due on {payable.due_date}.",
            )
            db.add(notification)
            created += 1

    # --- Due today ---
    payables_due_today = db.query(Payable).filter(
        Payable.company_id == company_id,
        Payable.due_date == today,
        Payable.paid_date.is_(None),
        Payable.status.in_([PayableStatus.UPCOMING, PayableStatus.DUE_SOON]),
    ).all()

    for payable in payables_due_today:
        key = _generate_idempotency_key("payable", payable.id, "due_today")
        existing = db.query(Notification).filter(Notification.idempotency_key == key).first()
        if existing:
            continue

        notification = Notification(
            company_id=company_id,
            user_id=ceo_id,
            type=NotificationType.PAYABLE_DUE_TODAY,
            channel=NotificationChannel.IN_APP,
            idempotency_key=key,
            reference_id=payable.id,
            reference_type="payable",
            title="Payment due today",
            message=f"Payable to supplier (ref: {payable.reference or 'N/A'}) "
                    f"of ${payable.amount:,.2f} is due today.",
        )
        db.add(notification)
        created += 1

    # --- Overdue ---
    overdue_payables = db.query(Payable).filter(
        Payable.company_id == company_id,
        Payable.due_date < today,
        Payable.paid_date.is_(None),
        Payable.status != PayableStatus.PAID,
    ).all()

    for payable in overdue_payables:
        key = _generate_idempotency_key("payable", payable.id, "overdue")
        existing = db.query(Notification).filter(Notification.idempotency_key == key).first()
        if existing:
            continue

        days_overdue = (today - payable.due_date).days
        notification = Notification(
            company_id=company_id,
            user_id=ceo_id,
            type=NotificationType.PAYABLE_OVERDUE,
            channel=NotificationChannel.IN_APP,
            idempotency_key=key,
            reference_id=payable.id,
            reference_type="payable",
            title=f"Overdue payment ({days_overdue} day{'s' if days_overdue > 1 else ''} overdue)",
            message=f"Payable to supplier (ref: {payable.reference or 'N/A'}) "
                    f"of ${payable.amount:,.2f} was due on {payable.due_date}.",
        )
        db.add(notification)
        created += 1

    db.commit()
    return created


def create_receivable_reminders(db: Session, company_id: uuid.UUID, today: date = None) -> int:
    """Create reminder notifications for receivables (money customers owe us).

    Returns count of notifications created.
    """
    today = today or date.today()
    created = 0

    # Get CEO for CEO attention notifications
    ceo = _get_company_ceo(db, company_id)
    ceo_id = ceo.id if ceo else None

    # --- 7/3/1 days before due ---
    for days_before in REMINDER_DAYS_BEFORE:
        target_date = today + timedelta(days=days_before)

        payments = db.query(Payment).filter(
            Payment.company_id == company_id,
            Payment.due_date == target_date,
            Payment.paid_date.is_(None),
            Payment.status.in_([PaymentStatus.UPCOMING, PaymentStatus.DUE_SOON]),
        ).all()

        for payment in payments:
            key = _generate_idempotency_key("receivable", payment.id, f"due_in_{days_before}")
            existing = db.query(Notification).filter(Notification.idempotency_key == key).first()
            if existing:
                continue

            notification = Notification(
                company_id=company_id,
                user_id=ceo_id,
                type=NotificationType.RECEIVABLE_DUE_SOON,
                channel=NotificationChannel.IN_APP,
                idempotency_key=key,
                reference_id=payment.id,
                reference_type="receivable",
                title=f"Receivable due in {days_before} day{'s' if days_before > 1 else ''}",
                message=f"Payment from customer (ref: {payment.customer_id}) "
                        f"of ${payment.amount:,.2f} is due on {payment.due_date}.",
            )
            db.add(notification)
            created += 1

    # --- Due today ---
    payments_due_today = db.query(Payment).filter(
        Payment.company_id == company_id,
        Payment.due_date == today,
        Payment.paid_date.is_(None),
        Payment.status.in_([PaymentStatus.UPCOMING, PaymentStatus.DUE_SOON]),
    ).all()

    for payment in payments_due_today:
        key = _generate_idempotency_key("receivable", payment.id, "due_today")
        existing = db.query(Notification).filter(Notification.idempotency_key == key).first()
        if existing:
            continue

        notification = Notification(
            company_id=company_id,
            user_id=ceo_id,
            type=NotificationType.RECEIVABLE_DUE_TODAY,
            channel=NotificationChannel.IN_APP,
            idempotency_key=key,
            reference_id=payment.id,
            reference_type="receivable",
            title="Receivable due today",
            message=f"Payment from customer (ref: {payment.customer_id}) "
                    f"of ${payment.amount:,.2f} is due today.",
        )
        db.add(notification)
        created += 1

    # --- Overdue ---
    overdue_payments = db.query(Payment).filter(
        Payment.company_id == company_id,
        Payment.due_date < today,
        Payment.paid_date.is_(None),
        Payment.status != PaymentStatus.PAID,
    ).all()

    for payment in overdue_payments:
        key = _generate_idempotency_key("receivable", payment.id, "overdue")
        existing = db.query(Notification).filter(Notification.idempotency_key == key).first()
        if existing:
            continue

        days_overdue = (today - payment.due_date).days
        notification = Notification(
            company_id=company_id,
            user_id=ceo_id,
            type=NotificationType.RECEIVABLE_OVERDUE,
            channel=NotificationChannel.IN_APP,
            idempotency_key=key,
            reference_id=payment.id,
            reference_type="receivable",
            title=f"Overdue receivable ({days_overdue} day{'s' if days_overdue > 1 else ''} overdue)",
            message=f"Payment from customer (ref: {payment.customer_id}) "
                    f"of ${payment.amount:,.2f} was due on {payment.due_date}.",
        )
        db.add(notification)
        created += 1

    db.commit()
    return created


def create_ceo_attention_notifications(db: Session, company_id: uuid.UUID, today: date = None) -> int:
    """Create CEO attention notifications for items requiring executive review.

    CEO attention items:
    - Large overdue payables (> $10,000)
    - Large overdue receivables (> $10,000)
    - Multiple overdue items from same supplier/customer
    - Payables due today over $5,000

    Returns count of notifications created.
    """
    today = today or date.today()
    created = 0

    ceo = _get_company_ceo(db, company_id)
    if not ceo:
        return 0

    # --- Large overdue payables ---
    large_overdue_payables = db.query(Payable).filter(
        Payable.company_id == company_id,
        Payable.due_date < today,
        Payable.paid_date.is_(None),
        Payable.amount >= 10000,
        Payable.status != PayableStatus.PAID,
    ).all()

    for payable in large_overdue_payables:
        key = _generate_idempotency_key("ceo", company_id, f"large_overdue_payable_{payable.id}")
        existing = db.query(Notification).filter(Notification.idempotency_key == key).first()
        if existing:
            continue

        days_overdue = (today - payable.due_date).days
        notification = Notification(
            company_id=company_id,
            user_id=ceo.id,
            type=NotificationType.CEO_ATTENTION,
            channel=NotificationChannel.IN_APP,
            idempotency_key=key,
            reference_id=payable.id,
            reference_type="payable",
            title=f"CEO Attention: Large overdue payable (${payable.amount:,.2f})",
            message=f"Payable to supplier of ${payable.amount:,.2f} is {days_overdue} day{'s' if days_overdue > 1 else ''} overdue. "
                    f"Reference: {payable.reference or 'N/A'}.",
        )
        db.add(notification)
        created += 1

    # --- Large overdue receivables ---
    large_overdue_receivables = db.query(Payment).filter(
        Payment.company_id == company_id,
        Payment.due_date < today,
        Payment.paid_date.is_(None),
        Payment.amount >= 10000,
        Payment.status != PaymentStatus.PAID,
    ).all()

    for payment in large_overdue_receivables:
        key = _generate_idempotency_key("ceo", company_id, f"large_overdue_receivable_{payment.id}")
        existing = db.query(Notification).filter(Notification.idempotency_key == key).first()
        if existing:
            continue

        days_overdue = (today - payment.due_date).days
        notification = Notification(
            company_id=company_id,
            user_id=ceo.id,
            type=NotificationType.CEO_ATTENTION,
            channel=NotificationChannel.IN_APP,
            idempotency_key=key,
            reference_id=payment.id,
            reference_type="receivable",
            title=f"CEO Attention: Large overdue receivable (${payment.amount:,.2f})",
            message=f"Receivable from customer of ${payment.amount:,.2f} is {days_overdue} day{'s' if days_overdue > 1 else ''} overdue.",
        )
        db.add(notification)
        created += 1

    # --- Payables due today over $5,000 ---
    large_due_today_payables = db.query(Payable).filter(
        Payable.company_id == company_id,
        Payable.due_date == today,
        Payable.paid_date.is_(None),
        Payable.amount >= 5000,
    ).all()

    for payable in large_due_today_payables:
        key = _generate_idempotency_key("ceo", company_id, f"large_due_today_payable_{payable.id}")
        existing = db.query(Notification).filter(Notification.idempotency_key == key).first()
        if existing:
            continue

        notification = Notification(
            company_id=company_id,
            user_id=ceo.id,
            type=NotificationType.CEO_ATTENTION,
            channel=NotificationChannel.IN_APP,
            idempotency_key=key,
            reference_id=payable.id,
            reference_type="payable",
            title=f"CEO Attention: Large payment due today (${payable.amount:,.2f})",
            message=f"Payable to supplier of ${payable.amount:,.2f} is due today. "
                    f"Reference: {payable.reference or 'N/A'}.",
        )
        db.add(notification)
        created += 1

    db.commit()
    return created


def run_all_reminders(db: Session, company_id: uuid.UUID, today: date = None) -> dict:
    """Run all reminder generation for a company.

    Returns dict with counts of notifications created per category.
    """
    today = today or date.today()

    payable_count = create_payable_reminders(db, company_id, today)
    receivable_count = create_receivable_reminders(db, company_id, today)
    ceo_count = create_ceo_attention_notifications(db, company_id, today)

    return {
        "payable_reminders": payable_count,
        "receivable_reminders": receivable_count,
        "ceo_attention": ceo_count,
        "total": payable_count + receivable_count + ceo_count,
    }


def get_user_notifications(db: Session, user_id: uuid.UUID, unread_only: bool = False, limit: int = 50) -> list[Notification]:
    """Get notifications for a user."""
    query = db.query(Notification).filter(Notification.user_id == user_id)
    if unread_only:
        query = query.filter(Notification.is_read == False)
    return query.order_by(Notification.created_at.desc()).limit(limit).all()


def get_company_notifications(db: Session, company_id: uuid.UUID, unread_only: bool = False, limit: int = 50) -> list[Notification]:
    """Get all notifications for a company (for CEO dashboard)."""
    query = db.query(Notification).filter(Notification.company_id == company_id)
    if unread_only:
        query = query.filter(Notification.is_read == False)
    return query.order_by(Notification.created_at.desc()).limit(limit).all()


def mark_notification_read(db: Session, notification_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    """Mark a notification as read."""
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == user_id
    ).first()
    if not notification:
        return False
    notification.is_read = True
    notification.read_at = datetime.utcnow()
    db.commit()
    return True


def mark_all_read(db: Session, user_id: uuid.UUID) -> int:
    """Mark all notifications as read for a user."""
    count = db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.is_read == False
    ).update({
        "is_read": True,
        "read_at": datetime.utcnow()
    })
    db.commit()
    return count