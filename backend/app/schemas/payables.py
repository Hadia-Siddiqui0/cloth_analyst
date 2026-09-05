import uuid
from datetime import date
from pydantic import BaseModel


class SupplierOut(BaseModel):
    id: uuid.UUID
    name: str
    contact_info: str | None
    payment_terms_days: int | None

    class Config:
        from_attributes = True


class PayableCreate(BaseModel):
    supplier_id: uuid.UUID
    purchase_id: uuid.UUID | None = None
    reference: str | None = None
    amount: float
    due_date: date | None = None


class PayableMarkPaid(BaseModel):
    paid_date: date | None = None  # defaults to today if omitted


class PayableOut(BaseModel):
    id: uuid.UUID
    supplier_id: uuid.UUID
    supplier_name: str
    purchase_id: uuid.UUID | None
    reference: str | None
    amount: float
    due_date: date | None
    paid_date: date | None
    status: str


class PayablesSummary(BaseModel):
    total_outstanding: float
    total_overdue: float
    overdue_count: int
    outstanding_count: int