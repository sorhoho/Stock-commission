#!/usr/bin/env python3
"""Seed default commission rules for the demo tenant."""

import asyncio
import httpx

BASE_URL = "http://localhost:8007/api/v1/agreementManagement"
TENANT_ID = "tenant-demo"
HEADERS = {"X-Tenant-ID": TENANT_ID}


async def seed():
    async with httpx.AsyncClient(headers=HEADERS, timeout=10.0) as client:
        # Create a default agreement spec
        spec_resp = await client.post(f"{BASE_URL}/agreementSpec", json={
            "name": "Standard Dealer Commission",
            "version": "2026.1",
            "description": "Standard commission scheme for all dealers",
            "applicable_party_roles": ["DEALER", "CHANNEL_PARTNER"],
            "effective_from": "2026-01-01",
            "tenant_id": TENANT_ID,
        })
        spec_resp.raise_for_status()
        spec = spec_resp.json()
        spec_id = spec["id"]
        print(f"Created AgreementSpec: {spec_id}")

        # Commission rules: tiered by quantity
        rules = [
            {"product_category": "*", "channel_type": None, "tier_min_qty": 1, "tier_max_qty": 10, "commission_type": "PERCENTAGE", "commission_value": 0.08, "currency": "USD", "priority": 10},
            {"product_category": "*", "channel_type": None, "tier_min_qty": 11, "tier_max_qty": 50, "commission_type": "PERCENTAGE", "commission_value": 0.12, "currency": "USD", "priority": 20},
            {"product_category": "*", "channel_type": None, "tier_min_qty": 51, "tier_max_qty": None, "commission_type": "PERCENTAGE", "commission_value": 0.15, "currency": "USD", "priority": 30},
        ]
        for rule_data in rules:
            rule_resp = await client.post(f"{BASE_URL}/commissionRule", json={
                **rule_data,
                "agreement_spec_id": spec_id,
                "tenant_id": TENANT_ID,
            })
            rule_resp.raise_for_status()
            print(f"  Rule created: tier {rule_data['tier_min_qty']}-{rule_data.get('tier_max_qty', '∞')} @ {rule_data['commission_value']*100:.0f}%")

        print("Commission rules seeded successfully.")


if __name__ == "__main__":
    asyncio.run(seed())
