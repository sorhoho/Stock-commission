"""Product catalog: initial schema with full telco product type fields.

Revision ID: cat001
Revises:
Create Date: 2026-06-10 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "cat001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "product",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("sku", sa.String(64), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("barcode", sa.String(64), nullable=False),
        sa.Column("product_type", sa.String(64), nullable=False),
        sa.Column("category", sa.String(128), nullable=False),
        sa.Column("brand", sa.String(128), nullable=True),
        sa.Column("model_number", sa.String(256), nullable=True),
        sa.Column("unit_price", sa.Float, nullable=False),
        sa.Column("denomination", sa.Float, nullable=True),
        sa.Column("tax_rate", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("commission_eligible", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("requires_serial_tracking", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("specifications", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("barcode", "tenant_id", name="uq_product_barcode_tenant"),
    )
    op.create_index("ix_product_sku", "product", ["sku"])
    op.create_index("ix_product_name", "product", ["name"])
    op.create_index("ix_product_product_type", "product", ["product_type"])
    op.create_index("ix_product_category", "product", ["category"])
    op.create_index("ix_product_brand", "product", ["brand"])
    op.create_index("ix_product_tenant_id", "product", ["tenant_id"])


def downgrade() -> None:
    op.drop_table("product")
