"""Inventory requirements: goods_receipt, resource, resource_characteristic,
stock_reconciliation, stock_reconciliation_item tables.

Revision ID: inv001
Revises:
Create Date: 2026-06-06 00:00:00.000000
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "inv001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "goods_receipt",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("grn_number", sa.String(100), nullable=False),
        sa.Column("supplier_reference", sa.String(200), nullable=True),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("location_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantity_received", sa.Integer, nullable=False),
        sa.Column("unit_cost", sa.Float, nullable=True),
        sa.Column("received_by", sa.String(255), nullable=False),
        sa.Column("received_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["location_id"], ["location.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("grn_number", "tenant_id", name="uq_goods_receipt_grn_tenant"),
    )
    op.create_index("ix_goods_receipt_product_id", "goods_receipt", ["product_id"])
    op.create_index("ix_goods_receipt_location_id", "goods_receipt", ["location_id"])
    op.create_index("ix_goods_receipt_grn_number", "goods_receipt", ["grn_number"])

    op.create_table(
        "resource",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("resource_name", sa.String(255), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("inventory_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("location_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="AVAILABLE"),
        sa.Column("batch_reference", sa.String(200), nullable=True),
        sa.Column("supplier_reference", sa.String(200), nullable=True),
        sa.Column("allocated_to", sa.String(255), nullable=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["inventory_id"], ["product_inventory.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["location_id"], ["location.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_resource_product_id", "resource", ["product_id"])
    op.create_index("ix_resource_inventory_id", "resource", ["inventory_id"])
    op.create_index("ix_resource_status", "resource", ["status"])
    op.create_index("ix_resource_resource_type", "resource", ["resource_type"])

    op.create_table(
        "resource_characteristic",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("value", sa.String(255), nullable=False),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.ForeignKeyConstraint(["resource_id"], ["resource.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("name", "value", "tenant_id", name="uq_resource_characteristic_nvt"),
    )
    op.create_index("ix_resource_characteristic_resource_id", "resource_characteristic", ["resource_id"])
    op.create_index("ix_resource_characteristic_name", "resource_characteristic", ["name"])
    op.create_index("ix_resource_characteristic_value", "resource_characteristic", ["value"])

    op.create_table(
        "stock_reconciliation",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("location_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reconciliation_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="DRAFT"),
        sa.Column("counted_by", sa.String(255), nullable=False),
        sa.Column("approved_by", sa.String(255), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["location_id"], ["location.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_stock_reconciliation_location_id", "stock_reconciliation", ["location_id"])
    op.create_index("ix_stock_reconciliation_status", "stock_reconciliation", ["status"])

    op.create_table(
        "stock_reconciliation_item",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("reconciliation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("system_quantity", sa.Integer, nullable=False),
        sa.Column("physical_quantity", sa.Integer, nullable=False),
        sa.Column("variance", sa.Integer, nullable=False),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.ForeignKeyConstraint(
            ["reconciliation_id"], ["stock_reconciliation.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        "ix_stock_reconciliation_item_reconciliation_id",
        "stock_reconciliation_item",
        ["reconciliation_id"],
    )


def downgrade() -> None:
    op.drop_table("stock_reconciliation_item")
    op.drop_table("stock_reconciliation")
    op.drop_table("resource_characteristic")
    op.drop_table("resource")
    op.drop_table("goods_receipt")
