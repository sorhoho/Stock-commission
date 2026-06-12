"""SQLAlchemy ORM models for the Party service."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from telco_common.db.base import Base, TimestampMixin, TenantMixin, UUIDMixin


class Party(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "party"

    party_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    tax_number: Mapped[str | None] = mapped_column(String(100), nullable=True, unique=False)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="ACTIVE", index=True
    )
    parent_party_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("party.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Self-referential relationship for hierarchy
    parent: Mapped["Party | None"] = relationship(
        "Party",
        remote_side="Party.id",
        back_populates="children",
        lazy="noload",
    )
    children: Mapped[list["Party"]] = relationship(
        "Party",
        back_populates="parent",
        lazy="noload",
    )
    characteristics: Mapped[list["PartyCharacteristic"]] = relationship(
        "PartyCharacteristic",
        back_populates="party",
        cascade="all, delete-orphan",
        lazy="noload",
    )
    accounts: Mapped[list["PartyAccount"]] = relationship(
        "PartyAccount",
        back_populates="party",
        cascade="all, delete-orphan",
        lazy="noload",
    )

    @property
    def href(self) -> str:
        return f"/api/v1/party/{self.id}"


class PartyCharacteristic(Base, UUIDMixin, TenantMixin):
    __tablename__ = "party_characteristic"

    party_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("party.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    value_type: Mapped[str] = mapped_column(String(50), nullable=False, default="string")

    party: Mapped["Party"] = relationship(
        "Party",
        back_populates="characteristics",
        lazy="noload",
    )


class PartyAccount(Base, UUIDMixin, TenantMixin):
    __tablename__ = "party_account"

    party_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("party.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    account_type: Mapped[str] = mapped_column(String(100), nullable=False)
    balance: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="THB")
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    party: Mapped["Party"] = relationship(
        "Party",
        back_populates="accounts",
        lazy="noload",
    )
