"""RBAC scope definitions used across all services."""


class Scopes:
    # Inventory
    INVENTORY_READ = "inventory:read"
    INVENTORY_WRITE = "inventory:write"
    STOCK_TRANSFER_CREATE = "stock_transfer:create"
    STOCK_TRANSFER_APPROVE = "stock_transfer:approve"

    # Sales
    SELL_OUT_CREATE = "sell_out:create"
    SELL_OUT_READ = "sell_out:read"
    SELL_OUT_REVERSE = "sell_out:reverse"
    SELL_IN_CREATE = "sell_in:create"
    SELL_IN_READ = "sell_in:read"

    # Performance
    PERFORMANCE_READ = "performance:read"
    PERFORMANCE_TARGET_WRITE = "performance:target:write"

    # Commission
    COMMISSION_RULES_READ = "commission_rules:read"
    COMMISSION_RULES_WRITE = "commission_rules:write"
    COMMISSION_STATEMENT_READ = "commission_statement:read"
    COMMISSION_STATEMENT_CONFIRM = "commission_statement:confirm"
    PAYOUT_CREATE = "payout:create"
    PAYOUT_ADMIN = "payout:admin"

    # Party
    PARTY_READ = "party:read"
    PARTY_WRITE = "party:write"

    # Admin
    ADMIN = "admin"
    AUDIT_READ = "audit:read"
