"""
All Command Center calculations live here, not in api/dashboard.py.
Same reason as always: this needs to be callable from the AI Analyst
and from anomaly detection later without duplicating logic.

The weekly-profit / why-analysis / lowest-margin logic here mirrors what
was first proven out in scripts/regenerate_dashboard.py against the real
sample file -- ported here so the live app and the standalone demo
script share one source of truth instead of two copies that can drift
apart. If you change the logic, change it in one place and keep the
other in sync (or better, have the script import from here once the
app's dependencies are installed in the same environment it runs in).
"""
import uuid
from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.production_run import ProductionRun, ProductionStream
from app.models.product import Product
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


def _week_start(d: date) -> date:
    """ISO-week Monday, matching pandas' default W-SUN resample anchor
    closely enough for display purposes -- exact anchor day doesn't
    matter here since it's only used to group and label."""
    return d - timedelta(days=d.weekday())


def get_weekly_profit(db: Session, company_id: uuid.UUID, stream: str = "self_made") -> list[dict]:
    """One point per week for the current production stream -- this is
    what the dashboard's bar chart reads. Defaults to self_made since
    that's the customer's confirmed current operation; pass stream=None
    to include everything."""
    q = db.query(ProductionRun.date, ProductionRun.profit).filter(ProductionRun.company_id == company_id)
    if stream:
        q = q.filter(ProductionRun.stream == stream)

    weekly_totals: dict[date, float] = defaultdict(float)
    for row in q.all():
        if row.date is None or row.profit is None:
            continue
        weekly_totals[_week_start(row.date)] += float(row.profit)

    weeks = sorted(w for w, total in weekly_totals.items() if abs(total) > 0.01)
    return [{"week_start": w, "label": f"Week of {w.strftime('%b %d')}", "profit": round(weekly_totals[w])} for w in weeks]


def get_why_analysis(db: Session, company_id: uuid.UUID, stream: str = "self_made") -> dict | None:
    """Compares two weeks and attributes the cost movement to whichever
    overhead category moved the most, using the cost_breakdown captured
    per row. Falls back to the most significant swing anywhere in the
    data if the most recent two weeks are flat, same logic as the demo
    script, and for the same reason: naming a "top driver" when nothing
    actually changed would be presenting noise as an explanation."""
    q = db.query(ProductionRun).filter(ProductionRun.company_id == company_id)
    if stream:
        q = q.filter(ProductionRun.stream == stream)
    rows = q.all()
    if not rows:
        return None

    weekly_revenue: dict[date, float] = defaultdict(float)
    weekly_cost: dict[date, float] = defaultdict(float)
    weekly_profit: dict[date, float] = defaultdict(float)
    weekly_breakdown: dict[date, dict] = defaultdict(lambda: defaultdict(float))

    for r in rows:
        if r.date is None:
            continue
        w = _week_start(r.date)
        weekly_revenue[w] += float(r.revenue_total or 0)
        weekly_cost[w] += float(r.cost_total or 0)
        weekly_profit[w] += float(r.profit or 0)
        if isinstance(r.cost_breakdown, dict):
            for cat, val in r.cost_breakdown.items():
                if isinstance(val, (int, float)):
                    weekly_breakdown[w][cat] += val

    weeks = sorted(w for w in weekly_profit if abs(weekly_profit[w]) > 0.01)
    if len(weeks) < 2:
        return None

    latest, prior = weeks[-1], weeks[-2]
    comparison_label = "most recent two weeks"

    if abs(weekly_profit[latest] - weekly_profit[prior]) < 1 and len(weeks) > 2:
        best_pair, best_swing = None, 0
        for i in range(1, len(weeks)):
            swing = abs(weekly_profit[weeks[i]] - weekly_profit[weeks[i - 1]])
            if swing > best_swing:
                best_swing, best_pair = swing, i
        if best_pair is not None and best_swing > 1:
            latest, prior = weeks[best_pair], weeks[best_pair - 1]
            comparison_label = "most significant week-over-week change found in your data"

    revenue_change = weekly_revenue[latest] - weekly_revenue[prior]
    cost_change = weekly_cost[latest] - weekly_cost[prior]
    profit_change = weekly_profit[latest] - weekly_profit[prior]
    flat_week = abs(revenue_change) < 1 and abs(cost_change) < 1

    top_driver, top_driver_change = None, None
    if not flat_week:
        all_cats = set(weekly_breakdown[latest]) | set(weekly_breakdown[prior])
        changes = {c: weekly_breakdown[latest].get(c, 0) - weekly_breakdown[prior].get(c, 0) for c in all_cats}
        meaningful = {c: v for c, v in changes.items() if abs(v) > 1}
        if meaningful:
            top_driver, top_driver_change = max(meaningful.items(), key=lambda kv: abs(kv[1]))

    return {
        "latest_week": latest.strftime("%b %d"),
        "prior_week": prior.strftime("%b %d"),
        "comparison_label": comparison_label,
        "revenue_change": round(revenue_change),
        "cost_change": round(cost_change),
        "profit_change": round(profit_change),
        "top_cost_driver": top_driver.strip() if top_driver else None,
        "top_cost_driver_change": round(top_driver_change) if top_driver_change is not None else None,
        "flat_week": flat_week,
    }


def get_product_profitability(db: Session, company_id: uuid.UUID) -> list[dict]:
    products = db.query(Product).filter(Product.company_id == company_id).all()
    return [
        {
            "cloth_type": p.cloth_type,
            "total_cost_per_piece": float(p.total_cost_per_piece) if p.total_cost_per_piece is not None else None,
            "sale_price_per_piece": float(p.sale_price_per_piece) if p.sale_price_per_piece is not None else None,
            "profit_per_piece": float(p.profit_per_piece) if p.profit_per_piece is not None else None,
            "is_current": p.source == "verified",
        }
        for p in products
    ]


def get_lowest_margin_product(db: Session, company_id: uuid.UUID) -> dict | None:
    products = get_product_profitability(db, company_id)
    if not products:
        return None
    losing = [p for p in products if (p["profit_per_piece"] or 0) < 0]
    pool = losing if losing else products
    lowest = min(pool, key=lambda p: p["profit_per_piece"] or 0)
    return {
        "cloth_type": lowest["cloth_type"],
        "profit_per_piece": lowest["profit_per_piece"],
        "is_losing_money": (lowest["profit_per_piece"] or 0) < 0,
    }


def get_expense_categories(db: Session, company_id: uuid.UUID) -> dict:
    rows = (
        db.query(Expense.category, func.sum(Expense.amount_used).label("total"))
        .filter(Expense.company_id == company_id)
        .group_by(Expense.category)
        .order_by(func.sum(Expense.amount_used).desc())
        .all()
    )
    return {r.category or "Misc/Other": round(float(r.total or 0)) for r in rows}


def get_contractor_summary(db: Session, company_id: uuid.UUID) -> dict:
    entries = (
        db.query(ContractorLedgerEntry)
        .filter(ContractorLedgerEntry.company_id == company_id, ContractorLedgerEntry.running_balance.isnot(None))
        .order_by(ContractorLedgerEntry.date)
        .all()
    )
    if not entries:
        return {"balance": None, "trend": None}

    balance = float(entries[-1].running_balance)
    trend = None
    if len(entries) > 1:
        first_balance = float(entries[0].running_balance)
        if balance < first_balance:
            trend = "down"
        elif balance > first_balance:
            trend = "up"
    return {"balance": round(balance), "trend": trend}