# Telco Distribution & Commission System — Business Guide

> **Who this is for:** Channel sales managers, finance teams, dealer support, and any business stakeholder who needs to understand what this system does, why it exists, and how to work with it — without needing to read code.

---

## What Problem Does This Solve?

In a typical telco distribution model, the company sells SIM cards, handsets, and data plans through a network of distributors and dealers. Two painful things happen manually today:

1. **Nobody knows exactly how many devices are at each dealer location** — stock is tracked on spreadsheets, reconciliation takes days, and disputed stock counts delay month-end.
2. **Commission calculation is a black box** — finance runs Excel macros at month-end, dealers dispute the numbers, re-calculations take a week, and the business can't pay on time.

This system replaces both of those with a real-time, auditable platform.

---

## The Four Business Domains

```
┌─────────────────────────────────────────────────────────────────────┐
│  1. Distribution & Inventory    │  2. Sales Channel                 │
│                                 │                                    │
│  • Where is every device right  │  • Record sell-in orders          │
│    now (warehouse, DC, dealer)  │    (distributor → dealer)         │
│  • Stock transfers & receipts   │  • Record sell-out transactions   │
│  • Real-time stock-on-hand      │    (dealer → customer / POS)      │
├─────────────────────────────────┼────────────────────────────────────┤
│  3. Sales Performance           │  4. Commission & Incentives        │
│                                 │                                    │
│  • Dealer KPI dashboards        │  • Commission rules per product    │
│  • Target vs. achievement       │    category, channel & tier       │
│  • Monthly reports              │  • Auto-calculated the instant    │
│                                 │    a sale is recorded             │
│                                 │  • Payout scheduling & receipts   │
└─────────────────────────────────┴────────────────────────────────────┘
```

---

## Key Business Workflows

### 1. Dealer Onboarding
A new dealer is registered in the system → the system automatically assigns a default commission agreement → the dealer can log in, see their stock, and record sales immediately.

### 2. Stock Transfer (Warehouse → Dealer)
The distributor raises a stock transfer order. When goods are received and confirmed, stock-on-hand at the dealer location is updated in real time. The regional manager can query any location's SOH at any moment.

### 3. Sell-Out (Point of Sale)
A dealer sells a device to a customer. The POS records the transaction. Within seconds:
- Commission is calculated (flat, percentage, or tiered — based on the active agreement)
- Stock-on-hand at that dealer drops by the sold quantity
- The performance KPI (monthly units sold) is updated
- An audit trail entry is written

### 4. Month-End Commission Statement
At the end of each month, the finance team reviews draft commission statements. Once approved:
- Statement status changes to CONFIRMED
- Payout service schedules the disbursement (runs automatically on the 1st of each month at 02:00)
- Dealers receive a notification when payment is processed

### 5. Dispute Management
If a dealer disputes a commission calculation, the event is flagged as DISPUTED. Finance can view the original transaction, the rule that applied, and the calculated amount before resolving.

---

## Commission Types Explained

| Type | How It Works | Example |
|------|-------------|---------|
| **Flat Amount** | Fixed RM per unit sold | RM 15 per SIM card |
| **Percentage** | % of the sale value | 3% of device selling price |
| **Tiered** | Per-unit amount that changes based on volume | RM 10/unit for 1–50 units, RM 15/unit for 51–100 units |

Rules are set up in the **Commission Rules** module by the finance team. Each dealer is bound to an **Agreement** that specifies which rules apply to them.

---

## Who Accesses What

| Role | What They See |
|------|--------------|
| **Admin** | Everything — user management, system config, all reports |
| **Finance** | Commission rules, statements, payout approval, dispute resolution |
| **Dealer** | Their own stock, their own sales transactions, their own commission statements |
| **Regional Manager** | All dealers in their region — stock, sales, performance vs. target |
| **Distributor** | Sell-in orders, stock transfers they initiated |

Access is controlled by Keycloak (the identity & access system). All roles and permissions are managed there — no code change needed to add a user or change their role.

---

## Demo Access

| URL | Purpose |
|-----|---------|
| http://localhost:3000 | Main web application (dealer & manager UI) |
| http://localhost:8080/admin | Identity & access management (Keycloak) |
| http://localhost:8090 | Kafka event stream monitor |
| http://localhost:3001 | Operations dashboards (Grafana) |

| Role | Username | Password |
|------|----------|----------|
| Admin | admin@telco.local | admin123 |
| Dealer | dealer1@telco.local | dealer123 |
| Finance | finance@telco.local | finance123 |

---

## Compliance & Audit

Every event in the system — every sale, every stock movement, every commission calculation, every status change — is written to an **immutable audit log**. Nothing is deleted; old records are only archived. The retention policy is:

- **Commission events & audit logs:** 7 years (financial regulation)
- **Sales transactions:** 5 years

The audit log is always available to regulators and internal audit teams via the audit API or direct database query.

---

## What "Real-Time" Actually Means

When a dealer records a sale, the system does not batch it for overnight processing. Instead, an event travels through the system within seconds:

```
POS sale recorded  →  (< 2 seconds)  →  Commission calculated
                   →  (< 2 seconds)  →  Stock-on-hand updated
                   →  (< 2 seconds)  →  KPI updated
                   →  (< 2 seconds)  →  Audit log written
```

This means a regional manager refreshing their dashboard will see the sale and commission within seconds, not the next morning.

---

## Key Metrics to Monitor

| Metric | Target | Where to Check |
|--------|--------|----------------|
| Commission calculation lag | < 5 seconds after sale | Grafana → Commission dashboard |
| Payout SLA (confirmed → disbursed) | Same business day | Payout service reports |
| Stock discrepancy rate | < 0.1% | Inventory reconciliation report |
| Kafka consumer lag | < 1,000 messages | Kafka UI (port 8090) |
| API response time (p99) | < 500 ms | Grafana → API latency panel |

---

## Frequently Asked Questions

**Q: Can a dealer see another dealer's commission?**
No. Every record is tagged with a `tenant_id` and the database enforces row-level isolation. A dealer logged in can only ever see their own data, even if they know another dealer's ID.

**Q: What happens if the system goes down mid-calculation?**
The commission calculation is designed to be idempotent — if the same sale event is processed twice (e.g., after a restart), the system detects the duplicate and skips the second calculation. No double-commission is ever paid.

**Q: Can we change commission rates retroactively?**
Commission rules apply at the time of the transaction. Changing a rule does not retroactively affect already-calculated commissions. A new rule only applies to new transactions.

**Q: How do I add a new product category with different commission?**
Finance logs into the Commission Rules module, creates a new `AgreementSpec` for the category, and sets the rule (flat/percentage/tiered). Then binds the relevant dealers to that spec via an `Agreement`.

**Q: How are disputes handled?**
The commission event status is set to `DISPUTED`. Finance reviews the original transaction amount, the rule that matched, and the calculated result. They can either approve (set to `APPROVED`) or raise a correction transaction.
