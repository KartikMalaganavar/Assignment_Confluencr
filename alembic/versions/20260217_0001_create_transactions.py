"""create transactions table

Revision ID: 20260217_0001
Revises:
Create Date: 2026-02-17 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260217_0001"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


transaction_status = postgresql.ENUM(
    "PROCESSING",
    "PROCESSED",
    "FAILED",
    name="transaction_status",
    create_type=False,
)


def upgrade() -> None:
    transaction_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("transaction_id", sa.String(length=128), nullable=False),
        sa.Column("source_account", sa.String(length=128), nullable=False),
        sa.Column("destination_account", sa.String(length=128), nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("status", transaction_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("duplicate_conflict_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_conflict_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("transaction_id"),
    )
    op.create_index("ix_transactions_transaction_id", "transactions", ["transaction_id"], unique=True)
    op.create_index("ix_transactions_status", "transactions", ["status"], unique=False)
    op.create_index(
        "ix_transactions_status_processing_started_at",
        "transactions",
        ["status", "processing_started_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_transactions_status_processing_started_at", table_name="transactions")
    op.drop_index("ix_transactions_status", table_name="transactions")
    op.drop_index("ix_transactions_transaction_id", table_name="transactions")
    op.drop_table("transactions")
    transaction_status.drop(op.get_bind(), checkfirst=True)
