"""Day 7 - customers, sales, payments (expenses already added in 0001)

Revision ID: 0003
Revises: 0002
Create Date: Day 7

Same caveat as 0001/0002: hand-written against the models, verify with
`alembic revision --autogenerate -m "verify against 0003"` once a real
Postgres connection is available -- should come back empty if accurate.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "customers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("customer_type", sa.String(50), nullable=True),
        sa.Column("contact_info", sa.String(500), nullable=True),
        sa.Column("credit_terms_days", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_customers_company_id", "customers", ["company_id"])

    op.create_table(
        "sales",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id"), nullable=True),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customers.id"), nullable=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 2), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("discount_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("total_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("channel", sa.String(255), nullable=True),
        sa.Column("source_upload_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("uploads.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_sales_company_id", "sales", ["company_id"])
    op.create_index("ix_sales_date", "sales", ["date"])

    op.create_table(
        "payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("sale_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sales.id"), nullable=True),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("paid_date", sa.Date(), nullable=True),
        sa.Column("status", sa.Enum(
            "upcoming", "due_soon", "due_today", "overdue", "paid", name="paymentstatus"),
            server_default="upcoming"),
        sa.Column("source_upload_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("uploads.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_payments_company_id", "payments", ["company_id"])
    op.create_index("ix_payments_due_date", "payments", ["due_date"])
    op.create_index("ix_payments_status", "payments", ["status"])


def downgrade():
    op.drop_table("payments")
    op.execute("DROP TYPE IF EXISTS paymentstatus")
    op.drop_table("sales")
    op.drop_table("customers")