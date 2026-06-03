-- Demo seed data for local development.
-- Idempotent (ON CONFLICT DO NOTHING). Run via: make seed
-- Writes directly to the databases — no auth tokens required for local dev.
--
-- Seeds a distributor + dealer, a commission AgreementSpec with three
-- quantity tiers, and an active Agreement binding the dealer to that spec.
-- The Agreement binding is what lets commission-calculation-service find a
-- dealer's rules when a sell-out event arrives.

\c party
INSERT INTO party (id, party_type, role, name, tax_number, status, parent_party_id, tenant_id)
VALUES
  ('11111111-0000-0000-0000-000000000001', 'ORGANIZATION', 'DISTRIBUTOR', 'Main Distribution Ltd', 'TAX-001', 'ACTIVE', NULL, 'tenant-demo'),
  ('22222222-2222-2222-2222-222222222222', 'ORGANIZATION', 'DEALER', 'Dealer Alpha', 'TAX-ALPHA', 'ACTIVE', '11111111-0000-0000-0000-000000000001', 'tenant-demo')
ON CONFLICT (id) DO NOTHING;

\c commission_rules
INSERT INTO agreement_spec (id, name, version, description, applicable_party_roles, effective_from, is_deleted, tenant_id)
VALUES
  ('aaaaaaaa-0000-0000-0000-000000000001', 'Standard Dealer Commission', '2026.1', 'Standard commission scheme for all dealers', '["DEALER"]', '2026-01-01', false, 'tenant-demo')
ON CONFLICT (id) DO NOTHING;

INSERT INTO commission_rule (id, agreement_spec_id, product_category, channel_type, tier_min_qty, tier_max_qty, commission_type, commission_value, currency, conditions, priority, is_deleted, tenant_id)
VALUES
  ('cccccccc-0000-0000-0000-000000000001', 'aaaaaaaa-0000-0000-0000-000000000001', '*', NULL, 1,  10,   'PERCENTAGE', 0.08, 'USD', '{}', 10, false, 'tenant-demo'),
  ('cccccccc-0000-0000-0000-000000000002', 'aaaaaaaa-0000-0000-0000-000000000001', '*', NULL, 11, 50,   'PERCENTAGE', 0.12, 'USD', '{}', 20, false, 'tenant-demo'),
  ('cccccccc-0000-0000-0000-000000000003', 'aaaaaaaa-0000-0000-0000-000000000001', '*', NULL, 51, NULL, 'PERCENTAGE', 0.15, 'USD', '{}', 30, false, 'tenant-demo')
ON CONFLICT (id) DO NOTHING;

INSERT INTO agreement (id, agreement_spec_id, party_id, party_name, status, signed_date, tenant_id)
VALUES
  ('bbbbbbbb-0000-0000-0000-000000000001', 'aaaaaaaa-0000-0000-0000-000000000001', '22222222-2222-2222-2222-222222222222', 'Dealer Alpha', 'ACTIVE', '2026-01-01', 'tenant-demo')
ON CONFLICT (id) DO NOTHING;
