import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.deps import get_current_company_id, get_current_user_id
from app.db.session import get_db
from app.models.payable import Payable, PayableStatus
from app.models.payment import Payment, PaymentStatus
from app.models.user import User
from app.services import payables_service, receivables_service, reminder_service

router = APIRouter(prefix="/api/ceo", tags=["ceo"])


@router.get("/attention")
def get_ceo_attention(
    company_id: uuid.UUID = Depends(get_current_company_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Get CEO attention dashboard - summary of items requiring executive review.

    Returns:
    - Overdue payables (total amount, count, largest items)
    - Overdue receivables (total amount, count, largest items)
    - Payables due today (total amount, count)
    - Receivables due today (total amount, count)
    - Payables due soon (1-3 days)
    - Receivables due soon (1-3 days)
    - Unread notification count
    """
    today = date.today()

    # Get all payables and receivables with computed status
    payables = payables_service.get_payables(db, company_id)
    receivables = receivables_service.get_receivables(db, company_id)

    # Categorize payables
    overdue_payables = [p for p in payables if p["status"] == "overdue"]
    due_today_payables = [p for p in payables if p["status"] == "due_today"]
    due_soon_payables = [p for p in payables if p["status"] == "due_soon"]
    upcoming_payables = [p for p in payables if p["status"] == "upcoming"]
    paid_payables = [p for p in payables if p["status"] == "paid"]

    # Categorize receivables
    overdue_receivables = [r for r in receivables if r["status"] == "overdue"]
    due_today_receivables = [r for r in receivables if r["status"] == "due_today"]
    due_soon_receivables = [r for r in receivables if r["status"] == "due_soon"]
    upcoming_receivables = [r for r in receivables if r["status"] == "upcoming"]
    paid_receivables = [r for r in receivables if r["status"] == "paid"]

    # Get unread notification count for CEO
    ceo = db.query(User).filter(
        User.company_id == company_id,
        User.role == "ceo"
    ).first()
    if not ceo:
        ceo = db.query(User).filter(User.company_id == company_id).first()

    unread_notifications = 0
    if ceo:
        unread_notifications = len([
            n for n in reminder_service.get_user_notifications(db, ceo.id, unread_only=True)
        ])

    # Top 5 largest overdue payables
    top_overdue_payables = sorted(overdue_payables, key=lambda x: x["amount"], reverse=True)[:5]
    top_overdue_receivables = sorted(overdue_receivables, key=lambda x: x["amount"], reverse=True)[:5]

    # Top 5 largest due today
    top_due_today_payables = sorted(due_today_payables, key=lambda x: x["amount"], reverse=True)[:5]
    top_due_today_receivables = sorted(due_today_receivables, key=lambda x: x["amount"], reverse=True)[:5]

    return {
        "summary": {
            "payables": {
                "overdue": {
                    "count": len(overdue_payables),
                    "total_amount": round(sum(p["amount"] for p in overdue_payables), 2),
                    "top_items": [
                        {
                            "id": p["id"],
                            "supplier_name": p["supplier_name"],
                            "amount": p["amount"],
                            "due_date": p["due_date"],
                            "days_overdue": (today - p["due_date"]).days if p["due_date"] else 0,
                            "reference": p["reference"],
                        }
                        for p in top_overdue_payables
                    ],
                },
                "due_today": {
                    "count": len(due_today_payables),
                    "total_amount": round(sum(p["amount"] for p in due_today_payables), 2),
                    "top_items": [
                        {
                            "id": p["id"],
                            "supplier_name": p["supplier_name"],
                            "amount": p["amount"],
                            "reference": p["reference"],
                        }
                        for p in top_due_today_payables
                    ],
                },
                "due_soon": {
                    "count": len(due_soon_payables),
                    "total_amount": round(sum(p["amount"] for p in due_soon_payables), 2),
                },
                "upcoming": {
                    "count": len(upcoming_payables),
                    "total_amount": round(sum(p["amount"] for p in upcoming_payables), 2),
                },
            },
            "receivables": {
                "overdue": {
                    "count": len(overdue_receivables),
                    "total_amount": round(sum(r["amount"] for r in overdue_receivables), 2),
                    "top_items": [
                        {
                            "id": r["id"],
                            "customer_name": r["customer_name"],
                            "amount": r["amount"],
                            "due_date": r["due_date"],
                            "days_overdue": (today - r["due_date"]).days if r["due_date"] else 0,
                        }
                        for r in top_overdue_receivables
                    ],
                },
                "due_today": {
                    "count": len(due_today_receivables),
                    "total_amount": round(sum(r["amount"] for r in due_today_receivables), 2),
                    "top_items": [
                        {
                            "id": r["id"],
                            "customer_name": r["customer_name"],
                            "amount": r["amount"],
                        }
                        for r in top_due_today_receivables
                    ],
                },
                "due_soon": {
                    "count": len(due_soon_receivables),
                    "total_amount": round(sum(r["amount"] for r in due_soon_receivables), 2),
                },
                "upcoming": {
                    "count": len(upcoming_receivables),
                    "total_amount": round(sum(r["amount"] for r in upcoming_receivables), 2),
                },
            },
            "net_position": {
                "total_payable_outstanding": round(sum(p["amount"] for p in payables if p["status"] != "paid"), 2),
                "total_receivable_outstanding": round(sum(r["amount"] for r in receivables if r["status"] != "paid"), 2),
                "net_cash_flow": round(
                    sum(r["amount"] for r in receivables if r["status"] != "paid")
                    - sum(p["amount"] for p in payables if p["status"] != "paid"),
                    2
                ),
            },
            "unread_notifications": unread_notifications,
        }
    }


@router.get("/attention/notifications")
def get_ceo_notifications(
    unread_only: bool = False,
    limit: int = 20,
    company_id: uuid.UUID = Depends(get_current_company_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Get CEO attention notifications (subset of all notifications)."""
    # Get CEO user
    ceo = db.query(User).filter(
        User.company_id == company_id,
        User.role == "ceo"
    ).first()
    if not ceo:
        ceo = db.query(User).filter(User.company_id == company_id).first()

    if not ceo:
        return {"notifications": [], "unread_count": 0}

    notifications = reminder_service.get_user_notifications(db, ceo.id, unread_only, limit)
    # Filter to CEO attention types only
    ceo_notifications = [
        n for n in notifications
        if n.type in ("ceo_attention", "payable_overdue", "receivable_overdue", "payable_due_today", "receivable_due_today")
    ]

    return {
        "notifications": ceo_notifications,
        "unread_count": len([n for n in ceo_notifications if not n.is_read]),
    }