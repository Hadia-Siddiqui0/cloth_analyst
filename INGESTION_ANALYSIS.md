# Ingestion Architecture Analysis

## Current State

### `ingestion_service.py` - **FILE-SPECIFIC (Garment Factory)**

This service is **hardcoded to the customer's specific Garment_12_updated.xlsx file**:

1. **Sheet Type Detection** (lines 226-247): Only recognizes 3 sheet types:
   - `daily_production_log` (Self Made, CMT, Daily Progress Sheet, Sheet1)
   - `article_costing` (Sheet4)
   - `ledger` (Contractor Invoice, Balance Sheet)
   - Everything else → `unrecognized`

2. **Hardcoded Column Aliases** (lines 81-91, 145-172):
   - Specific to garment factory terminology ("Transpotaion", "Maintanace", "Sefty", "peace" for "piece")
   - Specific cost breakdown columns: Elect, Rent, Helper, Supp, etc.
   - Article costing columns: "cloth amount peace", "cloth peace", "steaching", etc.

3. **Hardcoded Business Logic**:
   - `ProductionStream` enum (SELF_MADE, CMT, UNSPECIFIED) - line 439-444
   - Sheet name → stream mapping (line 440-444)
   - Expense categorization rules (lines 209-223) - specific to this factory
   - Contractor vs expense ledger detection (line 486-487)

4. **Fixed Output Schema**: Maps directly to `ProductionRun`, `Product`, `Expense`, `ContractorLedgerEntry` models

5. **No User Override**: The mapping is automatic with no confidence scoring or user review capability

---

### `universal_ingestion.py` - **UNIVERSAL (New, Better Architecture)**

This service provides **genuinely flexible ingestion**:

1. **Data-Type Driven Detection** (lines 110-159):
   - Detects column types by content: date, number, currency, text
   - No hardcoded column names required

2. **Multi-Language Field Matching** (lines 65-107):
   - `STANDARD_FIELDS` dictionary with aliases in English, Urdu, etc.
   - Fuzzy matching with difflib for typos

3. **Sheet Type Detection by Content** (lines 218-257):
   - Detects: production_log, sales, expenses, ledger, inventory, unknown
   - Based on which standard fields are present, not sheet names

4. **Confidence Scoring** (lines 34-35, 162-196):
   - Per-column confidence (0.0-1.0)
   - Per-sheet confidence
   - Warnings for low-confidence mappings

5. **Full Analysis Objects** (lines 29-61):
   - `ColumnAnalysis` - complete column metadata
   - `SheetAnalysis` - sheet structure with suggested mappings
   - `UniversalParseResult` - complete parse result with warnings

6. **Flexible Parsing** (lines 280-393):
   - Auto-detects header row (lines 260-277)
   - Handles CSV and Excel
   - Standardizes column names in output DataFrame
   - Converts date columns automatically
   - Preserves ALL columns (no data loss)

7. **Workbook Parser** (lines 396-430):
   - Parses all sheets in Excel file
   - Handles CSV as single-sheet

---

## What Needs to Change

### In `api/uploads.py`:

1. **Replace `detect_and_parse_workbook` with `parse_workbook_universal`** in `/upload` endpoint
2. **Enhance `/confirm` endpoint** to use universal ingestion with user-provided mappings
3. **Add new endpoint** `/api/uploads/{upload_id}/analyze` for detailed analysis preview
4. **Add new endpoint** `/api/uploads/{upload_id}/map` for accepting user column mappings
5. **Preserve transaction safety** - delete old data, insert new in single transaction
6. **Keep company_id scoping** and auth

### In Frontend (`upload.js`):

1. **Show sheet analysis** with confidence indicators
2. **Allow column mapping review** before confirm
3. **Show warnings** for low-confidence mappings
4. **Support "unknown" sheet types** with manual category selection
5. **Keep existing OCR flow** unchanged

### Database Models:

- **No changes needed** - existing models work for garment factory data
- **Add mapping storage** to Upload model for user-confirmed mappings
- The universal parser outputs standardized column names that map to existing models

---

## Migration Strategy

1. **Keep `ingestion_service.py`** for backward compatibility with existing confirm flow
2. **Add universal ingestion as parallel path** - new endpoints, new frontend flow
3. **Feature flag or path-based routing** - `/api/uploads/universal/` or similar
4. **Test with multiple file formats** before deprecating old path
5. **Eventually unify** - make universal the default, old service becomes deprecated

---

## Test Files Needed

| Test | Description |
|------|-------------|
| A | Standard headers (current Garment_12_updated.xlsx) |
| B | Different sheet name, different column order |
| C | Blank rows before header |
| D | Different header names (synonyms) |
| E | Multiple sheets |
| F | CSV format |
| G | Unknown/unrecognized structure |
| H | Mixed language headers (English + Urdu) |
| I | Extra columns not in standard fields |
| J | Missing required columns |

---

## Key Differences Summary

| Aspect | `ingestion_service.py` | `universal_ingestion.py` |
|--------|------------------------|--------------------------|
| Column detection | Name-based (aliases) | Content-type + name-based |
| Sheet detection | Header signature keywords | Standard field presence |
| Languages | English only (with typos) | English + Urdu + extensible |
| Confidence | None | Per-column + per-sheet |
| User override | No | Designed for it |
| Data loss | Drops unrecognized cols | Keeps all columns |
| File formats | Excel only | Excel + CSV |
| Header position | Scans first 6 rows | Scans first 10 rows |
| Output schema | Fixed to garment models | Standardized field names |
| Error handling | Returns unrecognized | Returns analysis with warnings |