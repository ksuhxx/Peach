"""add users and item owners

Revision ID: 0003
Revises: 0002
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("cognito_sub", sa.String(length=64), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cognito_sub"),
    )

    op.create_index(
        "ix_users_cognito_sub",
        "users",
        ["cognito_sub"],
        unique=True,
    )

    op.add_column(
        "items",
        sa.Column(
            "owner_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )

    op.create_foreign_key(
        "fk_items_owner_id_users",
        "items",
        "users",
        ["owner_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.create_index(
        "ix_items_owner_id",
        "items",
        ["owner_id"],
    )

    op.alter_column(
        "items",
        "owner_id",
        nullable=False,
    )


def downgrade() -> None:
    op.drop_index("ix_items_owner_id", table_name="items")
    op.drop_constraint(
        "fk_items_owner_id_users",
        "items",
        type_="foreignkey",
    )
    op.drop_column("items", "owner_id")

    op.drop_index("ix_users_cognito_sub", table_name="users")
    op.drop_table("users")
