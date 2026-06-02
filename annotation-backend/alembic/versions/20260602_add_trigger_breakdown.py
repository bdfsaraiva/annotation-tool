"""Add trigger breakdown columns to question_analysis_annotation

Revision ID: 20260602_trigger_breakdown
Revises: 20260601_question_analysis
Create Date: 2026-06-02
"""

from alembic import op
import sqlalchemy as sa


revision = "20260602_trigger_breakdown"
down_revision = "20260601_question_analysis"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("question_analysis_annotation", sa.Column("trigger_primary", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("question_analysis_annotation", sa.Column("trigger_f2", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("question_analysis_annotation", sa.Column("trigger_f3", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("question_analysis_annotation", sa.Column("trigger_f4", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("question_analysis_annotation", sa.Column("trigger_f5", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("question_analysis_annotation", sa.Column("trigger_f6", sa.Boolean(), nullable=False, server_default="false"))


def downgrade() -> None:
    op.drop_column("question_analysis_annotation", "trigger_f6")
    op.drop_column("question_analysis_annotation", "trigger_f5")
    op.drop_column("question_analysis_annotation", "trigger_f4")
    op.drop_column("question_analysis_annotation", "trigger_f3")
    op.drop_column("question_analysis_annotation", "trigger_f2")
    op.drop_column("question_analysis_annotation", "trigger_primary")
