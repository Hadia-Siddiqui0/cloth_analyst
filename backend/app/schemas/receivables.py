import uuid
from datetime import date
from pydantic import BaseModel


class CustomerCreate(BaseModel):
    name: str
    customer_type: str | None = None  # "shop" | "wholesaler" | "direct"
    contact_info: str | None = None
    credit_terms_days: int | None = None


class CustomerOut(BaseModel):
    id: uuid.UUID
    name: str
    customer_type: str | None
    contact_info: str | None
    credit_terms_days: int | None

    class Config:
        from_attributes = True


class PaymentCreate(BaseModel):
    customer_id: uuid.UUID
    amount: float
    due_date: date | None = None


class PaymentMarkPaid(BaseModel):
    paid_date: date | None = None  # defaults to today if omitted


class ReceivableOut(BaseModel):
    id: uuid.UUID
    customer_id: uuid.UUID
    customer_name: str
    amount: float
    due_date: date | None
    paid_date: date | None
    status: str


class ReceivablesSummary(BaseModel):
    total_outstanding: float
    total_overdue: float
    overdue_count: int
    outstanding_count: int