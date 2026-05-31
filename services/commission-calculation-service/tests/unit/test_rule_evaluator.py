"""Comprehensive tests for the commission rules engine — pure functions, no I/O."""

import pytest

from app.domain.rule_evaluator import (
    CommissionRule,
    CommissionType,
    calculate_commission,
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

    def test_tiered_commission(self):
        rule = make_rule(commission_type=CommissionType.TIERED, commission_value=1.50)
        assert calculate_commission(rule, 7, 10.0) == 10.5

    def test_zero_quantity_returns_zero(self):
        rule = make_rule(commission_type=CommissionType.FLAT_AMOUNT, commission_value=5.0)
        assert calculate_commission(rule, 0, 10.0) == 0.0

    def test_percentage_precision(self):
        rule = make_rule(commission_type=CommissionType.PERCENTAGE, commission_value=0.1)
        result = calculate_commission(rule, 3, 9.99)
        assert result == round(9.99 * 3 * 0.1, 2)
