import logging
import os
import shutil
import uuid
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Body, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_company_id, require_role
from app.db.session import get_db
from app.models.upload import Upload, UploadStatus
from app.models.production_run import ProductionRun, ProductionStream
from app.models.product import Product
from app.models.contractor_ledger import ContractorLedgerEntry
from app.models.expense import Expense
from app.services.ingestion_service import detect_and_parse_workbook, categorize_expense
from app.services.ocr_service import process_register_image, OCRResult
from app.services.universal_ingestion import (
    parse_workbook_universal,
    parse_workbook_with_mappings,
    get_sheet_summary,
    apply_user_mappings,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/uploads", tags=["uploads"])

# Allowed file extensions
ALLOWED_EXTENSIONS = {
    # Excel formats
    ".xlsx", ".xls",
    # CSV
    ".csv",
    # Image formats for OCR
    ".jpg", ".jpeg", ".png", ".webp", ".tiff", ".bmp",
}

# Maximum file size (in bytes)
MAX_FILE_SIZE = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024


def _sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal and other attacks."""
    # Remove any path separators
    filename = os.path.basename(filename)
    # Remove null bytes
    filename = filename.replace("\x00", "")
    # Remove any non-printable characters
    filename = "".join(c for c in filename if c.isprintable())
    # Limit length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:250] + ext
    return filename or "uploaded_file"


def _validate_file_signature(file_path: str, expected_type: str) -> bool:
    """Validate file type by checking file signature (magic numbers)."""
    try:
        with open(file_path, "rb") as f:
            header = f.read(8)

        # Excel (.xlsx) - ZIP signature (PK)
        if expected_type in {".xlsx", ".xls"}:
            # xlsx files are ZIP archives
            if header[:4] == b'PK\x03\x04':
                return True
            # Older .xls files have different signature
            if header[:8] == b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1':
                return True
            return False

        # CSV - check if text-based
        if expected_type == ".csv":
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    f.read(1024)
                return True
            except UnicodeDecodeError:
                try:
                    with open(file_path, "r", encoding="latin-1") as f:
                        f.read(1024)
                    return True
                except:
                    return False

        # Images
        if expected_type in {".jpg", ".jpeg"}:
            return header[:2] == b'\xff\xd8'
        if expected_type == ".png":
            return header[:8] == b'\x89PNG\r\n\x1a\n'
        if expected_type == ".webp":
            return header[:4] == b'RIFF' and header[4:8] == b'WEBP'
        if expected_type in {".tiff", ".tif"}:
            return header[:2] in (b'II', b'MM')
        if expected_type == ".bmp":
            return header[:2] == b'BM'

        return True  # Unknown type, allow with caution
    except Exception:
        return False


@router.delete("/reset")
def reset_company_data(
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    _current_user = Depends(require_role("ceo", "admin")),
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
    the mapping engine is the riskiest piece, don't let it write blind).

    SECURITY: Validates file type via magic numbers, sanitizes filename,
    and enforces size limits to prevent malicious file uploads."""
    # Sanitize the filename to prevent path traversal
    safe_filename = _sanitize_filename(file.filename or "uploaded_file")

    # Check file extension for quick rejection
    file_ext = os.path.splitext(safe_filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Supported formats: Excel (.xlsx, .xls), CSV, Images (JPG, PNG, WebP, TIFF, BMP)"
        )

    # Create upload directory
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Generate a safe, unique filename
    stored_path = upload_dir / f"{uuid.uuid4()}_{safe_filename}"

    # Write the file to disk
    try:
        with stored_path.open("wb") as f:
            shutil.copyfileobj(file.file, f)
    except Exception as e:
        # Clean up partially written file
        if stored_path.exists():
            stored_path.unlink()
        raise HTTPException(status_code=500, detail="Failed to save uploaded file")

    # Validate file size after writing
    file_size = stored_path.stat().st_size
    if file_size > MAX_FILE_SIZE:
        stored_path.unlink()
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {settings.MAX_UPLOAD_SIZE_MB}MB"
        )

    # Validate file signature (magic numbers)
    if not _validate_file_signature(str(stored_path), file_ext):
        stored_path.unlink()
        raise HTTPException(
            status_code=400,
            detail=f"File content doesn't match its extension. Possible security risk."
        )

    # Check if this is an image file (for OCR)
    is_image = file_ext in {".jpg", ".jpeg", ".png", ".webp", ".tiff", ".bmp"}

    if is_image:
        # For images, we'll store them for OCR processing later
        # Create a placeholder result for now
        upload = Upload(
            company_id=company_id,
            original_filename=file.filename,
            stored_path=str(stored_path),
            status=UploadStatus.UPLOADED,
            column_mapping={},
            validation_issues={"image": ["Image file uploaded. OCR processing pending."]},
        )
        db.add(upload)
        db.commit()
        db.refresh(upload)

        return {
            "upload_id": upload.id,
            "file_type": "image",
            "message": "Image uploaded successfully. OCR processing will extract business data.",
            "next_step": "Please confirm to start OCR extraction",
        }

    # For Excel/CSV files, parse them
    try:
        parsed_sheets = detect_and_parse_workbook(str(stored_path))
    except Exception as e:
        stored_path.unlink()
        raise HTTPException(
            status_code=400,
            detail=f"Could not parse file. Please ensure it's a valid Excel or CSV file."
        )

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


# ============================================================
# UNIVERSAL INGESTION ENDPOINTS (New flexible ingestion flow)
# ============================================================

@router.post("/{upload_id}/analyze")
def analyze_upload(
    upload_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
):
    """
    Analyze an uploaded file with universal ingestion engine.
    Returns detailed sheet analysis with confidence scores, column detection,
    and suggested mappings for user review before import.
    """
    logger.info(f"[UNIVERSAL] analyze_upload called for upload_id={upload_id}")
    upload = db.query(Upload).filter(Upload.id == upload_id, Upload.company_id == company_id).first()
    if not upload:
        logger.warning(f"[UNIVERSAL] Upload not found: {upload_id}")
        raise HTTPException(status_code=404, detail="Upload not found")

    # Check if this is an image file
    file_ext = os.path.splitext(upload.stored_path)[1].lower()
    is_image = file_ext in {".jpg", ".jpeg", ".png", ".webp", ".tiff", ".bmp"}

    if is_image:
        raise HTTPException(
            status_code=400,
            detail="Image files require OCR processing. Use /confirm for OCR extraction."
        )

    # Parse with universal engine
    try:
        parsed_results = parse_workbook_universal(upload.stored_path)
    except Exception as e:
        logger.error(f"[UNIVERSAL] Parse failed: {e}")
        raise HTTPException(status_code=400, detail=f"Could not parse file: {str(e)}")

    # Build detailed analysis for each sheet
    sheets_analysis = []
    for result in parsed_results:
        summary = get_sheet_summary(result)
        sheets_analysis.append(summary)

    # Update upload with universal analysis
    upload.status = UploadStatus.MAPPED
    upload.column_mapping = {
        r.sheet_name: r.analysis.suggested_mappings for r in parsed_results
    }
    upload.validation_issues = {
        r.sheet_name: r.warnings for r in parsed_results if r.warnings
    }
    db.commit()

    return {
        "upload_id": upload.id,
        "original_filename": upload.original_filename,
        "sheets": sheets_analysis,
        "message": "Analysis complete. Review column mappings and confirm to import.",
    }


@router.post("/{upload_id}/map")
def save_column_mappings(
    upload_id: uuid.UUID,
    mappings: dict = Body(..., description="Column mappings per sheet: {sheet_name: {standard_field: original_column}}"),
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
):
    """
    Save user-provided column mappings for an upload.
    This allows users to correct/override auto-detected mappings before import.
    """
    logger.info(f"[UNIVERSAL] save_column_mappings for upload_id={upload_id}")
    upload = db.query(Upload).filter(Upload.id == upload_id, Upload.company_id == company_id).first()
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")

    # Store user mappings in the upload record
    upload.column_mapping = mappings
    upload.status = UploadStatus.MAPPED
    db.commit()

    return {
        "upload_id": upload.id,
        "status": "mappings_saved",
        "message": "Column mappings saved. You can now confirm to import with these mappings.",
    }


@router.post("/{upload_id}/confirm-universal")
def confirm_universal_import(
    upload_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
):
    """
    Import data using universal ingestion with user-confirmed mappings.

    This replaces the company's existing business data (same as regular confirm)
    but uses the universal parser which can handle any file structure.

    Mappings are read from upload.column_mapping (saved via /map endpoint).
    """
    logger.info(f"[UNIVERSAL] confirm_universal_import for upload_id={upload_id}")
    upload = db.query(Upload).filter(Upload.id == upload_id, Upload.company_id == company_id).first()
    if not upload:
        logger.warning(f"[UNIVERSAL] Upload not found: {upload_id}")
        raise HTTPException(status_code=404, detail="Upload not found")

    # Check if this is an image file
    file_ext = os.path.splitext(upload.stored_path)[1].lower()
    is_image = file_ext in {".jpg", ".jpeg", ".png", ".webp", ".tiff", ".bmp"}

    if is_image:
        raise HTTPException(
            status_code=400,
            detail="Image files require OCR processing. Use /confirm for OCR extraction."
        )

    # Get user mappings from upload record
    user_mappings = upload.column_mapping or {}

    # Parse with universal engine and apply user mappings
    try:
        parsed_results = parse_workbook_with_mappings(upload.stored_path, user_mappings)
    except Exception as e:
        logger.error(f"[UNIVERSAL] Parse with mappings failed: {e}")
        raise HTTPException(status_code=400, detail=f"Could not parse file with mappings: {str(e)}")

    # Clear existing data (same as regular confirm)
    db.query(ProductionRun).filter(ProductionRun.company_id == company_id).delete()
    db.query(Product).filter(Product.company_id == company_id).delete()
    db.query(ContractorLedgerEntry).filter(ContractorLedgerEntry.company_id == company_id).delete()
    db.query(Expense).filter(Expense.company_id == company_id).delete()

    rows_imported = 0

    for result in parsed_results:
        df = result.dataframe
        if df.empty:
            continue

        sheet_type = result.sheet_type

        # Map universal sheet types to existing import logic
        if sheet_type in ("production_log", "production_costing"):
            # Determine stream from sheet name or default
            stream = ProductionStream.UNSPECIFIED
            name_lower = result.sheet_name.lower()
            if "self" in name_lower:
                stream = ProductionStream.SELF_MADE
            elif "cmt" in name_lower:
                stream = ProductionStream.CMT

            for _, row in df.iterrows():
                article = clean(row.get("article") or row.get("article_code") or row.get("product"))
                db.add(ProductionRun(
                    company_id=company_id,
                    date=clean(row.get("date")),
                    stream=stream,
                    article_label=str(article) if article is not None else None,
                    quantity=clean(row.get("quantity")),
                    cost_total=clean(row.get("cost_total") or row.get("cost")),
                    sale_price_piece=clean(row.get("sale_price_piece") or row.get("unit_price") or row.get("sale_price_per_piece")),
                    revenue_total=clean(row.get("revenue_total") or row.get("revenue")),
                    profit=clean(row.get("profit") or row.get("profit_per_piece")),
                    cost_breakdown=row.get("cost_breakdown") if isinstance(row.get("cost_breakdown"), dict) else None,
                    source_upload_id=upload.id,
                    source_sheet=result.sheet_name,
                ))
                rows_imported += 1

        elif sheet_type == "article_costing":
            for _, row in df.iterrows():
                article_code = clean(row.get("article_code") or row.get("product"))
                db.add(Product(
                    company_id=company_id,
                    cloth_type=clean(row.get("cloth_type") or row.get("product")),
                    article_code=str(article_code) if article_code is not None else None,
                    cost_per_meter=clean(row.get("cost_per_meter") or row.get("cost_per_piece")),
                    cloth_meters_per_piece=clean(row.get("meters_per_piece") or row.get("cloth_meters_per_piece")),
                    cloth_cost_per_piece=clean(row.get("cloth_cost_per_piece")),
                    stitching_cost_per_piece=clean(row.get("stitching_cost") or row.get("stitching_cost_per_piece")),
                    embroidery_cost_per_piece=clean(row.get("embroidery_cost") or row.get("embroidery_cost_per_piece")),
                    washing_cost_per_piece=clean(row.get("washing_cost") or row.get("washing_cost_per_piece")),
                    total_cost_per_piece=clean(row.get("total_cost_per_piece") or row.get("cost")),
                    sale_price_per_piece=clean(row.get("sale_price_per_piece") or row.get("unit_price")),
                    profit_per_piece=clean(row.get("profit_per_piece") or row.get("profit")),
                    source="verified",
                ))
                rows_imported += 1

        elif sheet_type == "expenses":
            for _, row in df.iterrows():
                description = clean(row.get("description")) or ""
                db.add(Expense(
                    company_id=company_id,
                    date=clean(row.get("date")),
                    description=description,
                    category=categorize_expense(description),
                    amount_received=clean(row.get("amount_received")),
                    amount_used=clean(row.get("cost") or row.get("amount_used")),
                    running_balance=clean(row.get("balance")),
                    source_upload_id=upload.id,
                ))
                rows_imported += 1

        elif sheet_type == "ledger":
            for _, row in df.iterrows():
                db.add(ContractorLedgerEntry(
                    company_id=company_id,
                    date=clean(row.get("date")),
                    amount_billed=clean(row.get("debit") or row.get("amount_billed")),
                    amount_paid=clean(row.get("credit") or row.get("paid") or row.get("amount_paid")),
                    running_balance=clean(row.get("balance")),
                    source_upload_id=upload.id,
                ))
                rows_imported += 1

        elif sheet_type == "sales":
            # Sales data can map to production runs or be stored separately
            # For now, treat as production log with customer info
            for _, row in df.iterrows():
                article = clean(row.get("article") or row.get("product"))
                db.add(ProductionRun(
                    company_id=company_id,
                    date=clean(row.get("date")),
                    stream=ProductionStream.UNSPECIFIED,
                    article_label=str(article) if article is not None else None,
                    quantity=clean(row.get("quantity")),
                    cost_total=clean(row.get("cost")),
                    sale_price_piece=clean(row.get("unit_price")),
                    revenue_total=clean(row.get("revenue")),
                    profit=clean(row.get("profit") or row.get("margin")),
                    source_upload_id=upload.id,
                    source_sheet=result.sheet_name,
                ))
                rows_imported += 1

        elif sheet_type == "purchases":
            # Purchases map to expenses for now
            for _, row in df.iterrows():
                description = clean(row.get("description") or row.get("product")) or "Purchase"
                db.add(Expense(
                    company_id=company_id,
                    date=clean(row.get("date")),
                    description=description,
                    category="Purchases",
                    amount_received=clean(row.get("amount_received")),
                    amount_used=clean(row.get("cost")),
                    running_balance=clean(row.get("balance")),
                    source_upload_id=upload.id,
                ))
                rows_imported += 1

        elif sheet_type in ("receivables", "payables"):
            # Ledger-style entries
            for _, row in df.iterrows():
                db.add(ContractorLedgerEntry(
                    company_id=company_id,
                    date=clean(row.get("date")),
                    amount_billed=clean(row.get("debit") or row.get("amount_billed")),
                    amount_paid=clean(row.get("credit") or row.get("paid") or row.get("amount_paid")),
                    running_balance=clean(row.get("balance")),
                    source_upload_id=upload.id,
                ))
                rows_imported += 1

        elif sheet_type == "inventory":
            # Inventory data - could map to products
            for _, row in df.iterrows():
                article_code = clean(row.get("article_code") or row.get("product"))
                db.add(Product(
                    company_id=company_id,
                    cloth_type=clean(row.get("product")),
                    article_code=str(article_code) if article_code is not None else None,
                    source="verified",
                ))
                rows_imported += 1

        else:
            # Unknown sheet type - log warning but don't fail
            logger.warning(f"[UNIVERSAL] Unknown sheet type '{sheet_type}' for sheet '{result.sheet_name}' - skipping import")

    upload.status = UploadStatus.IMPORTED
    upload.rows_imported = rows_imported
    db.commit()

    return {"upload_id": upload.id, "rows_imported": rows_imported, "status": "imported"}


def _process_ocr_upload(upload: Upload, company_id: uuid.UUID, db: Session) -> dict:
    """
    Process an image upload through OCR.

    Returns extracted data for human review. NEVER automatically imports.
    OCR output must always be reviewed and confirmed by a human.

    Returns:
        dict with status:
        - "review_required": OCR found text (with or without tables). User can review.
        - "failed": OCR could not extract any text. User needs to try a different image.
    """
    logger.info(f"[UPLOAD] _process_ocr_upload started for upload_id={upload.id}, path={upload.stored_path}")

    # Verify file still exists
    if not os.path.exists(upload.stored_path):
        logger.error(f"[UPLOAD] File not found: {upload.stored_path}")
        raise HTTPException(
            status_code=500,
            detail="Uploaded file no longer exists. Please re-upload."
        )

    logger.info(f"[UPLOAD] File exists, size={os.path.getsize(upload.stored_path)} bytes")

    # Run OCR extraction
    logger.info("[UPLOAD] Calling process_register_image...")
    ocr_result = process_register_image(upload.stored_path)

    logger.info(f"[UPLOAD] OCR result: raw_text_len={len(ocr_result.raw_text)}, tables={len(ocr_result.tables)}, confidence={ocr_result.confidence}, warnings={ocr_result.warnings}, detected_language={ocr_result.detected_language}")

    # Check for OCR failures - no text at all
    if not ocr_result.raw_text or not ocr_result.raw_text.strip():
        logger.warning("[UPLOAD] No raw_text from OCR - marking as failed")
        upload.status = UploadStatus.FAILED
        upload.validation_issues = {
            "ocr": ocr_result.warnings or ["OCR extraction failed. No text found in image."]
        }
        db.commit()

        # Build a more informative error message based on warnings
        warnings = ocr_result.warnings or []
        if any("not installed" in w.lower() for w in warnings):
            message = "OCR service is not available on the server. Please try again later."
        elif any("failed" in w.lower() for w in warnings):
            message = "OCR processing encountered an error. The image format may be unsupported or corrupted."
        else:
            message = "Could not extract any text from this image. Please ensure the image is clear, well-lit, and contains readable text. You can also try uploading your data as an Excel or CSV file instead."

        return {
            "upload_id": upload.id,
            "status": "failed",
            "message": message,
            "warnings": ocr_result.warnings,
        }

    # Text was found - proceed to review (even if no tables detected)
    logger.info(f"[UPLOAD] Text found ({len(ocr_result.raw_text)} chars), proceeding to review")

    # Convert OCR result to structured data for review
    extracted_records = []

    # If tables were found, use them
    if ocr_result.tables:
        for i, table_df in enumerate(ocr_result.tables):
            records = table_df.fillna("").to_dict(orient="records")
            extracted_records.append({
                "table_index": i,
                "columns": list(table_df.columns),
                "rows": records[:20],  # Limit preview to 20 rows
                "total_rows": len(records),
            })
    else:
        logger.info("[UPLOAD] No table structure detected - user will see raw text for manual review")

    # Store OCR result for later confirmation
    upload.status = UploadStatus.VALIDATED  # Ready for human review
    upload.validation_issues = {
        "ocr_warnings": ocr_result.warnings,
        "detected_language": ocr_result.detected_language,
        "confidence": ocr_result.confidence,
        "has_tables": bool(ocr_result.tables),
    }
    upload.column_mapping = {
        "ocr_raw_text": ocr_result.raw_text[:5000],  # Store first 5000 chars for reference
        "ocr_confidence": ocr_result.confidence,
    }
    db.commit()

    return {
        "upload_id": upload.id,
        "status": "review_required",
        "message": "OCR extraction complete. Please review and edit the extracted data before confirming.",
        "detected_language": ocr_result.detected_language,
        "confidence": ocr_result.confidence,
        "warnings": ocr_result.warnings,
        "raw_text_preview": ocr_result.raw_text[:1000] if ocr_result.raw_text else None,
        "extracted_records": extracted_records,
        "has_tables": bool(ocr_result.tables),
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

    For images: triggers OCR extraction and returns structured data for
    human review. OCR output is NEVER automatically imported - user must
    review and confirm the extracted data separately.

    For Excel/CSV: imports data directly after user confirmation.

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
    logger.info(f"[UPLOAD] confirm_import called for upload_id={upload_id}")
    upload = db.query(Upload).filter(Upload.id == upload_id, Upload.company_id == company_id).first()
    if not upload:
        logger.warning(f"[UPLOAD] Upload not found: {upload_id}")
        raise HTTPException(status_code=404, detail="Upload not found")

    logger.info(f"[UPLOAD] Found upload: id={upload.id}, status={upload.status}, path={upload.stored_path}")

    # Check if this is an image file (OCR required)
    file_ext = os.path.splitext(upload.stored_path)[1].lower()
    is_image = file_ext in {".jpg", ".jpeg", ".png", ".webp", ".tiff", ".bmp"}
    logger.info(f"[UPLOAD] File extension: {file_ext}, is_image: {is_image}")

    if is_image:
        # OCR flow: extract text and return for human review
        # NEVER automatically import OCR data without review
        logger.info("[UPLOAD] Routing to _process_ocr_upload")
        return _process_ocr_upload(upload, company_id, db)

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


@router.post("/{upload_id}/confirm-ocr")
def confirm_ocr_import(
    upload_id: uuid.UUID,
    records: list[dict] = Body(..., description="User-reviewed OCR records"),
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
):
    """
    Step 7 (OCR only): Import user-confirmed OCR data.

    This endpoint ONLY accepts data that has been reviewed and edited by a human.
    The `records` parameter must contain the corrected/validated data from the frontend.

    SECURITY: This is the ONLY way OCR data enters the database.
    Raw OCR output never bypasses human review.
    """
    logger.info(f"[UPLOAD] confirm_ocr_import called for upload_id={upload_id}, records_count={len(records)}")
    upload = db.query(Upload).filter(
        Upload.id == upload_id,
        Upload.company_id == company_id
    ).first()
    if not upload:
        logger.warning(f"[UPLOAD] Upload not found: {upload_id}")
        raise HTTPException(status_code=404, detail="Upload not found")

    # Verify this is an OCR upload that has been reviewed
    file_ext = os.path.splitext(upload.stored_path)[1].lower()
    is_image = file_ext in {".jpg", ".jpeg", ".png", ".webp", ".tiff", ".bmp"}

    if not is_image:
        logger.warning(f"[UPLOAD] Not an image file: {file_ext}")
        raise HTTPException(
            status_code=400,
            detail="This endpoint is only for OCR uploads. Use /confirm for Excel/CSV files."
        )

    if upload.status != UploadStatus.VALIDATED:
        logger.warning(f"[UPLOAD] Invalid status for OCR confirm: {upload.status}")
        raise HTTPException(
            status_code=400,
            detail="OCR data must be reviewed before confirmation. Call /confirm first."
        )

    if not records:
        logger.warning("[UPLOAD] No records provided for OCR confirmation")
        raise HTTPException(
            status_code=400,
            detail="No records provided. OCR did not extract any tabular data. Please try a clearer image or use Excel/CSV upload instead."
        )

    # Clear existing data (same as regular confirm)
    db.query(ProductionRun).filter(ProductionRun.company_id == company_id).delete()
    db.query(Product).filter(Product.company_id == company_id).delete()
    db.query(ContractorLedgerEntry).filter(ContractorLedgerEntry.company_id == company_id).delete()
    db.query(Expense).filter(Expense.company_id == company_id).delete()

    rows_imported = 0

    # Process user-confirmed records
    # Each record should have a 'type' field indicating the data type
    for record in records:
        record_type = record.get("type", "unknown")

        if record_type == "production":
            db.add(ProductionRun(
                company_id=company_id,
                date=clean(record.get("date")),
                stream=ProductionStream.UNSPECIFIED,
                article_label=clean(record.get("article")),
                quantity=clean(record.get("quantity")),
                cost_total=clean(record.get("cost_total")),
                sale_price_piece=clean(record.get("sale_price_piece")),
                revenue_total=clean(record.get("revenue_total")),
                profit=clean(record.get("profit")),
                source_upload_id=upload.id,
                source_sheet="ocr_extracted",
            ))
            rows_imported += 1

        elif record_type == "product":
            db.add(Product(
                company_id=company_id,
                cloth_type=clean(record.get("cloth_type")),
                article_code=clean(record.get("article_code")),
                cost_per_meter=clean(record.get("cost_per_meter")),
                cloth_meters_per_piece=clean(record.get("cloth_meters_per_piece")),
                cloth_cost_per_piece=clean(record.get("cloth_cost_per_piece")),
                stitching_cost_per_piece=clean(record.get("stitching_cost_per_piece")),
                embroidery_cost_per_piece=clean(record.get("embroidery_cost_per_piece")),
                washing_cost_per_piece=clean(record.get("washing_cost_per_piece")),
                total_cost_per_piece=clean(record.get("total_cost_per_piece")),
                sale_price_per_piece=clean(record.get("sale_price_per_piece")),
                profit_per_piece=clean(record.get("profit_per_piece")),
                source="ocr_verified",
            ))
            rows_imported += 1

        elif record_type == "expense":
            description = clean(record.get("description")) or ""
            db.add(Expense(
                company_id=company_id,
                date=clean(record.get("date")),
                description=description,
                category=categorize_expense(description),
                amount_received=clean(record.get("amount_received")),
                amount_used=clean(record.get("amount_used")),
                running_balance=clean(record.get("balance")),
                source_upload_id=upload.id,
            ))
            rows_imported += 1

        elif record_type == "ledger":
            db.add(ContractorLedgerEntry(
                company_id=company_id,
                date=clean(record.get("date")),
                amount_billed=clean(record.get("amount_billed")),
                amount_paid=clean(record.get("amount_paid")),
                running_balance=clean(record.get("balance")),
                source_upload_id=upload.id,
            ))
            rows_imported += 1

    upload.status = UploadStatus.IMPORTED
    upload.rows_imported = rows_imported
    db.commit()

    return {
        "upload_id": upload.id,
        "rows_imported": rows_imported,
        "status": "imported",
        "source": "ocr_verified",
    }
