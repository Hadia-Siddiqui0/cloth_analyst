import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_company_id
from app.db.session import get_db
from app.models.customer import Customer
from app.models.payment import Payment, PaymentStatus
from app.schemas.receivables import (
    CustomerCreate, CustomerOut, PaymentCreate, PaymentMarkPaid,
    ReceivableOut, ReceivablesSummary,
)
from app.services import receivables_service

router = APIRouter(prefix="/api/receivables", tags=["receivables"])


@router.post("/customers", response_model=CustomerOut)
def create_customer(
    payload: CustomerCreate,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
):
    customer = Customer(company_id=company_id, **payload.model_dump())
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@router.get("/customers", response_model=list[CustomerOut])
def list_customers(
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
):
    return receivables_service.get_customers(db, company_id)


@router.post("/payments", response_model=ReceivableOut)
def create_payment(
    payload: PaymentCreate,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
):
    customer = db.query(Customer).filter(Customer.id == payload.customer_id, Customer.company_id == company_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    status = receivables_service.compute_status(payload.due_date, None)
    payment = Payment(
        company_id=company_id,
        customer_id=payload.customer_id,
        amount=payload.amount,
        due_date=payload.due_date,
        status=status,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return {
        "id": payment.id,
        "customer_id": payment.customer_id,
        "customer_name": customer.name,
        "amount": float(payment.amount),
        "due_date": payment.due_date,
        "paid_date": payment.paid_date,
        "status": status.value,
    }


@router.get("/payments", response_model=list[ReceivableOut])
def list_payments(
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
):
    return receivables_service.get_receivables(db, company_id)


@router.patch("/payments/{payment_id}/mark-paid", response_model=ReceivableOut)
def mark_paid(
    payment_id: uuid.UUID,
    payload: PaymentMarkPaid,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
):
    payment = db.query(Payment).filter(Payment.id == payment_id, Payment.company_id == company_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    payment.paid_date = payload.paid_date or date.today()
    payment.status = PaymentStatus.PAID
    db.commit()

    customer = db.query(Customer).filter(Customer.id == payment.customer_id).first()
    return {
        "id": payment.id,
        "customer_id": payment.customer_id,
        "customer_name": customer.name if customer else "",
        "amount": float(payment.amount),
        "due_date": payment.due_date,
        "paid_date": payment.paid_date,
        "status": PaymentStatus.PAID.value,
    }


@router.get("/summary", response_model=ReceivablesSummary)
def summary(
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
):
    return receivables_service.get_receivables_summary(db, company_id)