"""Fix resource_characteristic uniqueness constraint.

Replace the overly-broad (name, value, tenant_id) constraint (which wrongly
prevents two different devices from sharing a characteristic value such as
COLOR='Black') with:
  - UniqueConstraint(resource_id, name)  — one value per characteristic per resource
  - Partial unique index on (value, tenant_id) restricted to identity
    characteristics (IMEI, ICCID, SERIAL_NUMBER, SMART_CARD_NUMBER, MAC_ADDRESS)
    — prevents the same physical identifier appearing on two resources.

Revision ID: inv002
Revises: inv001
Create Date: 2026-06-11 00:00:00.000000
"""

from __future__ import annotations

from alembic import op

revision = "inv002"
down_revision = "inv001"
branch_labels = None
depends_on = None

_IDENTITY_NAMES = "('IMEI','ICCID','SERIAL_NUMBER','SMART_CARD_NUMBER','MAC_ADDRESS')"


def upgrade() -> None:
    op.drop_constraint(
        "uq_resource_characteristic_nvt",
        "resource_characteristic",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_resource_characteristic_resource_name",
        "resource_characteristic",
        ["resource_id", "name"],
    )
    op.execute(
        f"CREATE UNIQUE INDEX uix_resource_characteristic_identity_value "
        f"ON resource_characteristic (value, tenant_id) "
        f"WHERE name IN {_IDENTITY_NAMES}"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uix_resource_characteristic_identity_value")
    op.drop_constraint(
        "uq_resource_characteristic_resource_name",
        "resource_characteristic",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_resource_characteristic_nvt",
        "resource_characteristic",
        ["name", "value", "tenant_id"],
    )
