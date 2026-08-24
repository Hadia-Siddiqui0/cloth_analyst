import shutil
import uuid
from pathlib import Path

import pandas as pd
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


@router.delete("/reset")
def reset_company_data(
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
):
    """Deletes every imported business record for the CURRENT company
    only (never touches other companies -- company_id comes from the
    verified JWT, same as every other endpoint here). For testing: since
    uploads are additive (each confirm ADDS rows, never replaces prior
    ones -- correct for a real business uploading new periods over time,
    confusing when repeatedly re-testing the same file), this gives a
    clean slate without creating a new account each time.

    Deliberately does NOT delete the company or user -- just the
    imported data -- so you keep your login."""
    deleted_counts = {
        "production_runs": db.query(ProductionRun).filter(ProductionRun.company_id == company_id).delete(),
        "products": db.query(Product).filter(Product.company_id == company_id).delete(),
        "contractor_ledger_entries": db.query(ContractorLedgerEntry).filter(ContractorLedgerEntry.company_id == company_id).delete(),
        "expenses": db.query(Expense).filter(Expense.company_id == company_id).delete(),
        "uploads": db.query(Upload).filter(Upload.company_id == company_id).delete(),
    }
    db.commit()
    return {"status": "reset", "deleted": deleted_counts}


def clean(v):
    """Convert any pandas 'missing' representation (NaN, NaT, None, pd.NA)
    to a plain Python None, so it becomes a real SQL NULL instead of the
    literal string "NaN"/"NaT" that a DB driver can't parse.

    This matters specifically because a single spreadsheet column can end
    up with a mixed dtype -- e.g. mostly numbers but pandas infers NaT
    (its 'missing' value for dates) for one blank cell instead of NaN --
    and that inconsistency is invisible until it hits the database. Every
    value pulled from a DataFrame row goes through this before being
    handed to SQLAlchemy, not just the ones that looked suspicious in
    testing."""
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        # pd.isna() raises on some inputs (e.g. certain array-likes) --
        # if we get here, v isn't a recognizable NA value, so keep it.
        pass
    return v


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
    tables, tagged with this upload's id for full traceability.

    IMPORTANT: this REPLACES the company's existing business data rather
    than adding to it. Confirmed by testing: re-uploading the same file
    repeatedly was silently duplicating every row each time (so KPIs
    kept shifting), and uploading a genuinely different file still
    showed old data mixed in from prior uploads. For a real business
    doing period-over-period uploads (January, then February, ...) this
    replace-everything approach is too blunt -- that needs proper
    period/versioning logic later -- but for now it makes every import
    deterministic: the same file always produces the same result, and a
    new file never overlaps with a previous one.

    The delete + re-insert both happen in this one transaction (single
    commit at the end), so if parsing/inserting the new file fails
    partway through, the rollback restores the old data instead of
    leaving the company with nothing."""
    upload = db.query(Upload).filter(Upload.id == upload_id, Upload.company_id == company_id).first()
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")

    db.query(ProductionRun).filter(ProductionRun.company_id == company_id).delete()
    db.query(Product).filter(Product.company_id == company_id).delete()
    db.query(ContractorLedgerEntry).filter(ContractorLedgerEntry.company_id == company_id).delete()
    db.query(Expense).filter(Expense.company_id == company_id).delete()

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
                article = clean(row.get("article"))
                db.add(ProductionRun(
                    company_id=company_id,
                    date=clean(row.get("date")),
                    stream=stream,
                    article_label=str(article) if article is not None else None,
                    quantity=clean(row.get("quantity")),
                    cost_total=clean(row.get("cost_total")),
                    sale_price_piece=clean(row.get("sale_price_piece")),
                    revenue_total=clean(row.get("revenue_total")),
                    profit=clean(row.get("profit")),
                    cost_breakdown=row.get("cost_breakdown") if isinstance(row.get("cost_breakdown"), dict) else None,
                    source_upload_id=upload.id,
                    source_sheet=result.sheet_name,
                ))
                rows_imported += 1

        elif result.sheet_type == "article_costing":
            for _, row in df.iterrows():
                article_code = clean(row.get("article_code"))
                db.add(Product(
                    company_id=company_id,
                    cloth_type=clean(row.get("cloth_type")),
                    article_code=str(article_code) if article_code is not None else None,
                    cost_per_meter=clean(row.get("cost_per_meter")),
                    cloth_meters_per_piece=clean(row.get("cloth_meters_per_piece")),
                    cloth_cost_per_piece=clean(row.get("cloth_cost_per_piece")),
                    stitching_cost_per_piece=clean(row.get("stitching_cost_per_piece")),
                    embroidery_cost_per_piece=clean(row.get("embroidery_cost_per_piece")),
                    washing_cost_per_piece=clean(row.get("washing_cost_per_piece")),
                    total_cost_per_piece=clean(row.get("total_cost_per_piece")),
                    sale_price_per_piece=clean(row.get("sale_price_per_piece")),
                    profit_per_piece=clean(row.get("profit_per_piece")),
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
                        date=clean(row.get("date")),
                        amount_billed=clean(row.get("amount")),
                        amount_paid=clean(row.get("receive")),
                        running_balance=clean(row.get("balance")),
                        source_upload_id=upload.id,
                    ))
                    rows_imported += 1
            else:
                for _, row in df.iterrows():
                    description = clean(row.get("description")) or ""
                    db.add(Expense(
                        company_id=company_id,
                        date=clean(row.get("date")),
                        description=description,
                        category=categorize_expense(description),
                        amount_received=clean(row.get("amount recive")) or clean(row.get("amount received")),
                        amount_used=clean(row.get("used")),
                        running_balance=clean(row.get("balance")),
                        source_upload_id=upload.id,
                    ))
                    rows_imported += 1

    upload.status = UploadStatus.IMPORTED
    upload.rows_imported = rows_imported
    db.commit()

    return {"upload_id": upload.id, "rows_imported": rows_imported, "status": "imported"}