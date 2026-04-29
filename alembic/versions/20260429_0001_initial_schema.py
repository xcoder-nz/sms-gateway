"""initial schema

Revision ID: 20260429_0001
Revises: 
Create Date: 2026-04-29

"""

from alembic import op
import sqlalchemy as sa

revision = "20260429_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("full_name", sa.String(), nullable=False),
        sa.Column("phone_number", sa.String(), nullable=False),
        sa.Column("national_id", sa.String(), nullable=True),
        sa.Column("pin_hash", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )
    op.create_index("ix_users_phone_number", "users", ["phone_number"], unique=True)
    op.create_index("ix_users_id", "users", ["id"], unique=False)

    op.create_table(
        "merchant_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, unique=True),
        sa.Column("merchant_code", sa.String(), nullable=False, unique=True),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("settlement_mode", sa.String(), nullable=False, server_default="simulated"),
        sa.Column("receipt_phone_number", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )

    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("reference", sa.String(), nullable=False, unique=True),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("from_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("to_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("merchant_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency", sa.String(), nullable=False, server_default="AFN"),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("rejection_reason", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )

    op.create_table(
        "wallets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, unique=True),
        sa.Column("currency", sa.String(), nullable=False, server_default="AFN"),
        sa.Column("balance", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("wallet_status", sa.String(), nullable=False, server_default="active"),
        sa.Column("last_updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )

    op.create_table(
        "sms_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("direction", sa.String(), nullable=False),
        sa.Column("from_number", sa.String(), nullable=False),
        sa.Column("to_number", sa.String(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("provider_message_id", sa.String(), nullable=True),
        sa.Column("delivery_status", sa.String(), nullable=False, server_default="queued"),
        sa.Column("linked_transaction_id", sa.Integer(), sa.ForeignKey("transactions.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("sms_messages")
    op.drop_table("wallets")
    op.drop_table("transactions")
    op.drop_table("merchant_profiles")
    op.drop_index("ix_users_id", table_name="users")
    op.drop_index("ix_users_phone_number", table_name="users")
    op.drop_table("users")
    op.drop_table("audit_events")
