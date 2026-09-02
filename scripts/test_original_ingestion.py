#!/usr/bin/env python
"""Test original ingestion service with the original garment file."""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "backend"))

from app.services.ingestion_service import detect_and_parse_workbook

file_path = Path(__file__).resolve().parents[1] / "data" / "sample" / "Garment_12_updated.xlsx"

print("=" * 80)
print("TESTING ORIGINAL INGESTION SERVICE WITH GARMENT FILE")
print("=" * 80)

results = detect_and_parse_workbook(str(file_path))

for result in results:
    print(f"\nSheet: {result.sheet_name}")
    print(f"  Detected Type: {result.sheet_type}")
    print(f"  Row Count: {len(result.dataframe)}")
    print(f"  Column Mapping: {result.column_mapping}")
    print(f"  Missing Fields: {result.missing_fields}")
    print(f"  Warnings: {result.warnings}")
    print(f"  Columns: {list(result.dataframe.columns)}")
    print(f"  Preview (first 3 rows):")
    for i, row in result.dataframe.head(3).iterrows():
        print(f"    Row {i}: {dict(row)}")

print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)