"""
Payables calculations live here, not in api/payables.py -- same
reason as dashboard_service.py: this needs to be callable from alerts
and the AI Analyst later without duplicating logic.

Status is computed fresh on every read rather than trusted from the
stored column, since "overdue" depends on comparing against today's
date -- a payable stored as "upcoming" yesterday needs to show as
"overdue" today without anything having touched that row. The stored
status column (see Payable model) is kept in sync as a side effect of
listing, so anything querying the raw table directly still gets a
reasonably fresh value, but this service is the source of truth.
"""
import uuid
from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.supplier import Supplier
from app.models.payable import Payable, PayableStatus


def compute_status(due_date: date | None, paid_date: date | None, today: date | None = None) -> PayableStatus:
    """Compute payable status based on due_date and paid_date.

    Mirrors the receivables compute_status logic exactly:
    - PAID if paid_date is set
    - UPCOMING if no due_date
    - OVERDUE if due_date < today
    - DUE_TODAY if due_date == today
    - DUE_SOON if due_date within 3 days
    - UPCOMING otherwise
    """
    if paid_date is not None:
        return PayableStatus.PAID
    if due_date is None:
        return PayableStatus.UPCOMING

    today = today or date.today()
    days_until_due = (due_date - today).days

    if days_until_due < 0:
        return PayableStatus.OVERDUE
    if days_until_due == 0:
        return PayableStatus.DUE_TODAY
    if days_until_due <= 3:
        return PayableStatus.DUE_SOON
    return PayableStatus.UPCOMING


def get_payables(db: Session, company_id: uuid.UUID) -> list[dict]:
    """Get all payables for a company with computed status."""
    rows = (
        db.query(Payable, Supplier.name.label("supplier_name"))
        .join(Supplier, Payable.supplier_id == Supplier.id)
        .filter(Payable.company_id == company_id)
        .order_by(Payable.due_date.asc().nulls_last())
        .all()
    )

    results = []
    today = date.today()
    for payable, supplier_name in rows:
        status = compute_status(payable.due_date, payable.paid_date, today)
        if status != payable.status:
            payable.status = status  # keep the stored column in sync
        results.append({
            "id": payable.id,
            "supplier_id": payable.supplier_id,
            "supplier_name": supplier_name,
            "purchase_id": payable.purchase_id,
            "reference": payable.reference,
            "amount": float(payable.amount),
            "due_date": payable.due_date,
            "paid_date": payable.paid_date,
            "status": status.value,
        })
    db.commit()
    return results


def get_payables_summary(db: Session, company_id: uuid.UUID) -> dict:
    """Get payables summary for a company."""
    payables = get_payables(db, company_id)
    outstanding = [p for p in payables if p["status"] != "paid"]
    overdue = [p for p in outstanding if p["status"] == "overdue"]

    return {
        "total_outstanding": round(sum(p["amount"] for p in outstanding), 2),
        "total_overdue": round(sum(p["amount"] for p in overdue), 2),
        "overdue_count": len(overdue),
        "outstanding_count": len(outstanding),
    }


def get_suppliers(db: Session, company_id: uuid.UUID) -> list[Supplier]:
    """Get all suppliers for a company."""
    return db.query(Supplier).filter(Supplier.company_id == company_id).order_by(Supplier.name).all()