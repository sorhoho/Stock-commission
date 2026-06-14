"""sell-out-service: POS session, return flow, and payment fields.

Adds pos_session_id / payment_method / payment_reference to sale_transaction,
creates pos_session, return_transaction, return_transaction_item tables.

Revision ID: slo001
Revises:
Create Date: 2026-06-14 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "slo001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add new columns to sale_transaction (guard with IF NOT EXISTS).
    op.execute(
        "ALTER TABLE sale_transaction "
        "ADD COLUMN IF NOT EXISTS pos_session_id UUID"
    )
    op.execute(
        "ALTER TABLE sale_transaction "
        "ADD COLUMN IF NOT EXISTS payment_method VARCHAR(32)"
    )
    op.execute(
        "ALTER TABLE sale_transaction "
        "ADD COLUMN IF NOT EXISTS payment_reference VARCHAR(128)"
    )

    # 2. Create pos_session table.
    op.execute("""
        CREATE TABLE IF NOT EXISTS pos_session (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            terminal_id VARCHAR(64) NOT NULL,
            dealer_party_id UUID NOT NULL,
            opened_by VARCHAR(256) NOT NULL,
            opened_at VARCHAR(32) NOT NULL,
            closed_at VARCHAR(32),
            status VARCHAR(16) NOT NULL DEFAULT 'OPEN',
            opening_cash FLOAT NOT NULL DEFAULT 0.0,
            closing_cash FLOAT,
            total_transactions INTEGER NOT NULL DEFAULT 0,
            total_amount FLOAT NOT NULL DEFAULT 0.0,
            tenant_id VARCHAR(64) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_pos_session_terminal_id ON pos_session (terminal_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_pos_session_dealer_party_id ON pos_session (dealer_party_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_pos_session_tenant_id ON pos_session (tenant_id)")

    # 3. Create return_transaction table.
    op.execute("""
        CREATE TABLE IF NOT EXISTS return_transaction (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            return_number VARCHAR(64) NOT NULL UNIQUE,
            original_transaction_id UUID REFERENCES sale_transaction(id) ON DELETE SET NULL,
            return_reason VARCHAR(512) NOT NULL,
            status VARCHAR(16) NOT NULL DEFAULT 'PENDING',
            returned_by VARCHAR(256) NOT NULL,
            returned_at VARCHAR(32) NOT NULL,
            tenant_id VARCHAR(64) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_return_transaction_return_number ON return_transaction (return_number)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_return_transaction_original_transaction_id ON return_transaction (original_transaction_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_return_transaction_tenant_id ON return_transaction (tenant_id)")

    # 4. Create return_transaction_item table.
    op.execute("""
        CREATE TABLE IF NOT EXISTS return_transaction_item (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            return_transaction_id UUID NOT NULL REFERENCES return_transaction(id) ON DELETE CASCADE,
            product_id UUID NOT NULL,
            quantity INTEGER NOT NULL,
            serial_numbers JSONB NOT NULL DEFAULT '[]',
            condition VARCHAR(16) NOT NULL DEFAULT 'GOOD',
            tenant_id VARCHAR(64) NOT NULL
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_return_transaction_item_return_transaction_id "
        "ON return_transaction_item (return_transaction_id)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS return_transaction_item")
    op.execute("DROP TABLE IF EXISTS return_transaction")
    op.execute("DROP TABLE IF EXISTS pos_session")
    op.execute("ALTER TABLE sale_transaction DROP COLUMN IF EXISTS payment_reference")
    op.execute("ALTER TABLE sale_transaction DROP COLUMN IF EXISTS payment_method")
    op.execute("ALTER TABLE sale_transaction DROP COLUMN IF EXISTS pos_session_id")
