"""
All Command Center calculations live here, not in api/dashboard.py.
Same reason as always: this needs to be callable from the AI Analyst
and from anomaly detection later without duplicating logic.
"""
import uuid
from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.production_run import ProductionRun
from app.models.contractor_ledger import ContractorLedgerEntry
from app.models.expense import Expense


def get_kpis(db: Session, company_id: uuid.UUID) -> dict:
    row = (
        db.query(
            func.sum(ProductionRun.revenue_total).label("revenue"),
            func.sum(ProductionRun.cost_total).label("cost"),
            func.sum(ProductionRun.profit).label("profit"),
            func.min(ProductionRun.date).label("period_start"),
            func.max(ProductionRun.date).label("period_end"),
            func.count(ProductionRun.id).label("record_count"),
        )
        .filter(ProductionRun.company_id == company_id)
        .first()
    )

    latest_balance = (
        db.query(ContractorLedgerEntry.running_balance)
        .filter(ContractorLedgerEntry.company_id == company_id)
        .order_by(ContractorLedgerEntry.date.desc())
        .first()
    )

    total_expenses = (
        db.query(func.sum(Expense.amount_used))
        .filter(Expense.company_id == company_id)
        .scalar()
    )

    return {
        "total_revenue": float(row.revenue or 0),
        "total_cost": float(row.cost or 0),
        "total_profit": float(row.profit or 0),
        "contractor_balance": float(latest_balance[0]) if latest_balance and latest_balance[0] is not None else None,
        "total_expenses": float(total_expenses) if total_expenses is not None else None,
        "period_start": row.period_start,
        "period_end": row.period_end,
        "record_count": row.record_count or 0,
    }


def get_daily_trend(db: Session, company_id: uuid.UUID, stream: str | None = None) -> list[dict]:
    q = db.query(
        ProductionRun.date,
        func.sum(ProductionRun.cost_total).label("cost"),
        func.sum(ProductionRun.revenue_total).label("revenue"),
        func.sum(ProductionRun.profit).label("profit"),
    ).filter(ProductionRun.company_id == company_id)

    if stream:
        q = q.filter(ProductionRun.stream == stream)

    q = q.group_by(ProductionRun.date).order_by(ProductionRun.date)
    return [
        {"date": r.date, "cost": float(r.cost or 0), "revenue": float(r.revenue or 0), "profit": float(r.profit or 0)}
        for r in q.all()
    ]
