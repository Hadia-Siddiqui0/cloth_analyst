#!/usr/bin/env python
"""Analyze the real customer stitching CSV with universal ingestion."""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "backend"))

from app.services.universal_ingestion import parse_workbook_universal, get_sheet_summary

file_path = Path(__file__).resolve().parents[1] / "data" / "real" / "stitching1.csv"

print("=" * 80)
print("ANALYZING REAL CUSTOMER STITCHING DATA")
print("=" * 80)

results = parse_workbook_universal(str(file_path))

for result in results:
    summary = get_sheet_summary(result)

    print(f"\nSheet: {summary['sheet_name']}")
    print(f"  Detected Type: {summary['sheet_type']} (confidence: {summary['confidence']:.0%})")
    print(f"  Row Count: {summary['row_count']}")
    print(f"  Suggested Mappings: {summary['suggested_mappings']}")

    if summary['warnings']:
        print(f"  Warnings:")
        for w in summary['warnings']:
            print(f"    [WARN] {w}")

    print(f"  Columns:")
    for col in summary['columns']:
        mapping_info = f" -> {col['suggested_mapping']}" if col['suggested_mapping'] else " (no mapping)"
        print(f"    - {col['original_name']}: type={col['detected_type']}, conf={col['confidence']:.0%}{mapping_info}")

    print(f"  Preview (all rows):")
    for i, row in enumerate(summary['preview']):
        print(f"    Row {i}: {row}")

print("\n" + "=" * 80)
print("ANALYSIS COMPLETE")
print("=" * 80)