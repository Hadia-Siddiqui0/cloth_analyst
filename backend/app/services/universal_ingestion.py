"""
Universal ingestion engine for ANY business data source.

This module replaces the hardcoded column matching with intelligent
auto-detection that works with:
- ANY column names (detects by data type, not by label)
- ANY sheet structure (auto-detects sheet purpose)
- ANY language (works with English, Urdu, etc.)
- Missing columns (gracefully handles incomplete data)
- Extra columns (captures everything, doesn't discard)

Design principles:
1. Data type detection: Identify columns by their content, not their names
2. Semantic understanding: Detect if a column contains dates, money, quantities, text
3. Pattern recognition: Find columns that "look like" dates, totals, profits
4. User override: Allow manual mapping when auto-detection is uncertain
5. No data loss: Keep all columns, mark confidence level

This is the foundation for the "upload anything" vision.
"""
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

import pandas as pd


@dataclass
class ColumnAnalysis:
    """Analysis of a single column's content and type."""
    original_name: str
    detected_type: str  # "date", "number", "currency", "text", "unknown"
    confidence: float  # 0.0 to 1.0
    sample_values: list[Any]
    null_count: int
    unique_count: int
    suggested_mapping: str | None  # Standard field name if confident


@dataclass
class SheetAnalysis:
    """Complete analysis of a sheet's structure."""
    sheet_name: str
    detected_type: str  # "production_log", "sales", "expenses", "inventory", "ledger", "unknown"
    confidence: float
    columns: list[ColumnAnalysis]
    row_count: int
    warnings: list[str]
    suggested_mappings: dict[str, str]  # standard_name -> original_column_name


@dataclass
class UniversalParseResult:
    """Result of parsing any data source."""
    sheet_name: str
    sheet_type: str
    confidence: float
    dataframe: pd.DataFrame
    analysis: SheetAnalysis
    warnings: list[str] = field(default_factory=list)


# Standard field names we look for in business data
# Each field maps to a list of aliases in multiple languages
STANDARD_FIELDS = {
    # Time fields
    "date": ["date", "dated", "dt", "day", "time", "tarikh", "تاریخ", "tanggal", "fecha", "datum"],

    # Product/Item fields
    "product": ["product", "item", "article", "cloth", "type", "design", "style", "maal", "مال", "مصنوع", "articulo", "produkt"],
    "article_code": ["article", "code", "sku", "id", "ref", "number", "art", "item_code", "product_code"],
    "quantity": ["quantity", "qty", "count", "pieces", "units", "amount", "tadad", "تعداد", "cantidad", "menge",
                 "amount/piece", "amount/pice", "amt/piece", "amt/pice", "amount per piece"],

    # Money in (revenue)
    "revenue": ["revenue", "sale", "sales", "income", "total sale", "total sales", "bikri", "بیع", "فروخت", "ventas", "umsatz", "ingresos",
                "total", "total.1", "grand total", "total amount", "total amount."],
    "unit_price": ["price", "rate", "unit price", "sale price", "price per piece", "preis", "precio",
                   "amount/piece", "amount/pice", "amt/piece", "amt/pice", "amount per piece"],

    # Money out (cost)
    "cost": ["cost", "total cost", "expense", "kharcha", "خرچہ", "کھرچہ", "kosten", "costo", "gasto",
             "total cost", "total", "total.", "total.1", "grand total", "amount"],
    "cost_per_piece": ["cost per piece", "cost/piece", "unit cost", "cost per unit"],

    # Profit
    "profit": ["profit", "gain", "faida", "فائدہ", "منافع", "ganancia", "gewinn", "margen",
               "total profit", "profit.", "profit.1"],
    "margin": ["margin", "profit margin", "profit %", "marge", "margen"],

    # Customer
    "customer": ["customer", "client", "buyer", "party", "grahak", "گاہک", "cliente", "kunde", "kunden"],

    # Supplier
    "supplier": ["supplier", "vendor", "seller", "party", "faroosh", "proveedor", "lieferant", "vendor",
                 "supp", "supp.", "supply"],

    # Balance/Payment
    "balance": ["balance", "remaining", "baqi", "باقی", "saldo", "restbetrag"],
    "paid": ["paid", "payment", "jama", "جمع", "pagado", "bezahlt", "paid_amount",
             "receive", "received", "recive", "amount received", "amount recive"],
    "due": ["due", "pending", "outstanding", "baki", "fälligkeit", "pendiente"],

    # Description
    "description": ["description", "details", "notes", "remarks", "detail", "beschreibung", "descripcion", "note"],

    # Category
    "category": ["category", "type", "group", "class", "kategorie", "categoria", "klasse"],

    # Inventory
    "stock_in": ["stock in", "received", "purchase", "in", "aaya", "entrada", "zugang", "receipts"],
    "stock_out": ["stock out", "issued", "sold", "out", "gaya", "salida", "abgang", "issues"],
    "stock_balance": ["stock", "inventory", "balance", "remainder", "bestand", "inventario", "existencias"],

    # Production-specific (for garment factory compatibility)
    "cloth_type": ["cloth type", "cloth", "fabric", "material", "tela", "stoff",
                   "cloth", "cloth type"],
    "meters_per_piece": ["meters per piece", "cloth meters", "meters/piece", "m/piece", "meter je stück",
                         "cloth/piece", "cloth peace", "meters per peace"],
    "stitching_cost": ["stitching", "stitching cost", "sewing", "sewing cost", "nähkosten", "costura",
                       "stitching/piece", "steaching peace", "steaching/peace"],
    "embroidery_cost": ["embroidery", "embroidery cost", "stickerei", "bordado",
                        "embroidery/piece", "embroidery peace"],
    "washing_cost": ["washing", "washing cost", "wäsche", "lavado",
                     "washing/piece", "washing peace"],
    "total_cost_per_piece": ["total cost per piece", "total cost/piece", "cost per piece total",
                             "total peace", "total/peace"],
    "sale_price_per_piece": ["sale price per piece", "sale price/piece", "selling price", "verkaufspreis",
                             "sale/peace", "seal/peace", "seal peace"],
    "profit_per_piece": ["profit per piece", "profit/piece", "gewinn je stück", "ganancia por pieza",
                         "profit/peace", "profit peace"],
    "total_pieces": ["total pieces", "total pcs", "total pieces produced"],
    "total_profit": ["total profit", "total gain", "total profit.", "total.profit"],

    # Garment factory specific cost breakdown items
    "kaaj_button": ["kaaj", "button", "kaaj/button", "kaaj/ button", "kaaj/button"],
    "electricity": ["elect", "electricity", "electric", "ssgc", "fuel", "fule"],
    "maintenance": ["maintanace", "maintenance", "mechanic"],
    "transport": ["transpotaion", "transp", "transport", "transportation"],
    "rent": ["rent"],
    "mis": ["mis", "misc", "miscellaneous"],
    "helper": ["helper", "helper/loader", "helper / loader"],
    "sweeper": ["sweeper"],
    "security": ["security"],
    "cards_labels": ["cards", "labels", "cards & labels", "cards & leable"],

    # Ledger/Accounting specific
    "debit": ["debit", "dr", "charge", "belastung", "cargo", "amount", "amount used", "used"],
    "credit": ["credit", "cr", "credit amount", "gutschrift", "abono", "receive", "received", "recive", "amount recive", "amount receive"],
    "reference": ["reference", "ref", "ref no", "voucher", "beleg", "referencia"],
    "account": ["account", "account name", "konto", "cuenta"],
}


def detect_column_type(series: pd.Series) -> tuple[str, float]:
    """
    Detect the type of a column by analyzing its content.
    Returns (type, confidence) where confidence is 0.0-1.0.
    """
    # Drop nulls for analysis
    non_null = series.dropna()
    if len(non_null) == 0:
        return ("unknown", 0.0)

    sample = non_null.head(100).tolist()

    # Try to detect date
    date_count = 0
    for val in sample:
        if isinstance(val, (pd.Timestamp, datetime)):
            date_count += 1
        elif isinstance(val, str):
            # Try common date patterns
            date_patterns = [
                r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}',  # dd-mm-yyyy, mm/dd/yyyy
                r'\d{4}[-/]\d{1,2}[-/]\d{1,2}',    # yyyy-mm-dd
                r'\d{1,2}\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)',  # dd month
            ]
            if any(re.search(p, val, re.IGNORECASE) for p in date_patterns):
                date_count += 1

    if date_count / len(sample) > 0.5:
        return ("date", date_count / len(sample))

    # Try to detect number
    numeric_count = 0
    for val in sample:
        if isinstance(val, (int, float)):
            numeric_count += 1
        elif isinstance(val, str):
            # Remove common non-numeric chars and try to parse
            cleaned = re.sub(r'[^\d.\-]', '', val)
            if cleaned and cleaned.replace('.', '').replace('-', '').isdigit():
                numeric_count += 1

    if numeric_count / len(sample) > 0.7:
        # Check if it looks like currency (has decimals or large values)
        avg_val = pd.to_numeric(non_null, errors='coerce').mean()
        if avg_val > 1000 or any(isinstance(v, float) or (isinstance(v, str) and '.' in v) for v in sample[:10]):
            return ("currency", numeric_count / len(sample))
        return ("number", numeric_count / len(sample))

    # Default to text
    return ("text", 0.5)


def find_matching_field(column_name: str, column_type: str) -> tuple[str | None, float]:
    """
    Find the standard field name that matches this column.
    Returns (standard_name, confidence).
    """
    col_lower = str(column_name).lower().strip()

    # Direct match with known aliases
    for standard, aliases in STANDARD_FIELDS.items():
        for alias in aliases:
            if alias in col_lower or col_lower in alias:
                return (standard, 0.9)

    # Fuzzy match for typos
    import difflib
    for standard, aliases in STANDARD_FIELDS.items():
        matches = difflib.get_close_matches(col_lower, aliases, n=1, cutoff=0.7)
        if matches:
            return (standard, 0.7)

    # Type-based inference
    if column_type == "date":
        return ("date", 0.6)
    if column_type == "currency":
        # Try to infer which currency field
        if any(word in col_lower for word in ["sale", "revenue", "income", "bikri"]):
            return ("revenue", 0.5)
        if any(word in col_lower for word in ["cost", "expense", "kharcha"]):
            return ("cost", 0.5)
        if any(word in col_lower for word in ["profit", "faida"]):
            return ("profit", 0.5)
        if any(word in col_lower for word in ["balance", "baqi"]):
            return ("balance", 0.5)

    return (None, 0.0)


def analyze_column(series: pd.Series) -> ColumnAnalysis:
    """Perform complete analysis of a column."""
    detected_type, type_confidence = detect_column_type(series)
    suggested_mapping, mapping_confidence = find_matching_field(series.name, detected_type)

    # Get sample values (non-null)
    sample_values = series.dropna().head(5).tolist()

    return ColumnAnalysis(
        original_name=str(series.name),
        detected_type=detected_type,
        confidence=max(type_confidence, mapping_confidence),
        sample_values=sample_values,
        null_count=series.isna().sum(),
        unique_count=series.nunique(),
        suggested_mapping=suggested_mapping,
    )


def detect_sheet_type(columns: list[ColumnAnalysis]) -> tuple[str, float]:
    """
    Detect what type of business data this sheet contains.
    Returns (sheet_type, confidence).
    """
    # Build a set of detected standard fields
    detected_fields = {c.suggested_mapping for c in columns if c.suggested_mapping}
    original_names = {c.original_name.lower() for c in columns}

    # Also check column types for additional signals
    column_types = {c.detected_type for c in columns}
    has_dates = "date" in column_types
    has_currency = "currency" in column_types
    has_numbers = "number" in column_types

    # Production log: has date, quantity, revenue/cost, profit
    production_fields = {"date", "quantity", "revenue", "cost", "profit"}
    production_match = len(detected_fields & production_fields)
    if production_match >= 3:
        return ("production_log", production_match / len(production_fields))

    # Sales: has date, customer, product, quantity, revenue
    sales_fields = {"date", "customer", "product", "quantity", "revenue"}
    sales_match = len(detected_fields & sales_fields)
    if sales_match >= 3:
        return ("sales", sales_match / len(sales_fields))

    # Article costing: has product, cost_per_piece, sale_price_per_piece, profit_per_piece
    costing_fields = {"product", "article_code", "cost_per_piece", "sale_price_per_piece", "profit_per_piece", "cloth_type", "meters_per_piece"}
    costing_match = len(detected_fields & costing_fields)
    if costing_match >= 3:
        return ("article_costing", costing_match / len(costing_fields))

    # Expenses: has date, description, cost (or paid/used amount)
    expense_fields = {"date", "description", "cost", "paid", "credit"}
    expense_match = len(detected_fields & expense_fields)
    if expense_match >= 2:
        return ("expenses", expense_match / len(expense_fields))

    # Ledger: has date, balance, paid (received)
    ledger_fields = {"date", "balance", "paid", "due", "debit", "credit"}
    ledger_match = len(detected_fields & ledger_fields)
    if ledger_match >= 2:
        return ("ledger", ledger_match / len(ledger_fields))

    # Inventory: has product, stock_in, stock_out, stock_balance
    inventory_fields = {"product", "stock_in", "stock_out", "stock_balance"}
    inventory_match = len(detected_fields & inventory_fields)
    if inventory_match >= 2:
        return ("inventory", inventory_match / len(inventory_fields))

    # Purchases: has date, supplier, product, quantity, cost
    purchase_fields = {"date", "supplier", "product", "quantity", "cost"}
    purchase_match = len(detected_fields & purchase_fields)
    if purchase_match >= 3:
        return ("purchases", purchase_match / len(purchase_fields))

    # Receivables/Payables: has date, customer/supplier, balance, paid/due
    receivable_fields = {"date", "customer", "balance", "paid", "due"}
    receivable_match = len(detected_fields & receivable_fields)
    if receivable_match >= 3:
        return ("receivables", receivable_match / len(receivable_fields))

    payable_fields = {"date", "supplier", "balance", "paid", "due"}
    payable_match = len(detected_fields & payable_fields)
    if payable_match >= 3:
        return ("payables", payable_match / len(payable_fields))

    # Production runs with cost breakdown (garment factory specific)
    if "cloth_type" in detected_fields and "meters_per_piece" in detected_fields:
        return ("production_costing", 0.7)

    # Check for ledger-like sheets by original column names (fallback)
    ledger_keywords = {"amount", "receive", "recive", "balance", "description", "date"}
    if len(original_names & ledger_keywords) >= 3 and has_dates:
        return ("ledger", 0.6)

    # Check for expense-like sheets by original column names
    expense_keywords = {"description", "amount recive", "used", "amount", "balance", "date"}
    if len(original_names & expense_keywords) >= 3 and has_dates:
        return ("expenses", 0.6)

    # Default to unknown - but provide some confidence based on data types
    if has_dates and has_currency:
        return ("unknown", 0.5)
    if has_dates:
        return ("unknown", 0.4)

    return ("unknown", 0.3)


def find_header_row(df: pd.DataFrame, max_scan: int = 10) -> int:
    """
    Find the row that looks like a header by checking for
    date-type columns and text headers.
    """
    for i in range(min(max_scan, len(df))):
        row = df.iloc[i]
        # Check if this row has text values that look like headers
        text_count = sum(1 for v in row if isinstance(v, str) and len(str(v)) > 0)
        # Check if next row has different data types (indicates data, not headers)
        if i + 1 < len(df):
            next_row = df.iloc[i + 1]
            has_numbers = any(isinstance(v, (int, float)) for v in next_row if pd.notna(v))
            has_dates = any(isinstance(v, (pd.Timestamp, datetime)) for v in next_row if pd.notna(v))
            if text_count > 3 and (has_numbers or has_dates):
                return i

    return 0  # Default to first row


def universal_parse_sheet(file_path: str, sheet_name: str | None = None) -> UniversalParseResult:
    """
    Parse any sheet from any file with intelligent column detection.
    Works with Excel, CSV, and doesn't require specific column names.
    """
    try:
        # Read the file
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path, header=None, nrows=100)
            header_row = find_header_row(df)
            df = pd.read_csv(file_path, header=header_row)
            actual_sheet = "CSV Data"
        else:
            xls = pd.ExcelFile(file_path)
            if sheet_name is None:
                sheet_name = xls.sheet_names[0]
            actual_sheet = sheet_name

            # Read without header first to find header row
            raw = pd.read_excel(xls, sheet_name=sheet_name, header=None, nrows=100)
            header_row = find_header_row(raw)
            df = pd.read_excel(xls, sheet_name=sheet_name, header=header_row)

        # Remove unnamed columns
        df = df.loc[:, ~df.columns.astype(str).str.contains('unnamed', case=False, na=False)]

        # Drop completely empty rows
        df = df.dropna(how='all')

        if len(df) == 0:
            return UniversalParseResult(
                sheet_name=actual_sheet,
                sheet_type="empty",
                confidence=1.0,
                dataframe=df,
                analysis=SheetAnalysis(
                    sheet_name=actual_sheet,
                    detected_type="empty",
                    confidence=1.0,
                    columns=[],
                    row_count=0,
                    warnings=["Sheet is empty"],
                    suggested_mappings={},
                ),
                warnings=["Sheet is empty"],
            )

        # Analyze each column
        column_analyses = [analyze_column(df[col]) for col in df.columns]

        # Detect sheet type
        sheet_type, sheet_confidence = detect_sheet_type(column_analyses)

        # Build suggested mappings
        suggested_mappings = {}
        for col in column_analyses:
            if col.suggested_mapping and col.confidence > 0.5:
                suggested_mappings[col.suggested_mapping] = col.original_name

        # Build analysis object
        analysis = SheetAnalysis(
            sheet_name=actual_sheet,
            detected_type=sheet_type,
            confidence=sheet_confidence,
            columns=column_analyses,
            row_count=len(df),
            warnings=[],
            suggested_mappings=suggested_mappings,
        )

        # Generate warnings for low-confidence mappings
        warnings = []
        for col in column_analyses:
            if col.suggested_mapping and col.confidence < 0.6:
                warnings.append(
                    f"Low confidence mapping: '{col.original_name}' → '{col.suggested_mapping}' ({col.confidence:.0%})"
                )

        # Standardize column names in output DataFrame
        standardized_df = df.copy()
        rename_map = {v: k for k, v in suggested_mappings.items()}
        standardized_df = standardized_df.rename(columns=rename_map)

        # Convert date columns
        for col in standardized_df.columns:
            if 'date' in str(col).lower() or any(c.detected_type == 'date' and c.original_name == col for c in column_analyses):
                standardized_df[col] = pd.to_datetime(standardized_df[col], errors='coerce')

        return UniversalParseResult(
            sheet_name=actual_sheet,
            sheet_type=sheet_type,
            confidence=sheet_confidence,
            dataframe=standardized_df,
            analysis=analysis,
            warnings=warnings,
        )

    except Exception as e:
        return UniversalParseResult(
            sheet_name=sheet_name or "unknown",
            sheet_type="error",
            confidence=0.0,
            dataframe=pd.DataFrame(),
            analysis=SheetAnalysis(
                sheet_name=sheet_name or "unknown",
                detected_type="error",
                confidence=0.0,
                columns=[],
                row_count=0,
                warnings=[str(e)],
                suggested_mappings={},
            ),
            warnings=[f"Failed to parse: {str(e)}"],
        )


def parse_workbook_universal(file_path: str) -> list[UniversalParseResult]:
    """
    Parse all sheets from any workbook (Excel or CSV).
    This is the main entry point for universal ingestion.
    """
    results = []

    if file_path.endswith('.csv'):
        # Single CSV file
        results.append(universal_parse_sheet(file_path))
    else:
        # Excel file - parse all sheets
        try:
            xls = pd.ExcelFile(file_path)
            for sheet_name in xls.sheet_names:
                results.append(universal_parse_sheet(file_path, sheet_name))
        except Exception as e:
            results.append(UniversalParseResult(
                sheet_name="error",
                sheet_type="error",
                confidence=0.0,
                dataframe=pd.DataFrame(),
                analysis=SheetAnalysis(
                    sheet_name="error",
                    detected_type="error",
                    confidence=0.0,
                    columns=[],
                    row_count=0,
                    warnings=[str(e)],
                    suggested_mappings={},
                ),
                warnings=[f"Failed to read workbook: {str(e)}"],
            ))

    return results


def apply_user_mappings(
    parse_result: UniversalParseResult,
    user_mappings: dict[str, str]
) -> UniversalParseResult:
    """
    Apply user-provided column mappings to a parse result.

    Args:
        parse_result: The original parse result
        user_mappings: Dict mapping {standard_field_name: original_column_name}
                      e.g., {"date": "Order Date", "revenue": "Total Sales"}

    Returns:
        New UniversalParseResult with updated mappings and standardized dataframe
    """
    # Create a copy of the analysis with updated suggested_mappings
    updated_mappings = {**parse_result.analysis.suggested_mappings, **user_mappings}

    # Standardize column names in output DataFrame
    standardized_df = parse_result.dataframe.copy()
    rename_map = {v: k for k, v in updated_mappings.items()}
    standardized_df = standardized_df.rename(columns=rename_map)

    # Convert date columns
    for col in standardized_df.columns:
        if 'date' in str(col).lower():
            standardized_df[col] = pd.to_datetime(standardized_df[col], errors='coerce')

    # Build updated analysis
    updated_analysis = SheetAnalysis(
        sheet_name=parse_result.analysis.sheet_name,
        detected_type=parse_result.analysis.detected_type,
        confidence=parse_result.analysis.confidence,
        columns=parse_result.analysis.columns,
        row_count=parse_result.analysis.row_count,
        warnings=parse_result.analysis.warnings,
        suggested_mappings=updated_mappings,
    )

    return UniversalParseResult(
        sheet_name=parse_result.sheet_name,
        sheet_type=parse_result.sheet_type,
        confidence=parse_result.confidence,
        dataframe=standardized_df,
        analysis=updated_analysis,
        warnings=parse_result.warnings,
    )


def parse_workbook_with_mappings(
    file_path: str,
    sheet_mappings: dict[str, dict[str, str]]
) -> list[UniversalParseResult]:
    """
    Parse workbook and apply user-provided mappings per sheet.

    Args:
        file_path: Path to the file
        sheet_mappings: Dict mapping {sheet_name: {standard_field: original_column}}

    Returns:
        List of UniversalParseResult with user mappings applied
    """
    results = parse_workbook_universal(file_path)

    updated_results = []
    for result in results:
        user_map = sheet_mappings.get(result.sheet_name, {})
        if user_map:
            result = apply_user_mappings(result, user_map)
        updated_results.append(result)

    return updated_results


def get_sheet_summary(parse_result: UniversalParseResult) -> dict:
    """
    Get a summary of a parse result for frontend display.
    Includes confidence, warnings, column analysis, and sample data.
    """
    col_summaries = []
    for col in parse_result.analysis.columns:
        col_summaries.append({
            "original_name": col.original_name,
            "detected_type": col.detected_type,
            "confidence": round(col.confidence, 2),
            "suggested_mapping": col.suggested_mapping,
            "sample_values": col.sample_values[:3],
            "null_count": col.null_count,
            "unique_count": col.unique_count,
        })

    return {
        "sheet_name": parse_result.sheet_name,
        "sheet_type": parse_result.sheet_type,
        "confidence": round(parse_result.confidence, 2),
        "row_count": parse_result.analysis.row_count,
        "columns": col_summaries,
        "suggested_mappings": parse_result.analysis.suggested_mappings,
        "warnings": parse_result.warnings,
        "preview": parse_result.dataframe.head(5).fillna("").to_dict(orient="records"),
    }
