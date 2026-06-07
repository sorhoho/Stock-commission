"""Pydantic domain models for product-catalog-service (TMF620)."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class ProductType(StrEnum):
    HANDSET = "HANDSET"                   # smartphones, feature phones
    TABLET = "TABLET"                     # tablets, iPad
    SIM_CARD = "SIM_CARD"                 # physical SIM (standard, micro, nano)
    ESIM = "ESIM"                         # embedded / downloadable SIM profile
    IOT_DEVICE = "IOT_DEVICE"            # smart meters, sensors, routers
    CCTV = "CCTV"                         # cameras, DVR/NVR recorders
    SET_TOP_BOX = "SET_TOP_BOX"           # satellite/cable TV decoders
    OTT_TV_BOX = "OTT_TV_BOX"            # Android TV / streaming boxes
    CASH_CARD = "CASH_CARD"               # airtime / data vouchers, recharge cards
    MOBILE_BROADBAND = "MOBILE_BROADBAND" # MiFi, 4G/5G dongles
    FIXED_CPE = "FIXED_CPE"              # home routers, ONT, ADSL/fibre modems
    ACCESSORY = "ACCESSORY"              # cases, chargers, earphones, cables
    OTHER = "OTHER"


class ProductCreate(BaseModel):
    sku: str
    name: str
    barcode: str = Field(description="EAN-13 / QR / internal barcode for POS scanning")
    product_type: ProductType
    category: str = Field(description="Commercial category for commission matching (e.g. PREPAID, POSTPAID, TV, DATA)")
    brand: str | None = None
    model_number: str | None = None
    unit_price: float = Field(ge=0)
    denomination: float | None = Field(
        default=None, ge=0,
        description="Face value for cash/voucher cards (e.g. 5.00, 10.00, 50.00)"
    )
    tax_rate: float = Field(ge=0, le=1, default=0.0)
    commission_eligible: bool = Field(
        default=True,
        description="False for cash cards and items excluded from dealer commission"
    )
    requires_serial_tracking: bool = Field(
        default=False,
        description="True for serialised items (handsets, STBs, CCTV) that need IMEI/serial in resource inventory"
    )
    specifications: dict = Field(
        default_factory=dict,
        description="Type-specific attributes: screen_size_inches, storage_gb, ram_gb, connectivity, etc."
    )


class Product(BaseModel):
    id: uuid.UUID
    sku: str
    name: str
    barcode: str
    product_type: ProductType
    category: str
    brand: str | None
    model_number: str | None
    unit_price: float
    denomination: float | None
    tax_rate: float
    commission_eligible: bool
    requires_serial_tracking: bool
    specifications: dict
    tenant_id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
