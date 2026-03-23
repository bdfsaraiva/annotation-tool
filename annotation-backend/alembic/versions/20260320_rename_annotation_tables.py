"""Rename annotation tables

Revision ID: 20260320_rename_annotation_tables
Revises: 20260312_username_only
Create Date: 2026-03-20
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "20260320_rename_annotation_tables"
down_revision = "20260312_username_only"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.rename_table("annotations", "disentanglement_annotation")
    op.rename_table("adjacency_pairs", "adj_pairs_annotation")


def downgrade() -> None:
    op.rename_table("adj_pairs_annotation", "adjacency_pairs")
    op.rename_table("disentanglement_annotation", "annotations")