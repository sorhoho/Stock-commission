"""Pydantic v2 domain models for the Inventory service (TMF637)."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class LocationType(StrEnum):
    WAREHOUSE = "WAREHOUSE"
    DISTRIBUTION_CENTER = "DISTRIBUTION_CENTER"
    DEALER_OUTLET = "DEALER_OUTLET"
    OWN_SHOP = "OWN_SHOP"


class InventoryStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    RESERVED = "RESERVED"
    DAMAGED = "DAMAGED"
    IN_TRANSIT = "IN_TRANSIT"


class TransferStatus(StrEnum):
    PENDING = "PENDING"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


# ---------------------------------------------------------------------------
# Location models
# ---------------------------------------------------------------------------


class Location(BaseModel):
    id: uuid.UUID
    name: str
    type: LocationType
    address: str | None = None
    tenant_id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LocationCreate(BaseModel):
    name: str
    type: LocationType
    address: str | None = None


class LocationUpdate(BaseModel):
    name: str | None = None
    type: LocationType | None = None
    address: str | None = None


# ---------------------------------------------------------------------------
# ProductInventory models
# ---------------------------------------------------------------------------


class ProductInventory(BaseModel):
    id: uuid.UUID
    href: str
    product_id: uuid.UUID
    product_name: str
    quantity: int
    quantity_uom: str = "EACH"
    location_id: uuid.UUID
    location_type: LocationType
    serial_number_range_start: str | None = None
    serial_number_range_end: str | None = None
    status: InventoryStatus
    tenant_id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProductInventoryCreate(BaseModel):
    product_id: uuid.UUID
    product_name: str
    quantity: int = Field(ge=0)
    quantity_uom: str = "EACH"
    location_id: uuid.UUID
    location_type: LocationType
    serial_number_range_start: str | None = None
    serial_number_range_end: str | None = None
    status: InventoryStatus = InventoryStatus.AVAILABLE


class ProductInventoryUpdate(BaseModel):
    product_name: str | None = None
    quantity: int | None = Field(default=None, ge=0)
    quantity_uom: str | None = None
    location_id: uuid.UUID | None = None
    location_type: LocationType | None = None
    serial_number_range_start: str | None = None
    serial_number_range_end: str | None = None
    status: InventoryStatus | None = None


# ---------------------------------------------------------------------------
# StockTransfer models
# ---------------------------------------------------------------------------


class StockTransfer(BaseModel):
    id: uuid.UUID
    transfer_order_number: str
    source_location_id: uuid.UUID
    destination_location_id: uuid.UUID
    product_id: uuid.UUID
    quantity: int
    status: TransferStatus
    initiated_by: str
    tenant_id: str
    requested_date: datetime
    completed_date: datetime | None = None

    model_config = {"from_attributes": True}


class StockTransferCreate(BaseModel):
    transfer_order_number: str
    source_location_id: uuid.UUID
    destination_location_id: uuid.UUID
    product_id: uuid.UUID
    quantity: int = Field(gt=0)
    initiated_by: str
    requested_date: datetime


class StockTransferUpdate(BaseModel):
    status: TransferStatus | None = None
    completed_date: datetime | None = None


# ---------------------------------------------------------------------------
# GoodsReceipt models (stock receipt from SAP / supplier)
# ---------------------------------------------------------------------------


class GoodsReceipt(BaseModel):
    id: uuid.UUID
    grn_number: str
    supplier_reference: str | None = None
    product_id: uuid.UUID
    location_id: uuid.UUID
    quantity_received: int
    unit_cost: float | None = None
    received_by: str
    received_date: datetime
    tenant_id: str
    created_at: datetime

    model_config = {"from_attributes": True}


class GoodsReceiptCreate(BaseModel):
    grn_number: str
    supplier_reference: str | None = None
    product_id: uuid.UUID
    location_id: uuid.UUID
    quantity_received: int = Field(gt=0)
    unit_cost: float | None = None
    received_by: str
    received_date: datetime
    # Serial numbers (IMEI / ICCID / SN) for products that require serial tracking.
    # Must have exactly quantity_received entries when the catalog flags
    # requires_serial_tracking=True.
    serial_numbers: list[str] | None = None


# ---------------------------------------------------------------------------
# StockReservation domain models (activate dormant ORM table)
# ---------------------------------------------------------------------------


class StockReservation(BaseModel):
    id: uuid.UUID
    inventory_id: uuid.UUID
    reserved_quantity: int
    reserved_by: str
    reservation_expiry: datetime
    reason: str | None = None
    tenant_id: str
    created_at: datetime

    model_config = {"from_attributes": True}


class StockReservationCreate(BaseModel):
    inventory_id: uuid.UUID
    reserved_quantity: int = Field(gt=0)
    reserved_by: str
    reservation_expiry: datetime
    reason: str | None = None


# ---------------------------------------------------------------------------
# StockAdjustment models (expose adjust_stock via API)
# ---------------------------------------------------------------------------


class StockAdjustmentCreate(BaseModel):
    inventory_id: uuid.UUID
    delta: int
    reason: str
    adjusted_by: str


# ---------------------------------------------------------------------------
# StockReconciliation models
# ---------------------------------------------------------------------------


class ReconciliationStatus(StrEnum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class StockReconciliationItem(BaseModel):
    id: uuid.UUID
    reconciliation_id: uuid.UUID
    product_id: uuid.UUID
    system_quantity: int
    physical_quantity: int
    variance: int
    tenant_id: str

    model_config = {"from_attributes": True}


class StockReconciliation(BaseModel):
    id: uuid.UUID
    location_id: uuid.UUID
    reconciliation_date: datetime
    status: ReconciliationStatus
    counted_by: str
    approved_by: str | None = None
    notes: str | None = None
    tenant_id: str
    created_at: datetime
    items: list[StockReconciliationItem] = []

    model_config = {"from_attributes": True}


class StockReconciliationItemCreate(BaseModel):
    product_id: uuid.UUID
    system_quantity: int = Field(ge=0)
    physical_quantity: int = Field(ge=0)


class StockReconciliationCreate(BaseModel):
    location_id: uuid.UUID
    reconciliation_date: datetime
    counted_by: str
    notes: str | None = None
    items: list[StockReconciliationItemCreate]


# ---------------------------------------------------------------------------
# Resource models (TMF 639 Resource Inventory — individual device/SIM tracking)
# ---------------------------------------------------------------------------


class ResourceType(StrEnum):
    HANDSET = "HANDSET"                   # smartphones, feature phones
    TABLET = "TABLET"                     # tablets
    SIM_CARD = "SIM_CARD"                 # physical SIM (standard, micro, nano)
    ESIM = "ESIM"                         # embedded / downloadable SIM profile
    IOT_DEVICE = "IOT_DEVICE"            # smart meters, sensors, connected devices
    CCTV = "CCTV"                         # cameras, DVR/NVR recorders
    SET_TOP_BOX = "SET_TOP_BOX"           # satellite/cable TV decoders
    OTT_TV_BOX = "OTT_TV_BOX"            # Android TV / streaming boxes
    CASH_CARD = "CASH_CARD"               # airtime / data vouchers (serialised batches)
    MOBILE_BROADBAND = "MOBILE_BROADBAND" # MiFi / 4G–5G dongles
    FIXED_CPE = "FIXED_CPE"              # home routers, ONT, ADSL/fibre modems
    ACCESSORY = "ACCESSORY"              # cases, chargers, earphones, cables


class CharacteristicName:
    """Standard resource-characteristic name constants.

    Used as the `name` field in ResourceCharacteristic to ensure consistent
    lookups across services (e.g. IMEI scan, ICCID import, serial search).
    """

    # Handset / tablet
    IMEI = "IMEI"
    IMEI2 = "IMEI2"           # dual-SIM second IMEI
    MAC_ADDRESS = "MAC_ADDRESS"
    COLOR = "COLOR"
    STORAGE_GB = "STORAGE_GB"
    RAM_GB = "RAM_GB"
    OS_VERSION = "OS_VERSION"

    # SIM card / eSIM
    ICCID = "ICCID"           # unique SIM identifier
    MSISDN = "MSISDN"         # phone number assigned to SIM
    IMSI = "IMSI"             # international mobile subscriber identity
    SIM_TYPE = "SIM_TYPE"     # STANDARD | MICRO | NANO | ESIM
    PIN1 = "PIN1"
    PUK1 = "PUK1"
    APN = "APN"               # default APN for data SIMs

    # IoT / CCTV
    SERIAL_NUMBER = "SERIAL_NUMBER"
    FIRMWARE_VERSION = "FIRMWARE_VERSION"
    IP_ADDRESS = "IP_ADDRESS"
    MAC_LAN = "MAC_LAN"
    MAC_WIFI = "MAC_WIFI"
    RESOLUTION = "RESOLUTION"           # e.g. "4MP", "8MP"
    SMART_CARD_NUMBER = "SMART_CARD_NUMBER"  # conditional-access card in STB

    # Set-top box / OTT box
    CONDITIONAL_ACCESS_ID = "CONDITIONAL_ACCESS_ID"
    DECODER_NUMBER = "DECODER_NUMBER"

    # Cash card / voucher
    VOUCHER_CODE = "VOUCHER_CODE"
    DENOMINATION = "DENOMINATION"
    EXPIRY_DATE = "EXPIRY_DATE"
    BATCH_NUMBER = "BATCH_NUMBER"

    # Mobile broadband / CPE
    PPPoE_USERNAME = "PPPoE_USERNAME"
    WIFI_SSID = "WIFI_SSID"
    WIFI_PASSWORD = "WIFI_PASSWORD"


class ResourceStatusType(StrEnum):
    AVAILABLE = "AVAILABLE"
    ALLOCATED = "ALLOCATED"
    SOLD = "SOLD"
    DAMAGED = "DAMAGED"
    SCRAPPED = "SCRAPPED"


class ResourceCharacteristic(BaseModel):
    id: uuid.UUID
    resource_id: uuid.UUID
    name: str
    value: str
    tenant_id: str

    model_config = {"from_attributes": True}


class Resource(BaseModel):
    id: uuid.UUID
    resource_name: str
    resource_type: ResourceType
    product_id: uuid.UUID
    inventory_id: uuid.UUID | None = None
    location_id: uuid.UUID | None = None
    status: ResourceStatusType
    batch_reference: str | None = None
    supplier_reference: str | None = None
    allocated_to: str | None = None
    tenant_id: str
    created_at: datetime
    characteristics: list[ResourceCharacteristic] = []

    model_config = {"from_attributes": True}


class ResourceCharacteristicCreate(BaseModel):
    name: str
    value: str


class ResourceCreate(BaseModel):
    resource_name: str
    resource_type: ResourceType
    product_id: uuid.UUID
    inventory_id: uuid.UUID | None = None
    location_id: uuid.UUID | None = None
    status: ResourceStatusType = ResourceStatusType.AVAILABLE
    batch_reference: str | None = None
    supplier_reference: str | None = None
    characteristics: list[ResourceCharacteristicCreate] = []
