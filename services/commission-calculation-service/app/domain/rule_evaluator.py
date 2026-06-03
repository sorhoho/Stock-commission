"""
Pure-function commission rules engine.

NO I/O. Fully deterministic. Zero side-effects.
All domain logic for rule matching and commission calculation lives here.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class CommissionType(StrEnum):
    FLAT_AMOUNT = "FLAT_AMOUNT"
    PERCENTAGE = "PERCENTAGE"
    TIERED = "TIERED"


@dataclass(frozen=True)
class CommissionRule:
    id: str
    product_category: str       # "*" means match all product categories
    channel_type: str | None    # None means match all channel types
    tier_min_qty: int
    tier_max_qty: int | None    # None means no upper quantity limit
    commission_type: CommissionType
    commission_value: float     # flat amount, percentage rate (0.15 = 15%), or tiered amount
    currency: str
    priority: int               # lower value = higher priority (1 beats 10)


def find_applicable_rule(
    rules: list[CommissionRule],
    product_category: str,
    channel_type: str,
    quantity: int,
) -> CommissionRule | None:
    """
    Return the highest-priority rule that matches the given product_category,
    channel_type, and quantity. Returns None when no rule matches.

    Matching criteria (all must be satisfied):
    - product_category: exact match OR rule.product_category == "*" (wildcard)
    - channel_type: rule.channel_type is None (match all) OR exact match
    - quantity range: tier_min_qty <= quantity <= tier_max_qty (or no upper limit)

    When multiple rules match, the one with the lowest priority number wins.
    """
    matching: list[CommissionRule] = []

    for rule in rules:
        # ── Product category filter ──
        if rule.product_category != "*" and rule.product_category != product_category:
            continue

        # ── Channel filter ──
        if rule.channel_type is not None and rule.channel_type != channel_type:
            continue

        # ── Quantity range filter ──
        if quantity < rule.tier_min_qty:
            continue
        if rule.tier_max_qty is not None and quantity > rule.tier_max_qty:
            continue

        matching.append(rule)

    if not matching:
        return None

    # Sort ascending by priority; lower number = higher priority
    return sorted(matching, key=lambda r: r.priority)[0]


def calculate_commission(
    rule: CommissionRule,
    quantity: int,
    unit_price: float,
) -> float:
    """
    Calculate commission amount for a single FLAT_AMOUNT or PERCENTAGE rule.

    Rules:
    - FLAT_AMOUNT:  commission = rule.commission_value * quantity
    - PERCENTAGE:   commission = unit_price * quantity * rule.commission_value

    TIERED rules are progressive (bracketed) and span multiple bands, so they
    cannot be computed from a single rule — use calculate_tiered_commission().

    Always returns a value rounded to 2 decimal places.
    """
    if rule.commission_type == CommissionType.FLAT_AMOUNT:
        return round(rule.commission_value * quantity, 2)
    elif rule.commission_type == CommissionType.PERCENTAGE:
        return round(unit_price * quantity * rule.commission_value, 2)
    elif rule.commission_type == CommissionType.TIERED:
        raise ValueError(
            "TIERED rules require progressive bracket calculation; "
            "call calculate_tiered_commission() with the full rule set."
        )
    return 0.0


def calculate_tiered_commission(
    rules: list[CommissionRule],
    product_category: str,
    channel_type: str,
    quantity: int,
) -> float:
    """
    Progressive (bracketed) tiered commission: each TIERED band's per-unit
    value applies only to the units that fall within that band's quantity
    range. Bands are matched on product_category/channel_type (same criteria
    as find_applicable_rule) and applied in ascending tier order.

    A band [tier_min_qty, tier_max_qty] covers unit positions min..max
    inclusive; tier_max_qty=None means the band extends to the full quantity.

    Example: bands [1-50 @ 1.00], [51-100 @ 1.50]; quantity 70
      -> 50 units * 1.00  +  20 units * 1.50  =  80.00

    Always returns a value rounded to 2 decimal places.
    """
    bands = sorted(
        (
            r for r in rules
            if r.commission_type == CommissionType.TIERED
            and (r.product_category == "*" or r.product_category == product_category)
            and (r.channel_type is None or r.channel_type == channel_type)
        ),
        key=lambda r: r.tier_min_qty,
    )

    total = 0.0
    for band in bands:
        if quantity < band.tier_min_qty:
            continue
        upper = band.tier_max_qty if band.tier_max_qty is not None else quantity
        units_in_band = min(quantity, upper) - band.tier_min_qty + 1
        total += band.commission_value * units_in_band

    return round(total, 2)
