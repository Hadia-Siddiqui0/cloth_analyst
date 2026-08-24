"""
Receivables calculations live here, not in api/receivables.py -- same
reason as dashboard_service.py: this needs to be callable from alerts
and the AI Analyst later without duplicating logic.

Status is computed fresh on every read rather than trusted from the
stored column, since "overdue" depends on comparing against today's
date -- a payment stored as "upcoming" yesterday needs to show as
"overdue" today without anything having touched that row. The stored
status column (see Payment model) is kept in sync as a side effect of
listing, so anything querying the raw table directly still gets a
reasonably fresh value, but this service is the source of truth.
"""
import uuid
from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.payment import Payment, PaymentStatus


def compute_status(due_date: date | None, paid_date: date | None, today: date | None = None) -> PaymentStatus:
    if paid_date is not None:
        return PaymentStatus.PAID
    if due_date is None:
        return PaymentStatus.UPCOMING

    today = today or date.today()
    days_until_due = (due_date - today).days

    if days_until_due < 0:
        return PaymentStatus.OVERDUE
    if days_until_due == 0:
        return PaymentStatus.DUE_TODAY
    if days_until_due <= 3:
        return PaymentStatus.DUE_SOON
    return PaymentStatus.UPCOMING


def get_receivables(db: Session, company_id: uuid.UUID) -> list[dict]:
    rows = (
        db.query(Payment, Customer.name.label("customer_name"))
        .join(Customer, Payment.customer_id == Customer.id)
        .filter(Payment.company_id == company_id)
        .order_by(Payment.due_date.asc().nulls_last())
        .all()
    )

    results = []
    today = date.today()
    for payment, customer_name in rows:
        status = compute_status(payment.due_date, payment.paid_date, today)
        if status != payment.status:
            payment.status = status  # keep the stored column in sync
        results.append({
            "id": payment.id,
            "customer_id": payment.customer_id,
            "customer_name": customer_name,
            "amount": float(payment.amount),
            "due_date": payment.due_date,
            "paid_date": payment.paid_date,
            "status": status.value,
        })
    db.commit()
    return results


def get_receivables_summary(db: Session, company_id: uuid.UUID) -> dict:
    receivables = get_receivables(db, company_id)
    outstanding = [r for r in receivables if r["status"] != "paid"]
    overdue = [r for r in outstanding if r["status"] == "overdue"]

    return {
        "total_outstanding": round(sum(r["amount"] for r in outstanding)),
        "total_overdue": round(sum(r["amount"] for r in overdue)),
        "overdue_count": len(overdue),
        "outstanding_count": len(outstanding),
    }


def get_customers(db: Session, company_id: uuid.UUID) -> list[Customer]:
    return db.query(Customer).filter(Customer.company_id == company_id).order_by(Customer.name).all()