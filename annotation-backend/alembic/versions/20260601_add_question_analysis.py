"""Add question_analysis_annotation table

Revision ID: 20260601_question_analysis
Revises: 20260324_message_read_status
Create Date: 2026-06-01
"""

from alembic import op
import sqlalchemy as sa


revision = "20260601_question_analysis"
down_revision = "20260324_message_read_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "question_analysis_annotation",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("message_id", sa.Integer(), sa.ForeignKey("chat_messages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("annotator_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("trigger_marker", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("borderline", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("multiform", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("message_id", "annotator_id", name="uix_qa_message_annotator"),
    )
    op.create_index("ix_qa_annotation_message_annotator", "question_analysis_annotation", ["message_id", "annotator_id"])
    op.create_index("ix_qa_annotation_project", "question_analysis_annotation", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_qa_annotation_project", table_name="question_analysis_annotation")
    op.drop_index("ix_qa_annotation_message_annotator", table_name="question_analysis_annotation")
    op.drop_table("question_analysis_annotation")
