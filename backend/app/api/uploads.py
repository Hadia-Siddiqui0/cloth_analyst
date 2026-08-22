import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_company_id
from app.db.session import get_db
from app.models.upload import Upload, UploadStatus
from app.models.production_run import ProductionRun, ProductionStream
from app.models.product import Product
from app.models.contractor_ledger import ContractorLedgerEntry
from app.models.expense import Expense
from app.services.ingestion_service import detect_and_parse_workbook, categorize_expense

router = APIRouter(prefix="/api/uploads", tags=["uploads"])


@router.post("/")
def upload_file(
    file: UploadFile = File(...),
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
):
    """Step 1-3 of the ingestion flow: store the file, parse every sheet,
    return a preview + mapping report. Nothing is written to the
    business tables yet -- that happens in /confirm, so a human can
    review the auto-detected mapping first (see Phase 2 of the roadmap:
    the mapping engine is the riskiest piece, don't let it write blind)."""
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_path = upload_dir / f"{uuid.uuid4()}_{file.filename}"

    with stored_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    parsed_sheets = detect_and_parse_workbook(str(stored_path))

    upload = Upload(
        company_id=company_id,
        original_filename=file.filename,
        stored_path=str(stored_path),
        status=UploadStatus.UPLOADED,
        column_mapping={r.sheet_name: r.column_mapping for r in parsed_sheets},
        validation_issues={r.sheet_name: r.warnings for r in parsed_sheets if r.warnings},
    )
    db.add(upload)
    db.commit()
    db.refresh(upload)

    return {
        "upload_id": upload.id,
        "sheets": [
            {
                "sheet_name": r.sheet_name,
                "detected_type": r.sheet_type,
                "row_count": len(r.dataframe),
                "columns_mapped": r.column_mapping,
                "warnings": r.warnings,
                "preview": r.dataframe.head(5).fillna("").to_dict(orient="records"),
            }
            for r in parsed_sheets
        ],
    }


@router.post("/{upload_id}/confirm")
def confirm_import(
    upload_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
):
    """Step 6: re-parse (mapping was already reviewed by the user via the
    frontend at this point) and actually write rows into the business
    tables, tagged with this upload's id for full traceability."""
    upload = db.query(Upload).filter(Upload.id == upload_id, Upload.company_id == company_id).first()
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")

    parsed_sheets = detect_and_parse_workbook(upload.stored_path)
    rows_imported = 0

    for result in parsed_sheets:
        df = result.dataframe
        if df.empty:
            continue

        if result.sheet_type == "daily_production_log":
            stream = ProductionStream.UNSPECIFIED
            name_lower = result.sheet_name.lower()
            if "self" in name_lower:
                stream = ProductionStream.SELF_MADE
            elif "cmt" in name_lower:
                stream = ProductionStream.CMT

            for _, row in df.iterrows():
                db.add(ProductionRun(
                    company_id=company_id,
                    date=row.get("date"),
                    stream=stream,
                    article_label=str(row.get("article")) if pd_notna(row.get("article")) else None,
                    quantity=row.get("quantity"),
                    cost_total=row.get("cost_total"),
                    sale_price_piece=row.get("sale_price_piece"),
                    revenue_total=row.get("revenue_total"),
                    profit=row.get("profit"),
                    source_upload_id=upload.id,
                    source_sheet=result.sheet_name,
                ))
                rows_imported += 1

        elif result.sheet_type == "article_costing":
            for _, row in df.iterrows():
                db.add(Product(
                    company_id=company_id,
                    cloth_type=row.get("cloth_type"),
                    article_code=str(row.get("article_code")) if pd_notna(row.get("article_code")) else None,
                    cost_per_meter=row.get("cost_per_meter"),
                    cloth_meters_per_piece=row.get("cloth_meters_per_piece"),
                    cloth_cost_per_piece=row.get("cloth_cost_per_piece"),
                    stitching_cost_per_piece=row.get("stitching_cost_per_piece"),
                    embroidery_cost_per_piece=row.get("embroidery_cost_per_piece"),
                    washing_cost_per_piece=row.get("washing_cost_per_piece"),
                    total_cost_per_piece=row.get("total_cost_per_piece"),
                    sale_price_per_piece=row.get("sale_price_per_piece"),
                    profit_per_piece=row.get("profit_per_piece"),
                    source="verified",
                ))
                rows_imported += 1

        elif result.sheet_type == "ledger":
            name_lower = result.sheet_name.lower()
            cols = set(df.columns)
            if "contractor" in name_lower or "amount" in cols and "receive" in cols:
                for _, row in df.iterrows():
                    db.add(ContractorLedgerEntry(
                        company_id=company_id,
                        date=row.get("date"),
                        amount_billed=row.get("amount"),
                        amount_paid=row.get("receive"),
                        running_balance=row.get("balance"),
                        source_upload_id=upload.id,
                    ))
                    rows_imported += 1
            else:
                for _, row in df.iterrows():
                    description = row.get("description", "")
                    db.add(Expense(
                        company_id=company_id,
                        date=row.get("date"),
                        description=description,
                        category=categorize_expense(description),
                        amount_received=row.get("amount recive") or row.get("amount received"),
                        amount_used=row.get("used"),
                        running_balance=row.get("balance"),
                        source_upload_id=upload.id,
                    ))
                    rows_imported += 1

    upload.status = UploadStatus.IMPORTED
    upload.rows_imported = rows_imported
    db.commit()

    return {"upload_id": upload.id, "rows_imported": rows_imported, "status": "imported"}


def pd_notna(v):
    import pandas as pd
    return pd.notna(v)
