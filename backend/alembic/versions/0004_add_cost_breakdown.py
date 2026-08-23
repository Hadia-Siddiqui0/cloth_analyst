"""Add cost_breakdown JSON column to production_runs

Revision ID: 0004
Revises: 0003
Create Date: frontend integration work

Needed so the real backend can do the same driver-level "why did cost
change" analysis the demo script does -- without this, cost_total is
all that's stored and there's no way to attribute a change to a
specific overhead category (Elect, Rent, Helper, etc.).
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("production_runs", sa.Column("cost_breakdown", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("production_runs", "cost_breakdown")