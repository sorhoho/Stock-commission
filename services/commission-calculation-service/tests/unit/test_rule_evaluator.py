"""Comprehensive tests for the commission rules engine — pure functions, no I/O."""

import pytest

from app.domain.rule_evaluator import (
    CommissionRule,
    CommissionType,
    calculate_commission,
    calculate_tiered_commission,
    find_applicable_rule,
)


def make_rule(**kwargs) -> CommissionRule:
    defaults = dict(
        id="rule-1",
        product_category="SIM",
        channel_type=None,
        tier_min_qty=0,
        tier_max_qty=None,
        commission_type=CommissionType.PERCENTAGE,
        commission_value=0.10,
        currency="USD",
        priority=100,
    )
    defaults.update(kwargs)
    return CommissionRule(**defaults)


class TestFindApplicableRule:
    def test_percentage_rule_match(self):
        rules = [make_rule(product_category="SIM", commission_type=CommissionType.PERCENTAGE, commission_value=0.10)]
        result = find_applicable_rule(rules, "SIM", "RETAIL", 5)
        assert result is not None
        assert result.commission_type == CommissionType.PERCENTAGE

    def test_flat_amount_rule_match(self):
        rules = [make_rule(product_category="DEVICE", commission_type=CommissionType.FLAT_AMOUNT, commission_value=5.0)]
        result = find_applicable_rule(rules, "DEVICE", "ONLINE", 3)
        assert result is not None
        assert result.commission_value == 5.0

    def test_wildcard_product_category_matches_any(self):
        rules = [make_rule(product_category="*", commission_value=0.05)]
        result = find_applicable_rule(rules, "ANYTHING", "RETAIL", 1)
        assert result is not None

    def test_exact_product_category_no_match(self):
        rules = [make_rule(product_category="SIM")]
        result = find_applicable_rule(rules, "DEVICE", "RETAIL", 1)
        assert result is None

    def test_channel_filter_matches(self):
        rules = [make_rule(channel_type="RETAIL")]
        result = find_applicable_rule(rules, "SIM", "RETAIL", 1)
        assert result is not None

    def test_channel_filter_excludes_wrong_channel(self):
        rules = [make_rule(channel_type="RETAIL")]
        result = find_applicable_rule(rules, "SIM", "ONLINE", 1)
        assert result is None

    def test_channel_none_matches_all_channels(self):
        rules = [make_rule(channel_type=None)]
        assert find_applicable_rule(rules, "SIM", "RETAIL", 1) is not None
        assert find_applicable_rule(rules, "SIM", "ONLINE", 1) is not None
        assert find_applicable_rule(rules, "SIM", "KIOSK", 1) is not None

    def test_tiered_quantity_range_lower_tier(self):
        rules = [
            make_rule(id="low", tier_min_qty=1, tier_max_qty=10, commission_value=0.05, priority=2),
            make_rule(id="high", tier_min_qty=11, tier_max_qty=None, commission_value=0.10, priority=1),
        ]
        result = find_applicable_rule(rules, "SIM", "RETAIL", 5)
        assert result.id == "low"

    def test_tiered_quantity_range_upper_tier(self):
        rules = [
            make_rule(id="low", tier_min_qty=1, tier_max_qty=10, commission_value=0.05, priority=2),
            make_rule(id="high", tier_min_qty=11, tier_max_qty=None, commission_value=0.10, priority=1),
        ]
        result = find_applicable_rule(rules, "SIM", "RETAIL", 15)
        assert result.id == "high"

    def test_quantity_below_min_no_match(self):
        rules = [make_rule(tier_min_qty=5)]
        result = find_applicable_rule(rules, "SIM", "RETAIL", 3)
        assert result is None

    def test_quantity_above_max_no_match(self):
        rules = [make_rule(tier_min_qty=1, tier_max_qty=10)]
        result = find_applicable_rule(rules, "SIM", "RETAIL", 20)
        assert result is None

    def test_priority_ordering_returns_highest_priority(self):
        rules = [
            make_rule(id="low-priority", priority=200, commission_value=0.05),
            make_rule(id="high-priority", priority=1, commission_value=0.20),
        ]
        result = find_applicable_rule(rules, "SIM", "RETAIL", 1)
        assert result.id == "high-priority"

    def test_empty_rules_returns_none(self):
        assert find_applicable_rule([], "SIM", "RETAIL", 1) is None


class TestCalculateCommission:
    def test_flat_amount_single_unit(self):
        rule = make_rule(commission_type=CommissionType.FLAT_AMOUNT, commission_value=2.50)
        assert calculate_commission(rule, 1, 10.0) == 2.50

    def test_flat_amount_multiple_units(self):
        rule = make_rule(commission_type=CommissionType.FLAT_AMOUNT, commission_value=2.50)
        assert calculate_commission(rule, 4, 10.0) == 10.0

    def test_percentage_calculation(self):
        rule = make_rule(commission_type=CommissionType.PERCENTAGE, commission_value=0.15)
        assert calculate_commission(rule, 10, 20.0) == 30.0

    def test_percentage_rounds_to_two_decimals(self):
        rule = make_rule(commission_type=CommissionType.PERCENTAGE, commission_value=0.333)
        result = calculate_commission(rule, 3, 10.0)
        assert result == round(10.0 * 3 * 0.333, 2)

    def test_tiered_rule_rejected_by_single_rule_calc(self):
        # TIERED is progressive and spans multiple bands; a single-rule calc
        # cannot express it and must refuse rather than silently mis-price.
        rule = make_rule(commission_type=CommissionType.TIERED, commission_value=1.50)
        with pytest.raises(ValueError):
            calculate_commission(rule, 7, 10.0)

    def test_zero_quantity_returns_zero(self):
        rule = make_rule(commission_type=CommissionType.FLAT_AMOUNT, commission_value=5.0)
        assert calculate_commission(rule, 0, 10.0) == 0.0

    def test_percentage_precision(self):
        rule = make_rule(commission_type=CommissionType.PERCENTAGE, commission_value=0.1)
        result = calculate_commission(rule, 3, 9.99)
        assert result == round(9.99 * 3 * 0.1, 2)


class TestCalculateTieredCommission:
    def _bands(self):
        return [
            make_rule(id="t1", commission_type=CommissionType.TIERED,
                      tier_min_qty=1, tier_max_qty=50, commission_value=1.00),
            make_rule(id="t2", commission_type=CommissionType.TIERED,
                      tier_min_qty=51, tier_max_qty=100, commission_value=1.50),
            make_rule(id="t3", commission_type=CommissionType.TIERED,
                      tier_min_qty=101, tier_max_qty=None, commission_value=2.00),
        ]

    def test_progressive_accumulation_across_bands(self):
        # 50 @ 1.00 + 20 @ 1.50 = 80.00
        assert calculate_tiered_commission(self._bands(), "SIM", "RETAIL", 70) == 80.0

    def test_single_band_only(self):
        # entirely within band 1: 30 @ 1.00
        assert calculate_tiered_commission(self._bands(), "SIM", "RETAIL", 30) == 30.0

    def test_boundary_exactly_at_band_edge(self):
        # qty 50 stays fully in band 1; qty 51 spills one unit into band 2
        assert calculate_tiered_commission(self._bands(), "SIM", "RETAIL", 50) == 50.0
        assert calculate_tiered_commission(self._bands(), "SIM", "RETAIL", 51) == 51.5

    def test_spans_all_three_bands(self):
        # 50 @ 1.00 + 50 @ 1.50 + 20 @ 2.00 = 50 + 75 + 40 = 165.00
        assert calculate_tiered_commission(self._bands(), "SIM", "RETAIL", 120) == 165.0

    def test_channel_and_category_filtering(self):
        bands = [
            make_rule(id="r", commission_type=CommissionType.TIERED, channel_type="RETAIL",
                      tier_min_qty=1, tier_max_qty=None, commission_value=1.00),
            make_rule(id="o", commission_type=CommissionType.TIERED, channel_type="ONLINE",
                      tier_min_qty=1, tier_max_qty=None, commission_value=9.00),
        ]
        # only the RETAIL band applies
        assert calculate_tiered_commission(bands, "SIM", "RETAIL", 10) == 10.0

    def test_no_tiered_bands_returns_zero(self):
        flat = [make_rule(commission_type=CommissionType.FLAT_AMOUNT, commission_value=5.0)]
        assert calculate_tiered_commission(flat, "SIM", "RETAIL", 10) == 0.0
