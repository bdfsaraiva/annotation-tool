"""Replace email with username for users

Revision ID: 20260312_username_only
Revises: 20260312_chat_room_completion
Create Date: 2026-03-12
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260312_username_only"
down_revision = "20260312_chat_room_completion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("username", sa.String(), nullable=True))

    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, email FROM users")).fetchall()
    used = set()
    for row in rows:
        email = row.email or ""
        base = email.split("@")[0] if "@" in email else email
        base = base.strip() or f"user{row.id}"
        username = base if len(base) >= 3 else f"user{row.id}"

        candidate = username
        counter = 1
        while candidate in used:
            candidate = f"{username}_{counter}"
            counter += 1

        used.add(candidate)
        conn.execute(
            sa.text("UPDATE users SET username = :username WHERE id = :id"),
            {"username": candidate, "id": row.id}
        )

    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("username", nullable=False)
        batch_op.drop_column("email")
        batch_op.create_unique_constraint("uq_users_username", ["username"])


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("email", sa.String(), nullable=True))

    op.execute("UPDATE users SET email = username")

    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("email", nullable=False)
        batch_op.drop_constraint("uq_users_username", type_="unique")
        batch_op.drop_column("username")
        batch_op.create_unique_constraint("uq_users_email", ["email"])
