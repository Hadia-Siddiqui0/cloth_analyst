"""
Run once per company after it's created, to seed its department list.

Usage:
    python -m app.db.seed <company_id>

This seeds Customer #1's real, confirmed department workflow: Cutting ->
5x Stitching -> Embroidery -> Packaging. Do NOT reuse this exact list for
a future customer without confirming their own departments first (Phase 8
of the roadmap generalizes this into a proper onboarding UI step instead
of a script) -- for now, this script IS that step.

Departments are tagged applies_to_stream="self_made" because discovery
(Day 2-3 audit) found his CMT contractor likely doesn't report
department-level detail back -- confirm this with him (open question #1/#2
from the data audit) before relying on it.
"""
import sys
import uuid

from app.db.session import SessionLocal
from app.models.department import Department

CUSTOMER_1_DEPARTMENTS = [
    ("Cutting", 1),
    ("Stitching 1", 2),
    ("Stitching 2", 3),
    ("Stitching 3", 4),
    ("Stitching 4", 5),
    ("Stitching 5", 6),
    ("Embroidery", 7),
    ("Packaging", 8),
]


def seed_departments(company_id: uuid.UUID):
    db = SessionLocal()
    try:
        existing = db.query(Department).filter(Department.company_id == company_id).count()
        if existing > 0:
            print(f"Company {company_id} already has {existing} departments -- skipping to avoid duplicates.")
            return

        for name, order in CUSTOMER_1_DEPARTMENTS:
            db.add(Department(
                company_id=company_id,
                name=name,
                sequence_order=order,
                applies_to_stream="self_made",
            ))
        db.commit()
        print(f"Seeded {len(CUSTOMER_1_DEPARTMENTS)} departments for company {company_id}.")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m app.db.seed <company_id>")
        sys.exit(1)
    seed_departments(uuid.UUID(sys.argv[1]))