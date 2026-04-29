"""add idempotency columns to sms_messages and transactions

Revision ID: 20260429_0002
Revises: 20260429_0001
Create Date: 2026-04-29

"""

from alembic import op
import sqlalchemy as sa

revision = "20260429_0002"
down_revision = "20260429_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sms_messages", sa.Column("idempotency_key", sa.String(), nullable=True))
    op.create_index(
        "ix_sms_messages_idempotency_key", "sms_messages", ["idempotency_key"], unique=True
    )

    op.add_column("transactions", sa.Column("idempotency_key", sa.String(), nullable=True))
    op.create_index(
        "ix_transactions_idempotency_key", "transactions", ["idempotency_key"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ix_transactions_idempotency_key", table_name="transactions")
    op.drop_column("transactions", "idempotency_key")

    op.drop_index("ix_sms_messages_idempotency_key", table_name="sms_messages")
    op.drop_column("sms_messages", "idempotency_key")
