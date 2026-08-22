"""
Generalized ingestion engine for garment-factory Excel exports.

This is ported from the prototype that was validated directly against
the customer's real (messy, old) file -- Garment_12_updated.xlsx -- so
the parsing logic here is proven against real data, not theoretical.

Design principles (why it's built this way):
- Column matching is alias + fuzzy (difflib) based, not exact-string,
  because his real headers have typos/whitespace variance even *within*
  the same file ("Transpotaion", "Maintanace", "Sefty").
- Sheet *type* is detected by header signature, not by sheet name --
  a renamed sheet still parses correctly.
- Footer/note rows are dropped by requiring a parseable date, not by
  hardcoding row numbers.
- Nothing here writes to the DB directly -- it returns clean pandas
  DataFrames + a mapping report. The `api/uploads.py` route is
  responsible for review/confirmation and persistence, so a human can
  catch a bad auto-mapping before it becomes data.
"""
import difflib
import re
from dataclasses import dataclass, field

import pandas as pd


@dataclass
class SheetParseResult:
    sheet_name: str
    sheet_type: str  # "daily_production_log" | "article_costing" | "ledger" | "unrecognized"
    dataframe: pd.DataFrame
    column_mapping: dict = field(default_factory=dict)
    missing_fields: list = field(default_factory=list)
    warnings: list = field(default_factory=list)


def normalize_colname(c) -> str:
    c = str(c).lower()
    return re.sub(r"[^a-z0-9]+", " ", c).strip()


def fuzzy_match(col_norm: str, alias_options: list[str], cutoff: float = 0.6) -> bool:
    for opt in alias_options:
        if opt in col_norm:
            return True
    return bool(difflib.get_close_matches(col_norm, alias_options, n=1, cutoff=cutoff))


def find_header_row(raw_df: pd.DataFrame, must_contain=("date",), max_scan: int = 6) -> int | None:
    """Scan the first few rows for the one that looks like a real header,
    instead of assuming header row position is fixed."""
    for i in range(min(max_scan, len(raw_df))):
        row_vals = [normalize_colname(v) for v in raw_df.iloc[i].tolist() if pd.notna(v)]
        if any(m in row_vals for m in must_contain):
            return i
    return None


def parse_daily_production_sheet(xls: pd.ExcelFile, sheet_name: str) -> SheetParseResult:
    """Parses sheets shaped like the customer's 'Self Made' / 'CMT' /
    'Daily Progress Sheet' / 'Sheet1': one row per day, cost breakdown
    columns in the middle, cost total -> sale price -> revenue total ->
    profit as the last four columns."""
    raw = pd.read_excel(xls, sheet_name=sheet_name, header=None)
    hdr_row = find_header_row(raw)
    if hdr_row is None:
        return SheetParseResult(sheet_name, "unrecognized", pd.DataFrame(), warnings=["no header row found"])

    df = pd.read_excel(xls, sheet_name=sheet_name, header=hdr_row)
    df = df.loc[:, ~df.columns.astype(str).str.startswith("Unnamed")]
    colnames = list(df.columns)
    norm_list = [normalize_colname(c) for c in colnames]

    def col_by_alias(aliases):
        for c, n in zip(colnames, norm_list):
            if fuzzy_match(n, aliases):
                return c
        return None

    date_col = col_by_alias(["date"])
    article_col = col_by_alias(["article"])
    qty_col = col_by_alias(["quantity"])
    profit_col = col_by_alias(["profit"])

    total_cols = [c for c, n in zip(colnames, norm_list) if n.startswith("total")]
    price_piece_cols = [c for c, n in zip(colnames, norm_list) if "amount" in n and ("piece" in n or "pice" in n)]

    cost_total_col = total_cols[0] if len(total_cols) >= 1 else None
    revenue_total_col = total_cols[1] if len(total_cols) >= 2 else None
    sale_price_col = price_piece_cols[1] if len(price_piece_cols) >= 2 else (price_piece_cols[0] if price_piece_cols else None)

    mapping = {
        "date": date_col, "article": article_col, "quantity": qty_col,
        "cost_total": cost_total_col, "sale_price_piece": sale_price_col,
        "revenue_total": revenue_total_col, "profit": profit_col,
    }
    missing = [k for k, v in mapping.items() if v is None]

    # Everything between the identity columns (date/article/quantity) and
    # the summary columns (cost total onward) is an itemized overhead cost
    # -- Elect, Rent, Helper, etc. Captured per-row as a dict so the "why
    # did cost change" analysis can attribute a change to a specific
    # category instead of only seeing the total move. Column names kept
    # as-is (not normalized) since these are for display, not matching.
    identified = {c for c in [date_col, article_col, qty_col] if c}
    summary = {c for c in [cost_total_col, sale_price_col, revenue_total_col, profit_col] if c}
    breakdown_cols = [c for c in colnames if c not in identified and c not in summary]
    if breakdown_cols:
        out_breakdown = df[breakdown_cols]

    out = pd.DataFrame({k: df[v] for k, v in mapping.items() if v is not None})
    if breakdown_cols:
        out["cost_breakdown"] = out_breakdown.apply(
            lambda row: {str(c): (None if pd.isna(row[c]) else float(row[c]) if isinstance(row[c], (int, float)) else str(row[c]))
                         for c in breakdown_cols},
            axis=1,
        )
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out = out[out["date"].notna()].copy()  # drops footer "Total"/"Note" rows

    if "article" in out.columns:
        out["article"] = out["article"].ffill()
    if "quantity" in out.columns:
        out["quantity"] = out["quantity"].ffill()

    warnings = []
    if missing:
        warnings.append(f"could not confidently map: {missing} -- needs human review before import")

    return SheetParseResult(sheet_name, "daily_production_log", out, mapping, missing, warnings)


def parse_article_costing_sheet(xls: pd.ExcelFile, sheet_name: str) -> SheetParseResult:
    raw = pd.read_excel(xls, sheet_name=sheet_name, header=None)
    hdr_row = find_header_row(raw, must_contain=("cloth", "article"))
    if hdr_row is None:
        return SheetParseResult(sheet_name, "unrecognized", pd.DataFrame(), warnings=["no header row found"])

    df = pd.read_excel(xls, sheet_name=sheet_name, header=hdr_row)
    df.columns = [normalize_colname(c) for c in df.columns]
    df = df.dropna(how="all")

    rename = {}
    for c in df.columns:
        if "cloth" in c and "amount" in c and "peace" in c:
            rename[c] = "cloth_cost_per_piece"
        elif "cloth" in c and "peace" in c:
            rename[c] = "cloth_meters_per_piece"
        elif c.startswith("cloth"):
            rename[c] = "cloth_type"
        elif "amout" in c:
            rename[c] = "cost_per_meter"
        elif "article" in c:
            rename[c] = "article_code"
        elif "steaching" in c or "stitching" in c:
            rename[c] = "stitching_cost_per_piece"
        elif "embroidery" in c:
            rename[c] = "embroidery_cost_per_piece"
        elif "washing" in c:
            rename[c] = "washing_cost_per_piece"
        elif c.strip() == "total":
            rename[c] = "total_cost_per_piece"
        elif "seal" in c:
            rename[c] = "sale_price_per_piece"
        elif "profit peace" in c or "profit piece" in c:
            rename[c] = "profit_per_piece"
        elif "total peace" in c or "total piece" in c:
            rename[c] = "total_pieces"
        elif "total profit" in c:
            rename[c] = "total_profit"
    df = df.rename(columns=rename)

    if "cloth_type" in df.columns:
        df["cloth_type"] = df["cloth_type"].ffill()
    keep_cols = [c for c in [
        "cloth_type", "article_code", "cost_per_meter", "cloth_meters_per_piece",
        "cloth_cost_per_piece", "stitching_cost_per_piece", "embroidery_cost_per_piece",
        "washing_cost_per_piece", "total_cost_per_piece", "sale_price_per_piece",
        "profit_per_piece", "total_pieces", "total_profit",
    ] if c in df.columns]
    df = df[keep_cols]
    if "total_pieces" in df.columns:
        df = df[df["total_pieces"].notna()]

    return SheetParseResult(sheet_name, "article_costing", df.reset_index(drop=True), rename)


def parse_ledger_sheet(xls: pd.ExcelFile, sheet_name: str) -> SheetParseResult:
    """Generic running-balance ledger: date, description(optional),
    amount(s), balance. Matches 'Contractor Invoice' and 'Balance Sheet'
    style sheets."""
    raw = pd.read_excel(xls, sheet_name=sheet_name, header=None)
    hdr_row = find_header_row(raw, must_contain=("date",))
    if hdr_row is None:
        return SheetParseResult(sheet_name, "unrecognized", pd.DataFrame(), warnings=["no header row found"])

    df = pd.read_excel(xls, sheet_name=sheet_name, header=hdr_row)
    df.columns = [normalize_colname(c) for c in df.columns]
    df = df.loc[:, [c for c in df.columns if c and not c.startswith("unnamed") and c != "s no"]]
    df["date"] = pd.to_datetime(df.get("date"), errors="coerce", dayfirst=True)
    df = df[df["date"].notna()].copy()

    return SheetParseResult(sheet_name, "ledger", df.reset_index(drop=True))


# --- category rules for expense ledgers -- deliberately simple/keyword based for MVP;
# revisit as a user-editable category list once there's more than one customer's data to generalize from.
EXPENSE_CATEGORY_RULES = {
    "Food & Refreshments": ["tea", "lunch", "drink", "food"],
    "Transport": ["transport", "fare", "petrol", "fuel"],
    "Wages & Advances": ["salary", "wage", "advance"],
    "Machine/Maintenance": ["machine", "belt", "spare", "repair"],
    "Transfers/Other": ["account", "sent"],
}


def categorize_expense(description: str) -> str:
    d = str(description).lower()
    for category, keywords in EXPENSE_CATEGORY_RULES.items():
        if any(k in d for k in keywords):
            return category
    return "Misc/Other"


def detect_and_parse_workbook(file_path: str) -> list[SheetParseResult]:
    """Entry point: given any uploaded .xlsx, detect each sheet's type by
    header signature and parse it accordingly. This is what makes 'just
    upload the new file and it works' actually true -- it doesn't assume
    sheet names, only header *shape*."""
    xls = pd.ExcelFile(file_path)
    results = []
    for sheet_name in xls.sheet_names:
        raw = pd.read_excel(xls, sheet_name=sheet_name, header=None, nrows=6)
        header_signature = " ".join(
            normalize_colname(v) for row in raw.itertuples(index=False) for v in row if pd.notna(v)
        )

        if "cloth" in header_signature and "article" in header_signature and "peace" in header_signature:
            results.append(parse_article_costing_sheet(xls, sheet_name))
        elif "date" in header_signature and ("total" in header_signature and "profit" in header_signature):
            results.append(parse_daily_production_sheet(xls, sheet_name))
        elif "date" in header_signature and "balance" in header_signature:
            results.append(parse_ledger_sheet(xls, sheet_name))
        else:
            results.append(SheetParseResult(sheet_name, "unrecognized", pd.DataFrame(),
                                              warnings=["sheet shape not recognized -- needs manual mapping"]))
    return results