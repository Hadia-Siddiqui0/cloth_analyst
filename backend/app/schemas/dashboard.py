from datetime import date
from pydantic import BaseModel


class DashboardKPIs(BaseModel):
    total_revenue: float
    total_cost: float
    total_profit: float
    contractor_balance: float | None
    total_expenses: float | None
    period_start: date | None
    period_end: date | None
    record_count: int


class ProductProfitability(BaseModel):
    cloth_type: str
    total_cost_per_piece: float | None
    sale_price_per_piece: float | None
    profit_per_piece: float | None
    is_current: bool

    class Config:
        from_attributes = True


class TrendPoint(BaseModel):
    date: date
    cost: float | None
    revenue: float | None
    profit: float | None


class WeeklyProfitPoint(BaseModel):
    week_start: date
    label: str
    profit: float


class WhyAnalysis(BaseModel):
    latest_week: str
    prior_week: str
    comparison_label: str
    revenue_change: float
    cost_change: float
    profit_change: float
    top_cost_driver: str | None
    top_cost_driver_change: float | None
    flat_week: bool


class LowestMarginProduct(BaseModel):
    cloth_type: str
    profit_per_piece: float | None
    is_losing_money: bool


class ContractorSummary(BaseModel):
    balance: float | None
    trend: str | None