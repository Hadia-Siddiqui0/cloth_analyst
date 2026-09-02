#!/usr/bin/env python
"""Test universal ingestion with various file formats."""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "backend"))

from app.services.universal_ingestion import parse_workbook_universal, get_sheet_summary

test_dir = Path(__file__).resolve().parents[1] / "data" / "test_universal"

test_files = [
    "test_A_standard.xlsx",
    "test_B_different_order.xlsx",
    "test_C_blank_rows.xlsx",
    "test_D_synonyms.xlsx",
    "test_E_multiple_sheets.xlsx",
    "test_F_csv.csv",
    "test_G_unknown.xlsx",
    "test_H_mixed_language.xlsx",
    "test_I_extra_columns.xlsx",
    "test_J_missing_columns.xlsx",
    "test_K_sales.xlsx",
    "test_L_inventory.xlsx",
    "test_M_purchases.xlsx",
]

print("=" * 80)
print("UNIVERSAL INGESTION TEST RESULTS")
print("=" * 80)

for test_file in test_files:
    file_path = test_dir / test_file
    print(f"\n{'='*80}")
    print(f"TEST: {test_file}")
    print(f"{'='*80}")

    try:
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

            print(f"  Preview (first 3 rows):")
            for i, row in enumerate(summary['preview'][:3]):
                print(f"    Row {i}: {row}")

    except Exception as e:
        print(f"  ERROR: {e}")

print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)