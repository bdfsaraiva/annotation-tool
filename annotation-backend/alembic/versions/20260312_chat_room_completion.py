"""Add chat room completion tracking

Revision ID: 20260312_chat_room_completion
Revises: 20260311_adjacency_pairs
Create Date: 2026-03-12
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260312_chat_room_completion"
down_revision = "20260311_adjacency_pairs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "chat_room_completions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("chat_room_id", sa.Integer(), sa.ForeignKey("chat_rooms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("annotator_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("is_completed", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("chat_room_id", "annotator_id", name="uix_chat_room_completion"),
    )
    op.create_index("ix_chat_room_completions_chat_room", "chat_room_completions", ["chat_room_id"])
    op.create_index("ix_chat_room_completions_project", "chat_room_completions", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_chat_room_completions_project", table_name="chat_room_completions")
    op.drop_index("ix_chat_room_completions_chat_room", table_name="chat_room_completions")
    op.drop_table("chat_room_completions")
