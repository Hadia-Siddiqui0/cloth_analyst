"""
Tests the ingestion engine against the real sample file. This is the
piece the whole "just upload a new file and it works" promise depends
on, so it gets tested against real data, not synthetic fixtures.
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "backend"))

from app.services.ingestion_service import detect_and_parse_workbook

SAMPLE_FILE = str(Path(__file__).resolve().parents[1] / "data" / "sample" / "Garment_12_updated.xlsx")


def test_detects_all_sheets():
    results = detect_and_parse_workbook(SAMPLE_FILE)
    sheet_names = {r.sheet_name for r in results}
    assert "CMT" in sheet_names
    assert "Sheet4" in sheet_names


def test_daily_production_log_parses_self_made_sheet():
    results = detect_and_parse_workbook(SAMPLE_FILE)
    self_made = next(r for r in results if r.sheet_name.strip() == "Self Made")
    assert self_made.sheet_type == "daily_production_log"
    assert len(self_made.dataframe) > 0
    assert "date" in self_made.dataframe.columns
    assert "profit" in self_made.dataframe.columns
    # forward-fill should mean no nulls in article/quantity after row 1
    assert self_made.dataframe["quantity"].isna().sum() == 0


def test_article_costing_sheet_parses_correctly():
    results = detect_and_parse_workbook(SAMPLE_FILE)
    costing = next(r for r in results if r.sheet_name == "Sheet4")
    assert costing.sheet_type == "article_costing"
    df = costing.dataframe
    assert "cloth_type" in df.columns
    assert "cloth_meters_per_piece" in df.columns
    # regression check for the column-collision bug found during dev:
    # cloth_cost_per_piece must differ from cloth_meters_per_piece
    assert not df["cloth_cost_per_piece"].equals(df["cloth_meters_per_piece"])


def test_footer_and_note_rows_are_excluded():
    results = detect_and_parse_workbook(SAMPLE_FILE)
    self_made = next(r for r in results if r.sheet_name.strip() == "Self Made")
    # the "Total" footer row and "Note" text block must not appear as data rows
    assert self_made.dataframe["date"].notna().all()
