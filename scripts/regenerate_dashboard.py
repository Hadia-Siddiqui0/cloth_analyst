"""
Regenerates the Command Center demo dashboard from any garment-factory
Excel file, using the exact same parsing logic as the real backend
(app/services/ingestion_service.py -- imported directly, not duplicated).

This is the bridge between "here's a demo built on old data" and "just
upload your real file and it works": today, that means running this
script against a new file. Once the backend is deployed (Day 8+
infrastructure work, separate from this), the same ingestion_service
code runs automatically behind the /api/uploads endpoint and the
frontend dashboard reads live from the database instead of a
regenerated static file -- but the parsing/calculation logic doesn't
change at all between the two, which is the whole point.

Usage:
    python scripts/regenerate_dashboard.py [path/to/new_file.xlsx]

Defaults to the original sample file if no argument is given.
"""
import sys
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

# Imported directly to avoid pulling in the full app (fastapi/sqlalchemy
# aren't installed in every environment this script might run in) --
# this is the same file the real API endpoint uses.
import importlib.util
spec = importlib.util.spec_from_file_location(
    "ingestion_service", ROOT / "backend" / "app" / "services" / "ingestion_service.py"
)
ingestion_service = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ingestion_service)

import pandas as pd

# --- confirmed business context (from the CEO's answers -- update this
# block, not the parsing logic, as more gets confirmed) ---
CONFIRMED_CONTEXT = {
    "current_production_stream": "self_made",  # he confirmed: currently self-made / in-house only
    "department_model_applies_to": "self_made",  # confirmed: 5-department split is in-house only
    "sales_customers_source": "separate paper register",  # not yet digitized
    "purchases_source": "separate paper register",  # not yet digitized
    "inventory_tracked": "all types, but on paper -- not yet digitized",
    "article_costing_current": False,  # he confirmed Sheet4's costing is OUTDATED
    "daily_production_target_current": False,  # he confirmed "more than 2500/day" now, exact figure unknown
}


def clean(v):
    if isinstance(v, float) and math.isnan(v):
        return None
    return v


def build_dataset(xlsx_path: str) -> dict:
    results = ingestion_service.detect_and_parse_workbook(xlsx_path)

    prod_frames = [r.dataframe for r in results if r.sheet_type == "daily_production_log" and not r.dataframe.empty]
    for r in results:
        if r.sheet_type == "daily_production_log" and not r.dataframe.empty:
            r.dataframe["source_sheet"] = r.sheet_name.strip()
            name_lower = r.sheet_name.lower()
            if "self" in name_lower:
                r.dataframe["stream"] = "self_made"
            elif "cmt" in name_lower:
                r.dataframe["stream"] = "cmt"
            else:
                r.dataframe["stream"] = "unspecified"
    prod = pd.concat([r.dataframe for r in results if r.sheet_type == "daily_production_log" and not r.dataframe.empty],
                      ignore_index=True) if prod_frames else pd.DataFrame()

    costing_results = [r for r in results if r.sheet_type == "article_costing" and not r.dataframe.empty]
    costing = costing_results[0].dataframe if costing_results else pd.DataFrame()

    ledger_results = [r for r in results if r.sheet_type == "ledger" and not r.dataframe.empty]
    contractor = pd.DataFrame()
    expenses_frames = []
    for r in ledger_results:
        cols = set(r.dataframe.columns)
        name_lower = r.sheet_name.lower()
        if "contractor" in name_lower or ({"amount", "receive", "balance"} <= cols):
            contractor = r.dataframe
        else:
            expenses_frames.append(r.dataframe)
    expenses = pd.concat(expenses_frames, ignore_index=True) if expenses_frames else pd.DataFrame()

    # --- WHY did profit change? Compare the two most recent weeks with
    # real activity, and attribute the cost movement to whichever
    # overhead category moved the most -- using the itemized breakdown
    # captured per row, not just the total. This is a real, verifiable
    # comparison (diagnostic analytics), not a generated narrative --
    # every number here is directly computed from the file. ---
    current_stream_frames = [r.dataframe for r in results
                              if r.sheet_type == "daily_production_log" and not r.dataframe.empty
                              and "self" in r.sheet_name.lower()]

    why_analysis = None
    if current_stream_frames:
        current = pd.concat(current_stream_frames, ignore_index=True)
        current["date"] = pd.to_datetime(current["date"])
        current["week"] = current["date"].dt.to_period("W").apply(lambda p: p.start_time)

        weekly_totals = current.groupby("week").agg(
            revenue=("revenue_total", "sum"),
            cost=("cost_total", "sum"),
            profit=("profit", "sum"),
        ).reset_index()
        weekly_totals = weekly_totals[weekly_totals["profit"] != 0].sort_values("week")

        if len(weekly_totals) >= 2:
            weekly_totals = weekly_totals.reset_index(drop=True)
            latest = weekly_totals.iloc[-1]
            prior = weekly_totals.iloc[-2]
            comparison_label = "most recent two weeks"

            # if the most recent two weeks happen to be flat (a real
            # possibility with a steady-state batch, as it turned out to
            # be here), fall back to the pair with the biggest profit
            # swing anywhere in the data instead of reporting "nothing
            # changed" as the headline finding.
            if abs(float(latest["profit"] - prior["profit"])) < 1 and len(weekly_totals) > 2:
                best_pair = None
                best_swing = 0
                for i in range(1, len(weekly_totals)):
                    swing = abs(float(weekly_totals.iloc[i]["profit"] - weekly_totals.iloc[i-1]["profit"]))
                    if swing > best_swing:
                        best_swing = swing
                        best_pair = i
                if best_pair is not None and best_swing > 1:
                    latest = weekly_totals.iloc[best_pair]
                    prior = weekly_totals.iloc[best_pair - 1]
                    comparison_label = "most significant week-over-week change found in your data"

            revenue_change = float(latest["revenue"] - prior["revenue"])
            cost_change = float(latest["cost"] - prior["cost"])
            profit_change = float(latest["profit"] - prior["profit"])

            # Sum each overhead category across all rows in each week to
            # find which single category moved the most.
            def week_category_totals(week_start):
                rows = current[current["week"] == week_start]
                totals = {}
                for bd in rows.get("cost_breakdown", []):
                    if not isinstance(bd, dict):
                        continue
                    for cat, val in bd.items():
                        if val is None or not isinstance(val, (int, float)):
                            continue
                        totals[cat] = totals.get(cat, 0) + val
                return totals

            latest_cats = week_category_totals(latest["week"])
            prior_cats = week_category_totals(prior["week"])
            all_cats = set(latest_cats) | set(prior_cats)
            cat_changes = {c: latest_cats.get(c, 0) - prior_cats.get(c, 0) for c in all_cats}
            # only name a "top driver" if something actually moved --
            # naming one when everything is flat (a real possibility with
            # steady-state batches, as it turned out to be in this file)
            # would be presenting noise as an explanation.
            meaningful_changes = {c: v for c, v in cat_changes.items() if abs(v) > 1}
            top_driver = max(meaningful_changes.items(), key=lambda kv: abs(kv[1])) if meaningful_changes else None

            why_analysis = {
                "latest_week": latest["week"].strftime("%b %d"),
                "prior_week": prior["week"].strftime("%b %d"),
                "comparison_label": comparison_label,
                "revenue_change": clean(round(revenue_change)),
                "cost_change": clean(round(cost_change)),
                "profit_change": clean(round(profit_change)),
                "top_cost_driver": top_driver[0].strip() if top_driver else None,
                "top_cost_driver_change": clean(round(top_driver[1])) if top_driver else None,
                "flat_week": abs(revenue_change) < 1 and abs(cost_change) < 1,
            }


    daily_series = {}
    if not prod.empty:
        prod["date_str"] = pd.to_datetime(prod["date"]).dt.strftime("%Y-%m-%d")
        grouped = prod.groupby(["source_sheet", "date_str"], as_index=False)[["cost_total", "revenue_total", "profit"]].sum()
        for sheet in grouped["source_sheet"].unique():
            d = grouped[grouped["source_sheet"] == sheet].sort_values("date_str")
            daily_series[sheet] = {
                "dates": d["date_str"].tolist(),
                "cost": [clean(x) for x in d["cost_total"].round(0).tolist()],
                "revenue": [clean(x) for x in d["revenue_total"].round(0).tolist()],
                "profit": [clean(x) for x in d["profit"].round(0).tolist()],
            }

    # --- weekly profit series for the CURRENT stream only (self-made) --
    # this is what a non-technical reader actually sees: one bar per week,
    # green if that week made money, red if it lost money. Daily noise
    # and multi-line comparisons are exactly what's hard to read, so this
    # is deliberately the only line/bar trend chart in the dashboard.
    weekly_profit = {"labels": [], "profit": []}
    if current_stream_frames:
        current = pd.concat(current_stream_frames, ignore_index=True)
        current["date"] = pd.to_datetime(current["date"])
        weekly = current.set_index("date").resample("W")["profit"].sum().reset_index()
        weekly = weekly[weekly["profit"] != 0]
        weekly_profit = {
            "labels": [f"Week of {d.strftime('%b %d')}" for d in weekly["date"]],
            "profit": [clean(round(x)) for x in weekly["profit"].tolist()],
        }

    # --- contractor balance series (only meaningful if CMT data present) ---
    contractor_series = {"dates": [], "balance": []}
    if not contractor.empty and "balance" in contractor.columns:
        c = contractor[contractor["balance"].notna()].sort_values("date")
        contractor_series = {
            "dates": pd.to_datetime(c["date"]).dt.strftime("%Y-%m-%d").tolist(),
            "balance": [clean(x) for x in c["balance"].tolist()],
        }

    # --- article costing table ---
    costing_records = []
    if not costing.empty:
        keep = [c for c in ["cloth_type", "total_cost_per_piece", "sale_price_per_piece",
                             "profit_per_piece", "total_pieces", "total_profit"] if c in costing.columns]
        costing_records = [{k: clean(v) for k, v in r.items()} for r in costing[keep].round(1).to_dict("records")]

    # --- expense categorization ---
    expense_categories = {}
    if not expenses.empty and "used" in expenses.columns:
        expenses = expenses.copy()
        expenses["used"] = expenses["used"].fillna(0)
        desc_col = "description" if "description" in expenses.columns else None
        if desc_col:
            expenses["category"] = expenses[desc_col].apply(ingestion_service.categorize_expense)
            cat = expenses.groupby("category")["used"].sum().sort_values(ascending=False).round(0)
            expense_categories = {k: clean(v) for k, v in cat.to_dict().items()}

    # --- KPIs ---
    total_revenue = float(prod["revenue_total"].sum()) if not prod.empty else 0
    total_cost = float(prod["cost_total"].sum()) if not prod.empty else 0
    total_profit = float(prod["profit"].sum()) if not prod.empty else 0
    contractor_balance = None
    contractor_trend = None  # "down" (good, being paid off) | "up" | None
    if not contractor.empty and "balance" in contractor.columns:
        nz = contractor[contractor["balance"].notna()].sort_values("date")
        if len(nz):
            contractor_balance = float(nz.iloc[-1]["balance"])
            if len(nz) > 1:
                first_balance = float(nz.iloc[0]["balance"])
                if contractor_balance < first_balance:
                    contractor_trend = "down"
                elif contractor_balance > first_balance:
                    contractor_trend = "up"
    total_expenses = float(expenses["used"].sum()) if (not expenses.empty and "used" in expenses.columns) else None

    date_min = pd.to_datetime(prod["date"]).min().strftime("%b %Y") if not prod.empty else "—"
    date_max = pd.to_datetime(prod["date"]).max().strftime("%b %Y") if not prod.empty else "—"

    kpis = {
        "total_revenue": round(total_revenue),
        "total_cost": round(total_cost),
        "total_profit": round(total_profit),
        "contractor_balance": round(contractor_balance) if contractor_balance is not None else None,
        "contractor_trend": contractor_trend,
        "total_expenses": round(total_expenses) if total_expenses is not None else None,
        "n_records": int(len(prod)),
        "date_min": date_min,
        "date_max": date_max,
        "n_articles": int(len(costing)),
    }

    # --- which product drags profitability down most, if any lose money ---
    lowest_margin_product = None
    if costing_records:
        losing = [r for r in costing_records if (r.get("profit_per_piece") or 0) < 0]
        pool = losing if losing else costing_records
        lowest = min(pool, key=lambda r: r.get("profit_per_piece") or 0)
        lowest_margin_product = {
            "cloth_type": lowest.get("cloth_type"),
            "profit_per_piece": lowest.get("profit_per_piece"),
            "is_losing_money": (lowest.get("profit_per_piece") or 0) < 0,
        }

    return {
        "daily_series": daily_series,
        "weekly_profit": weekly_profit,
        "why_analysis": why_analysis,
        "lowest_margin_product": lowest_margin_product,
        "contractor_series": contractor_series,
        "costing": costing_records,
        "expense_categories": expense_categories,
        "kpis": kpis,
        "context": CONFIRMED_CONTEXT,
    }


def render_html(data: dict) -> str:
    template_path = ROOT / "scripts" / "dashboard_template.html"
    template = template_path.read_text()
    return template.replace("@@DATA_JSON@@", json.dumps(data))


def main():
    input_path = sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "data" / "sample" / "Garment_12_updated.xlsx")
    output_path = ROOT / "dashboard.html"

    print(f"Parsing {input_path} ...")
    data = build_dataset(input_path)
    html = render_html(data)
    output_path.write_text(html)
    print(f"Dashboard regenerated: {output_path}")
    print(f"  {data['kpis']['n_records']} production records, {data['kpis']['n_articles']} articles costed")


if __name__ == "__main__":
    main()