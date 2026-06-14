"""sell-in-service: add destination_location_id to product_order.

Revision ID: sli001
Revises:
Create Date: 2026-06-14 00:00:00.000000
"""

from __future__ import annotations

from alembic import op

revision = "sli001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE product_order "
        "ADD COLUMN IF NOT EXISTS destination_location_id UUID"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE product_order "
        "DROP COLUMN IF EXISTS destination_location_id"
    )
