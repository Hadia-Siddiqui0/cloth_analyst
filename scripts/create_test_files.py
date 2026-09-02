#!/usr/bin/env python
"""Create test files for universal ingestion testing."""
import pandas as pd
import os

test_dir = r"F:\cloth_market.v2\the_code\clothing-business-analytics\data\test_universal"
os.makedirs(test_dir, exist_ok=True)

# Test A: Standard headers (similar to original)
df_a = pd.DataFrame({
    "Date": ["2024-01-15", "2024-01-16", "2024-01-17"],
    "Article": ["ART001", "ART002", "ART001"],
    "Quantity": [100, 200, 150],
    "Cost Total": [5000, 10000, 7500],
    "Sale Price/Piece": [60, 55, 60],
    "Revenue Total": [6000, 11000, 9000],
    "Profit": [1000, 1000, 1500],
})
df_a.to_excel(os.path.join(test_dir, "test_A_standard.xlsx"), index=False)
print("Created test_A_standard.xlsx")

# Test B: Different sheet name, different column order
df_b = pd.DataFrame({
    "Artikel": ["ART001", "ART002"],
    "Datum": ["2024-01-15", "2024-01-16"],
    "Gewinn": [1000, 1200],
    "Menge": [100, 150],
    "Gesamtkosten": [5000, 7500],
    "Umsatz": [6000, 8700],
    "VK/Stück": [60, 58],
})
with pd.ExcelWriter(os.path.join(test_dir, "test_B_different_order.xlsx")) as writer:
    df_b.to_excel(writer, sheet_name="Tägliche Produktion", index=False)
print("Created test_B_different_order.xlsx")

# Test C: Blank rows before header
df_c = pd.DataFrame({
    "Date": ["2024-01-15", "2024-01-16"],
    "Product": ["Shirt", "Pants"],
    "Qty": [50, 75],
    "Total Cost": [2500, 3750],
    "Sale Price": [60, 55],
    "Revenue": [3000, 4125],
    "Profit": [500, 375],
})
# Create with 3 blank rows at top
with pd.ExcelWriter(os.path.join(test_dir, "test_C_blank_rows.xlsx")) as writer:
    # Write blank rows first
    blank_df = pd.DataFrame([[""] * 7] * 3)
    blank_df.to_excel(writer, sheet_name="Data", index=False, header=False, startrow=0)
    df_c.to_excel(writer, sheet_name="Data", index=False, startrow=4)
print("Created test_C_blank_rows.xlsx")

# Test D: Different header names (synonyms)
df_d = pd.DataFrame({
    "Order Date": ["2024-01-15", "2024-01-16"],
    "Item Name": ["T-Shirt", "Jeans"],
    "Units": [200, 100],
    "Unit Cost": [25, 40],
    "Total Cost": [5000, 4000],
    "Selling Price": [35, 55],
    "Total Sales": [7000, 5500],
    "Margin": [2000, 1500],
})
df_d.to_excel(os.path.join(test_dir, "test_D_synonyms.xlsx"), index=False)
print("Created test_D_synonyms.xlsx")

# Test E: Multiple sheets
df_e1 = pd.DataFrame({
    "Date": ["2024-01-15"],
    "Article": ["ART001"],
    "Qty": [100],
    "Cost": [5000],
    "Price": [60],
    "Revenue": [6000],
    "Profit": [1000],
})
df_e2 = pd.DataFrame({
    "Cloth Type": ["Cotton", "Polyester"],
    "Article Code": ["ART001", "ART002"],
    "Meters/Piece": [1.5, 1.2],
    "Cost/Meter": [20, 15],
    "Stitching": [5, 4],
    "Total Cost/Piece": [35, 22],
    "Sale Price": [60, 55],
    "Profit/Piece": [25, 33],
})
df_e3 = pd.DataFrame({
    "Date": ["2024-01-15", "2024-01-16"],
    "Description": ["Office Rent", "Electricity"],
    "Amount": [10000, 5000],
    "Balance": [50000, 45000],
})
with pd.ExcelWriter(os.path.join(test_dir, "test_E_multiple_sheets.xlsx")) as writer:
    df_e1.to_excel(writer, sheet_name="Production Log", index=False)
    df_e2.to_excel(writer, sheet_name="Costing Sheet", index=False)
    df_e3.to_excel(writer, sheet_name="Expenses", index=False)
print("Created test_E_multiple_sheets.xlsx")

# Test F: CSV format
df_f = pd.DataFrame({
    "date": ["2024-01-15", "2024-01-16"],
    "product": ["Widget A", "Widget B"],
    "quantity": [100, 200],
    "revenue": [5000, 10000],
    "cost": [3000, 6000],
    "profit": [2000, 4000],
})
df_f.to_csv(os.path.join(test_dir, "test_F_csv.csv"), index=False)
print("Created test_F_csv.csv")

# Test G: Unknown/unrecognized structure
df_g = pd.DataFrame({
    "Random Col 1": ["A", "B", "C"],
    "Random Col 2": [1, 2, 3],
    "Random Col 3": [10.5, 20.3, 30.1],
    "Some Text": ["foo", "bar", "baz"],
})
df_g.to_excel(os.path.join(test_dir, "test_G_unknown.xlsx"), index=False)
print("Created test_G_unknown.xlsx")

# Test H: Mixed language headers (English + Urdu)
df_h = pd.DataFrame({
    "Date": ["2024-01-15", "2024-01-16"],
    "مصنوع": ["شیرٹ", "پینٹ"],  # Product in Urdu
    "تعداد": [50, 75],  # Quantity in Urdu
    "کھرچہ": [2500, 3750],  # Cost in Urdu
    "فروخت": [3000, 4125],  # Sale/Revenue in Urdu
    "منافع": [500, 375],  # Profit in Urdu
})
df_h.to_excel(os.path.join(test_dir, "test_H_mixed_language.xlsx"), index=False)
print("Created test_H_mixed_language.xlsx")

# Test I: Extra columns not in standard fields
df_i = pd.DataFrame({
    "Date": ["2024-01-15", "2024-01-16"],
    "Article": ["ART001", "ART002"],
    "Quantity": [100, 150],
    "Cost Total": [5000, 7500],
    "Sale Price": [60, 55],
    "Revenue": [6000, 8250],
    "Profit": [1000, 750],
    "Department": ["Cutting", "Sewing"],
    "Shift": ["Morning", "Evening"],
    "Supervisor": ["John", "Jane"],
    "Machine ID": ["M001", "M002"],
    "Notes": ["Normal", "Overtime"],
})
df_i.to_excel(os.path.join(test_dir, "test_I_extra_columns.xlsx"), index=False)
print("Created test_I_extra_columns.xlsx")

# Test J: Missing required columns
df_j = pd.DataFrame({
    "Date": ["2024-01-15", "2024-01-16"],
    "Product": ["Shirt", "Pants"],
    "Qty": [50, 75],
    # Missing cost, revenue, profit columns
})
df_j.to_excel(os.path.join(test_dir, "test_J_missing_columns.xlsx"), index=False)
print("Created test_J_missing_columns.xlsx")

# Test K: Sales data (customer-focused)
df_k = pd.DataFrame({
    "Date": ["2024-01-15", "2024-01-16"],
    "Customer": ["ABC Corp", "XYZ Ltd"],
    "Product": ["Widget A", "Widget B"],
    "Quantity": [100, 200],
    "Unit Price": [50, 45],
    "Total": [5000, 9000],
})
df_k.to_excel(os.path.join(test_dir, "test_K_sales.xlsx"), index=False)
print("Created test_K_sales.xlsx")

# Test L: Inventory data
df_l = pd.DataFrame({
    "Product": ["Fabric A", "Fabric B", "Thread"],
    "Stock In": [1000, 500, 200],
    "Stock Out": [300, 200, 50],
    "Balance": [700, 300, 150],
    "Unit": ["meters", "meters", "kg"],
})
df_l.to_excel(os.path.join(test_dir, "test_L_inventory.xlsx"), index=False)
print("Created test_L_inventory.xlsx")

# Test M: Purchase data
df_m = pd.DataFrame({
    "Date": ["2024-01-15", "2024-01-16"],
    "Supplier": ["Fabric Co", "Thread Inc"],
    "Product": ["Cotton Fabric", "Polyester Thread"],
    "Quantity": [500, 1000],
    "Unit Cost": [20, 5],
    "Total Cost": [10000, 5000],
})
df_m.to_excel(os.path.join(test_dir, "test_M_purchases.xlsx"), index=False)
print("Created test_M_purchases.xlsx")

print("\nAll test files created successfully!")