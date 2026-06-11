"""Add is_question column to question_analysis_annotation

Revision ID: 20260611_is_question
Revises: 20260602_trigger_breakdown
Create Date: 2026-06-11
"""

from alembic import op
import sqlalchemy as sa


revision = "20260611_is_question"
down_revision = "20260602_trigger_breakdown"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "question_analysis_annotation",
        sa.Column("is_question", sa.Boolean(), nullable=False, server_default="false"),
    )
    # Existing rows were created as question annotations, so backfill them as such.
    op.execute("UPDATE question_analysis_annotation SET is_question = true")


def downgrade() -> None:
    op.drop_column("question_analysis_annotation", "is_question")
