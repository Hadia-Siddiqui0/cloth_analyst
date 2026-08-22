import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_company_id
from app.db.session import get_db
from app.schemas.dashboard import (
    DashboardKPIs, TrendPoint, WeeklyProfitPoint, WhyAnalysis,
    ProductProfitability, LowestMarginProduct, ContractorSummary,
)
from app.services import dashboard_service

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/kpis", response_model=DashboardKPIs)
def kpis(
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
):
    return dashboard_service.get_kpis(db, company_id)


@router.get("/trend", response_model=list[TrendPoint])
def trend(
    stream: str | None = None,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
):
    return dashboard_service.get_daily_trend(db, company_id, stream)


@router.get("/weekly-profit", response_model=list[WeeklyProfitPoint])
def weekly_profit(
    stream: str = "self_made",
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
):
    return dashboard_service.get_weekly_profit(db, company_id, stream)


@router.get("/why", response_model=WhyAnalysis | None)
def why_analysis(
    stream: str = "self_made",
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
):
    return dashboard_service.get_why_analysis(db, company_id, stream)


@router.get("/products", response_model=list[ProductProfitability])
def products(
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
):
    return dashboard_service.get_product_profitability(db, company_id)


@router.get("/products/lowest-margin", response_model=LowestMarginProduct | None)
def lowest_margin_product(
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
):
    return dashboard_service.get_lowest_margin_product(db, company_id)


@router.get("/expenses/categories", response_model=dict[str, float])
def expense_categories(
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
):
    return dashboard_service.get_expense_categories(db, company_id)


@router.get("/contractor", response_model=ContractorSummary)
def contractor_summary(
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
):
    return dashboard_service.get_contractor_summary(db, company_id)