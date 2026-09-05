import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_company_id
from app.db.session import get_db
from app.models.supplier import Supplier
from app.models.payable import Payable, PayableStatus
from app.schemas.payables import (
    PayableCreate, PayableMarkPaid, PayableOut, PayablesSummary, SupplierOut,
)
from app.services import payables_service

router = APIRouter(prefix="/api/payables", tags=["payables"])


@router.get("/suppliers", response_model=list[SupplierOut])
def list_suppliers(
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
):
    return payables_service.get_suppliers(db, company_id)


@router.post("/payables", response_model=PayableOut)
def create_payable(
    payload: PayableCreate,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
):
    supplier = db.query(Supplier).filter(Supplier.id == payload.supplier_id, Supplier.company_id == company_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    if payload.purchase_id:
        purchase = db.query(Supplier).filter(Supplier.id == payload.purchase_id, Supplier.company_id == company_id).first()
        if not purchase:
            raise HTTPException(status_code=404, detail="Purchase not found")

    status = payables_service.compute_status(payload.due_date, None)
    payable = Payable(
        company_id=company_id,
        supplier_id=payload.supplier_id,
        purchase_id=payload.purchase_id,
        reference=payload.reference,
        amount=payload.amount,
        due_date=payload.due_date,
        status=status,
    )
    db.add(payable)
    db.commit()
    db.refresh(payable)
    return {
        "id": payable.id,
        "supplier_id": payable.supplier_id,
        "supplier_name": supplier.name,
        "purchase_id": payable.purchase_id,
        "reference": payable.reference,
        "amount": float(payable.amount),
        "due_date": payable.due_date,
        "paid_date": payable.paid_date,
        "status": status.value,
    }


@router.get("/payables", response_model=list[PayableOut])
def list_payables(
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
):
    return payables_service.get_payables(db, company_id)


@router.patch("/payables/{payable_id}/mark-paid", response_model=PayableOut)
def mark_paid(
    payable_id: uuid.UUID,
    payload: PayableMarkPaid,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
):
    payable = db.query(Payable).filter(Payable.id == payable_id, Payable.company_id == company_id).first()
    if not payable:
        raise HTTPException(status_code=404, detail="Payable not found")

    payable.paid_date = payload.paid_date or date.today()
    payable.status = PayableStatus.PAID
    db.commit()

    supplier = db.query(Supplier).filter(Supplier.id == payable.supplier_id).first()
    return {
        "id": payable.id,
        "supplier_id": payable.supplier_id,
        "supplier_name": supplier.name if supplier else "",
        "purchase_id": payable.purchase_id,
        "reference": payable.reference,
        "amount": float(payable.amount),
        "due_date": payable.due_date,
        "paid_date": payable.paid_date,
        "status": PayableStatus.PAID.value,
    }


@router.get("/summary", response_model=PayablesSummary)
def summary(
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
):
    return payables_service.get_payables_summary(db, company_id)