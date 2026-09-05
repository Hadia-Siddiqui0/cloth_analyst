"""Day X - payables and notifications

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-03

Adds:
- payables table for supplier payment tracking (mirrors payments table)
- notifications table for reminders and CEO attention alerts

Hand-written against the models, verify with
`alembic revision --autogenerate -m "verify against 0005"` once a real
Postgres connection is available -- should come back empty if accurate.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    # payables table - mirrors payments but for suppliers
    op.create_table(
        "payables",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("suppliers.id"), nullable=False),
        sa.Column("purchase_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("purchases.id"), nullable=True),
        sa.Column("reference", sa.String(100), nullable=True),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("paid_date", sa.Date(), nullable=True),
        sa.Column("status", sa.Enum(
            "upcoming", "due_soon", "due_today", "overdue", "paid", name="payablestatus"),
            server_default="upcoming"),
        sa.Column("source_upload_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("uploads.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_payables_company_id", "payables", ["company_id"])
    op.create_index("ix_payables_due_date", "payables", ["due_date"])
    op.create_index("ix_payables_status", "payables", ["status"])
    op.create_index("ix_payables_supplier_id", "payables", ["supplier_id"])

    # notifications table for reminders and CEO attention
    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("type", sa.Enum(
            "payable_due_soon", "payable_due_today", "payable_overdue",
            "receivable_due_soon", "receivable_due_today", "receivable_overdue",
            "ceo_attention", name="notificationtype"),
            nullable=False),
        sa.Column("channel", sa.Enum(
            "in_app", "email", "push", name="notificationchannel"),
            server_default="in_app"),
        sa.Column("idempotency_key", sa.String(200), nullable=False, unique=True),
        sa.Column("reference_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reference_type", sa.String(50), nullable=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("message", sa.String(1000), nullable=False),
        sa.Column("is_read", sa.Boolean(), server_default="false"),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_notifications_company_id", "notifications", ["company_id"])
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_type", "notifications", ["type"])
    op.create_index("ix_notifications_is_read", "notifications", ["is_read"])
    op.create_index("ix_notifications_idempotency_key", "notifications", ["idempotency_key"], unique=True)
    op.create_index("ix_notifications_reference_id", "notifications", ["reference_id"])
    op.create_index("ix_notifications_created_at", "notifications", ["created_at"])


def downgrade():
    op.drop_table("notifications")
    op.execute("DROP TYPE IF EXISTS notificationtype")
    op.execute("DROP TYPE IF EXISTS notificationchannel")

    op.drop_table("payables")
    op.execute("DROP TYPE IF EXISTS payablestatus")