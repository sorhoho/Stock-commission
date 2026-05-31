#!/usr/bin/env python3
"""Seed demo parties (distributor + dealers) for local development."""

import asyncio
import httpx

BASE_URL = "http://localhost:8002/api/v1/party"
RULES_URL = "http://localhost:8007/api/v1/agreementManagement"
TENANT_ID = "tenant-demo"
HEADERS = {"X-Tenant-ID": TENANT_ID}


async def seed():
    async with httpx.AsyncClient(headers=HEADERS, timeout=10.0) as client:
        # Distributor
        dist_resp = await client.post(f"{BASE_URL}/party", json={
            "party_type": "ORGANIZATION",
            "role": "DISTRIBUTOR",
            "name": "Main Distribution Ltd",
            "tax_number": "TAX-001",
            "status": "ACTIVE",
            "tenant_id": TENANT_ID,
        })
        dist_resp.raise_for_status()
        distributor = dist_resp.json()
        print(f"Created distributor: {distributor['id']}")

        # Dealers
        dealer_names = ["Dealer Alpha", "Dealer Beta", "Dealer Gamma"]
        for name in dealer_names:
            dealer_resp = await client.post(f"{BASE_URL}/party", json={
                "party_type": "ORGANIZATION",
                "role": "DEALER",
                "name": name,
                "tax_number": f"TAX-{name[:5].upper()}",
                "status": "ACTIVE",
                "parent_party_id": distributor["id"],
                "tenant_id": TENANT_ID,
            })
            dealer_resp.raise_for_status()
            dealer = dealer_resp.json()
            print(f"Created dealer: {dealer['id']} — {name}")

        print("Parties seeded successfully.")


if __name__ == "__main__":
    asyncio.run(seed())
