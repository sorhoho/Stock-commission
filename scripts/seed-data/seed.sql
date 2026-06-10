-- Demo seed data for local development.
-- Idempotent (ON CONFLICT DO NOTHING). Run via: make seed
-- Writes directly to the databases — no auth tokens required for local dev.
--
-- Covers:
--   party        — distributor + two dealers
--   commission   — tiered agreement spec with per-category rules
--   inventory    — 3 locations, SOH for seeded products
--   product_catalog — comprehensive telco product range
--   inventory.resource — sample serialised units with characteristics

-- ─── Party ───────────────────────────────────────────────────────────────────

\c party
INSERT INTO party (id, party_type, role, name, tax_number, status, parent_party_id, tenant_id)
VALUES
  ('11111111-0000-0000-0000-000000000001', 'ORGANIZATION', 'DISTRIBUTOR', 'Main Distribution Ltd',  'TAX-001',   'ACTIVE', NULL,                                   'tenant-demo'),
  ('22222222-2222-2222-2222-222222222222', 'ORGANIZATION', 'DEALER',      'Dealer Alpha',            'TAX-ALPHA', 'ACTIVE', '11111111-0000-0000-0000-000000000001', 'tenant-demo'),
  ('33333333-3333-3333-3333-333333333333', 'ORGANIZATION', 'DEALER',      'Dealer Beta',             'TAX-BETA',  'ACTIVE', '11111111-0000-0000-0000-000000000001', 'tenant-demo')
ON CONFLICT (id) DO NOTHING;

-- ─── Commission rules ─────────────────────────────────────────────────────────

\c commission_rules

INSERT INTO agreement_spec (id, name, version, description, applicable_party_roles, effective_from, is_deleted, tenant_id)
VALUES
  ('aaaaaaaa-0000-0000-0000-000000000001', 'Standard Dealer Commission',  '2026.1', 'Tiered commission for all dealers',             '["DEALER"]', '2026-01-01', false, 'tenant-demo'),
  ('aaaaaaaa-0000-0000-0000-000000000002', 'Handset Specialist Scheme',   '2026.1', 'Higher rates for high-volume handset dealers',  '["DEALER"]', '2026-01-01', false, 'tenant-demo'),
  ('aaaaaaaa-0000-0000-0000-000000000003', 'TV & STB Commission Scheme',  '2026.1', 'Commission scheme for TV products and STBs',    '["DEALER"]', '2026-01-01', false, 'tenant-demo')
ON CONFLICT (id) DO NOTHING;

-- Standard tiered rules (all categories)
INSERT INTO commission_rule (id, agreement_spec_id, product_category, channel_type, tier_min_qty, tier_max_qty, commission_type, commission_value, currency, conditions, priority, is_deleted, tenant_id)
VALUES
  ('cccccccc-0000-0000-0000-000000000001', 'aaaaaaaa-0000-0000-0000-000000000001', '*',       NULL, 1,  10,   'PERCENTAGE', 0.08, 'USD', '{}', 10, false, 'tenant-demo'),
  ('cccccccc-0000-0000-0000-000000000002', 'aaaaaaaa-0000-0000-0000-000000000001', '*',       NULL, 11, 50,   'PERCENTAGE', 0.12, 'USD', '{}', 20, false, 'tenant-demo'),
  ('cccccccc-0000-0000-0000-000000000003', 'aaaaaaaa-0000-0000-0000-000000000001', '*',       NULL, 51, NULL, 'PERCENTAGE', 0.15, 'USD', '{}', 30, false, 'tenant-demo'),
  -- SIM cards — lower margin, flat fee per unit
  ('cccccccc-0000-0000-0000-000000000004', 'aaaaaaaa-0000-0000-0000-000000000001', 'PREPAID', NULL, 1,  NULL, 'FLAT_AMOUNT', 0.50, 'USD', '{}', 5,  false, 'tenant-demo'),
  -- Cash / recharge cards — not eligible (handled by commission_eligible=false on product)
  -- Handset specialist scheme
  ('cccccccc-0000-0000-0000-000000000005', 'aaaaaaaa-0000-0000-0000-000000000002', 'HANDSET', NULL, 1,  20,   'PERCENTAGE', 0.10, 'USD', '{}', 10, false, 'tenant-demo'),
  ('cccccccc-0000-0000-0000-000000000006', 'aaaaaaaa-0000-0000-0000-000000000002', 'HANDSET', NULL, 21, NULL, 'PERCENTAGE', 0.14, 'USD', '{}', 20, false, 'tenant-demo'),
  -- TV / STB scheme
  ('cccccccc-0000-0000-0000-000000000007', 'aaaaaaaa-0000-0000-0000-000000000003', 'TV',      NULL, 1,  NULL, 'PERCENTAGE', 0.09, 'USD', '{}', 10, false, 'tenant-demo')
ON CONFLICT (id) DO NOTHING;

INSERT INTO agreement (id, agreement_spec_id, party_id, party_name, status, signed_date, tenant_id)
VALUES
  ('bbbbbbbb-0000-0000-0000-000000000001', 'aaaaaaaa-0000-0000-0000-000000000001', '22222222-2222-2222-2222-222222222222', 'Dealer Alpha', 'ACTIVE', '2026-01-01', 'tenant-demo'),
  ('bbbbbbbb-0000-0000-0000-000000000002', 'aaaaaaaa-0000-0000-0000-000000000002', '33333333-3333-3333-3333-333333333333', 'Dealer Beta',  'ACTIVE', '2026-01-01', 'tenant-demo')
ON CONFLICT (id) DO NOTHING;

-- ─── Inventory: locations ─────────────────────────────────────────────────────

\c inventory
INSERT INTO location (id, name, type, address, tenant_id)
VALUES
  ('dddddddd-0000-0000-0000-000000000001', 'Central Warehouse',      'WAREHOUSE',        '1 Warehouse Rd, City',    'tenant-demo'),
  ('dddddddd-0000-0000-0000-000000000002', 'Main Street Own Shop',   'OWN_SHOP',         '10 Main St, City',        'tenant-demo'),
  ('dddddddd-0000-0000-0000-000000000003', 'Dealer Alpha Outlet',    'DEALER_OUTLET',    '22 Alpha Ave, City',      'tenant-demo'),
  ('dddddddd-0000-0000-0000-000000000004', 'Dealer Beta Outlet',     'DEALER_OUTLET',    '55 Beta Blvd, Uptown',    'tenant-demo'),
  ('dddddddd-0000-0000-0000-000000000005', 'Regional DC North',      'DISTRIBUTION_CENTER', '100 North Ring Rd',   'tenant-demo')
ON CONFLICT (id) DO NOTHING;

-- Stock-on-hand at Central Warehouse (product IDs match product_catalog seed below)
INSERT INTO product_inventory (id, product_id, product_name, location_id, location_type, quantity, status, tenant_id)
VALUES
  -- Handsets
  ('eeeeeeee-0000-0000-0000-000000000001', 'f1000001-0000-0000-0000-000000000000', 'Apple iPhone 16 Pro 256GB Black',       'dddddddd-0000-0000-0000-000000000001', 'WAREHOUSE', 50,    'AVAILABLE', 'tenant-demo'),
  ('eeeeeeee-0000-0000-0000-000000000002', 'f1000002-0000-0000-0000-000000000000', 'Samsung Galaxy S25 Ultra 512GB Silver', 'dddddddd-0000-0000-0000-000000000001', 'WAREHOUSE', 80,    'AVAILABLE', 'tenant-demo'),
  ('eeeeeeee-0000-0000-0000-000000000003', 'f1000003-0000-0000-0000-000000000000', 'Huawei Pura 70 Pro 128GB Green',        'dddddddd-0000-0000-0000-000000000001', 'WAREHOUSE', 120,   'AVAILABLE', 'tenant-demo'),
  -- SIM cards
  ('eeeeeeee-0000-0000-0000-000000000010', 'f2000001-0000-0000-0000-000000000000', 'Prepaid SIM Starter Pack',              'dddddddd-0000-0000-0000-000000000001', 'WAREHOUSE', 5000,  'AVAILABLE', 'tenant-demo'),
  ('eeeeeeee-0000-0000-0000-000000000011', 'f2000002-0000-0000-0000-000000000000', 'Data SIM 4G/LTE Pack',                  'dddddddd-0000-0000-0000-000000000001', 'WAREHOUSE', 3000,  'AVAILABLE', 'tenant-demo'),
  -- Set-top boxes
  ('eeeeeeee-0000-0000-0000-000000000020', 'f3000001-0000-0000-0000-000000000000', 'HD Satellite Decoder',                  'dddddddd-0000-0000-0000-000000000001', 'WAREHOUSE', 200,   'AVAILABLE', 'tenant-demo'),
  ('eeeeeeee-0000-0000-0000-000000000021', 'f3000002-0000-0000-0000-000000000000', '4K UHD Cable Decoder',                  'dddddddd-0000-0000-0000-000000000001', 'WAREHOUSE', 150,   'AVAILABLE', 'tenant-demo'),
  -- OTT TV boxes
  ('eeeeeeee-0000-0000-0000-000000000025', 'f4000001-0000-0000-0000-000000000000', 'Android TV Box 4K',                     'dddddddd-0000-0000-0000-000000000001', 'WAREHOUSE', 300,   'AVAILABLE', 'tenant-demo'),
  -- Cash / recharge cards
  ('eeeeeeee-0000-0000-0000-000000000030', 'f5000001-0000-0000-0000-000000000000', 'Airtime Voucher $5',                    'dddddddd-0000-0000-0000-000000000001', 'WAREHOUSE', 10000, 'AVAILABLE', 'tenant-demo'),
  ('eeeeeeee-0000-0000-0000-000000000031', 'f5000002-0000-0000-0000-000000000000', 'Airtime Voucher $10',                   'dddddddd-0000-0000-0000-000000000001', 'WAREHOUSE', 5000,  'AVAILABLE', 'tenant-demo'),
  ('eeeeeeee-0000-0000-0000-000000000032', 'f5000003-0000-0000-0000-000000000000', 'Airtime Voucher $20',                   'dddddddd-0000-0000-0000-000000000001', 'WAREHOUSE', 2000,  'AVAILABLE', 'tenant-demo'),
  -- Mobile broadband / MiFi
  ('eeeeeeee-0000-0000-0000-000000000040', 'f6000001-0000-0000-0000-000000000000', 'Huawei 5G Mobile WiFi (MiFi)',          'dddddddd-0000-0000-0000-000000000001', 'WAREHOUSE', 80,    'AVAILABLE', 'tenant-demo'),
  -- CCTV
  ('eeeeeeee-0000-0000-0000-000000000050', 'f7000001-0000-0000-0000-000000000000', 'IP Camera 4MP PoE Outdoor',             'dddddddd-0000-0000-0000-000000000001', 'WAREHOUSE', 60,    'AVAILABLE', 'tenant-demo'),
  -- IoT
  ('eeeeeeee-0000-0000-0000-000000000060', 'f8000001-0000-0000-0000-000000000000', 'Smart Energy Meter (NB-IoT)',           'dddddddd-0000-0000-0000-000000000001', 'WAREHOUSE', 200,   'AVAILABLE', 'tenant-demo'),
  -- Fixed CPE / router
  ('eeeeeeee-0000-0000-0000-000000000070', 'f9000001-0000-0000-0000-000000000000', 'Fibre ONT (GPON)',                      'dddddddd-0000-0000-0000-000000000001', 'WAREHOUSE', 100,   'AVAILABLE', 'tenant-demo'),
  -- Tablet
  ('eeeeeeee-0000-0000-0000-000000000080', 'fa000001-0000-0000-0000-000000000000', 'Samsung Galaxy Tab S9 128GB WiFi',      'dddddddd-0000-0000-0000-000000000001', 'WAREHOUSE', 40,    'AVAILABLE', 'tenant-demo'),
  -- Accessories
  ('eeeeeeee-0000-0000-0000-000000000090', 'fb000001-0000-0000-0000-000000000000', 'GaN Charger 65W USB-C',                 'dddddddd-0000-0000-0000-000000000001', 'WAREHOUSE', 500,   'AVAILABLE', 'tenant-demo'),
  ('eeeeeeee-0000-0000-0000-000000000091', 'fb000002-0000-0000-0000-000000000000', 'Universal Phone Case (6.5")',           'dddddddd-0000-0000-0000-000000000001', 'WAREHOUSE', 300,   'AVAILABLE', 'tenant-demo')
ON CONFLICT (id) DO NOTHING;

-- Sample serialised resources: 3 handsets with IMEI, 5 SIM cards with ICCID, 2 STBs
INSERT INTO resource (id, resource_name, resource_type, product_id, inventory_id, location_id, status, batch_reference, supplier_reference, tenant_id)
VALUES
  -- iPhone 16 Pro units
  ('aaaaaaaa-a0a0-0000-0000-000000000001', 'iPhone 16 Pro 256GB Black #1',   'HANDSET', 'f1000001-0000-0000-0000-000000000000', 'eeeeeeee-0000-0000-0000-000000000001', 'dddddddd-0000-0000-0000-000000000001', 'AVAILABLE', 'BATCH-2026-01', 'APPLE-PO-001', 'tenant-demo'),
  ('aaaaaaaa-a0a0-0000-0000-000000000002', 'iPhone 16 Pro 256GB Black #2',   'HANDSET', 'f1000001-0000-0000-0000-000000000000', 'eeeeeeee-0000-0000-0000-000000000001', 'dddddddd-0000-0000-0000-000000000001', 'AVAILABLE', 'BATCH-2026-01', 'APPLE-PO-001', 'tenant-demo'),
  -- Samsung Galaxy S25 Ultra
  ('aaaaaaaa-a0a0-0000-0000-000000000003', 'Samsung Galaxy S25 Ultra #1',    'HANDSET', 'f1000002-0000-0000-0000-000000000000', 'eeeeeeee-0000-0000-0000-000000000002', 'dddddddd-0000-0000-0000-000000000001', 'AVAILABLE', 'BATCH-2026-01', 'SAMSG-PO-001', 'tenant-demo'),
  -- SIM cards
  ('aaaaaaaa-a0a0-0000-0000-000000000010', 'Prepaid SIM #001',               'SIM_CARD', 'f2000001-0000-0000-0000-000000000000', 'eeeeeeee-0000-0000-0000-000000000010', 'dddddddd-0000-0000-0000-000000000001', 'AVAILABLE', 'SIM-BATCH-A', NULL, 'tenant-demo'),
  ('aaaaaaaa-a0a0-0000-0000-000000000011', 'Prepaid SIM #002',               'SIM_CARD', 'f2000001-0000-0000-0000-000000000000', 'eeeeeeee-0000-0000-0000-000000000010', 'dddddddd-0000-0000-0000-000000000001', 'AVAILABLE', 'SIM-BATCH-A', NULL, 'tenant-demo'),
  ('aaaaaaaa-a0a0-0000-0000-000000000012', 'Prepaid Data SIM #001',          'SIM_CARD', 'f2000002-0000-0000-0000-000000000000', 'eeeeeeee-0000-0000-0000-000000000011', 'dddddddd-0000-0000-0000-000000000001', 'AVAILABLE', 'SIM-BATCH-B', NULL, 'tenant-demo'),
  -- Satellite STB
  ('aaaaaaaa-a0a0-0000-0000-000000000020', 'HD Satellite Decoder #1',        'SET_TOP_BOX', 'f3000001-0000-0000-0000-000000000000', 'eeeeeeee-0000-0000-0000-000000000020', 'dddddddd-0000-0000-0000-000000000001', 'AVAILABLE', 'STB-BATCH-01', 'STB-PO-001', 'tenant-demo'),
  ('aaaaaaaa-a0a0-0000-0000-000000000021', 'HD Satellite Decoder #2',        'SET_TOP_BOX', 'f3000001-0000-0000-0000-000000000000', 'eeeeeeee-0000-0000-0000-000000000020', 'dddddddd-0000-0000-0000-000000000001', 'AVAILABLE', 'STB-BATCH-01', 'STB-PO-001', 'tenant-demo')
ON CONFLICT (id) DO NOTHING;

-- Resource characteristics
INSERT INTO resource_characteristic (id, resource_id, name, value, tenant_id)
VALUES
  -- iPhone 16 Pro #1
  ('bbbbbbbb-b0b0-0000-0000-000000000001', 'aaaaaaaa-a0a0-0000-0000-000000000001', 'IMEI',        '358240051111110', 'tenant-demo'),
  ('bbbbbbbb-b0b0-0000-0000-000000000002', 'aaaaaaaa-a0a0-0000-0000-000000000001', 'COLOR',       'Black Titanium',  'tenant-demo'),
  ('bbbbbbbb-b0b0-0000-0000-000000000003', 'aaaaaaaa-a0a0-0000-0000-000000000001', 'STORAGE_GB',  '256',             'tenant-demo'),
  -- iPhone 16 Pro #2 (IMEI and COLOR only; STORAGE_GB='256' omitted — same (name,value,tenant) as #1)
  ('bbbbbbbb-b0b0-0000-0000-000000000004', 'aaaaaaaa-a0a0-0000-0000-000000000002', 'IMEI',        '358240051111111', 'tenant-demo'),
  ('bbbbbbbb-b0b0-0000-0000-000000000005', 'aaaaaaaa-a0a0-0000-0000-000000000002', 'COLOR',       'White Titanium',  'tenant-demo'),
  -- Samsung Galaxy S25 Ultra #1
  ('bbbbbbbb-b0b0-0000-0000-000000000007', 'aaaaaaaa-a0a0-0000-0000-000000000003', 'IMEI',        '352099001761481', 'tenant-demo'),
  ('bbbbbbbb-b0b0-0000-0000-000000000008', 'aaaaaaaa-a0a0-0000-0000-000000000003', 'COLOR',       'Titanium Silver', 'tenant-demo'),
  ('bbbbbbbb-b0b0-0000-0000-000000000009', 'aaaaaaaa-a0a0-0000-0000-000000000003', 'STORAGE_GB',  '512',             'tenant-demo'),
  ('bbbbbbbb-b0b0-0000-0000-000000000010', 'aaaaaaaa-a0a0-0000-0000-000000000003', 'RAM_GB',      '12',              'tenant-demo'),
  -- Prepaid SIM #001
  ('bbbbbbbb-b0b0-0000-0000-000000000011', 'aaaaaaaa-a0a0-0000-0000-000000000010', 'ICCID',       '89310410100211118510', 'tenant-demo'),
  ('bbbbbbbb-b0b0-0000-0000-000000000012', 'aaaaaaaa-a0a0-0000-0000-000000000010', 'SIM_TYPE',    'NANO',                'tenant-demo'),
  -- Prepaid SIM #002 (ICCID only; SIM_TYPE='NANO' omitted — same (name,value,tenant) as #001)
  ('bbbbbbbb-b0b0-0000-0000-000000000013', 'aaaaaaaa-a0a0-0000-0000-000000000011', 'ICCID',       '89310410100211118511', 'tenant-demo'),
  -- Prepaid Data SIM
  ('bbbbbbbb-b0b0-0000-0000-000000000015', 'aaaaaaaa-a0a0-0000-0000-000000000012', 'ICCID',       '89310410100211118520', 'tenant-demo'),
  ('bbbbbbbb-b0b0-0000-0000-000000000016', 'aaaaaaaa-a0a0-0000-0000-000000000012', 'SIM_TYPE',    'MICRO',               'tenant-demo'),
  ('bbbbbbbb-b0b0-0000-0000-000000000017', 'aaaaaaaa-a0a0-0000-0000-000000000012', 'APN',         'data.telco.net',      'tenant-demo'),
  -- HD Satellite Decoder #1
  ('bbbbbbbb-b0b0-0000-0000-000000000018', 'aaaaaaaa-a0a0-0000-0000-000000000020', 'SERIAL_NUMBER',       'STB20260001A', 'tenant-demo'),
  ('bbbbbbbb-b0b0-0000-0000-000000000019', 'aaaaaaaa-a0a0-0000-0000-000000000020', 'SMART_CARD_NUMBER',   'CA-0000000001', 'tenant-demo'),
  ('bbbbbbbb-b0b0-0000-0000-000000000020', 'aaaaaaaa-a0a0-0000-0000-000000000020', 'MAC_ADDRESS',         '00:1A:79:AA:BB:01', 'tenant-demo'),
  -- HD Satellite Decoder #2
  ('bbbbbbbb-b0b0-0000-0000-000000000021', 'aaaaaaaa-a0a0-0000-0000-000000000021', 'SERIAL_NUMBER',       'STB20260002A', 'tenant-demo'),
  ('bbbbbbbb-b0b0-0000-0000-000000000022', 'aaaaaaaa-a0a0-0000-0000-000000000021', 'SMART_CARD_NUMBER',   'CA-0000000002', 'tenant-demo'),
  ('bbbbbbbb-b0b0-0000-0000-000000000023', 'aaaaaaaa-a0a0-0000-0000-000000000021', 'MAC_ADDRESS',         '00:1A:79:AA:BB:02', 'tenant-demo')
ON CONFLICT (id) DO NOTHING;

-- ─── Product Catalog ─────────────────────────────────────────────────────────

\c product_catalog

-- ── Handsets ──────────────────────────────────────────────────────────────────
INSERT INTO product (id, sku, name, barcode, product_type, category, brand, model_number, unit_price, denomination, tax_rate, commission_eligible, requires_serial_tracking, specifications, tenant_id)
VALUES
  ('f1000001-0000-0000-0000-000000000000', 'APL-IP16P-256-BLK', 'Apple iPhone 16 Pro 256GB Black',
   '0194253000001', 'HANDSET', 'HANDSET', 'Apple', 'iPhone 16 Pro', 1099.00, NULL, 0.15,
   true, true,
   '{"screen_size_inches": 6.3, "storage_gb": 256, "ram_gb": 8, "connectivity": ["5G","WiFi6E","Bluetooth5.3"], "os": "iOS 18", "camera_mp": 48, "battery_mah": 3582}',
   'tenant-demo'),

  ('f1000002-0000-0000-0000-000000000000', 'SAM-S25U-512-SLV', 'Samsung Galaxy S25 Ultra 512GB Silver',
   '8806095543901', 'HANDSET', 'HANDSET', 'Samsung', 'Galaxy S25 Ultra', 1299.00, NULL, 0.15,
   true, true,
   '{"screen_size_inches": 6.9, "storage_gb": 512, "ram_gb": 12, "connectivity": ["5G","WiFi7","Bluetooth5.3"], "os": "Android 15", "camera_mp": 200, "battery_mah": 5000}',
   'tenant-demo'),

  ('f1000003-0000-0000-0000-000000000000', 'HUW-P70-128-GRN', 'Huawei Pura 70 Pro 128GB Green',
   '6942103101512', 'HANDSET', 'HANDSET', 'Huawei', 'Pura 70 Pro', 649.00, NULL, 0.15,
   true, true,
   '{"screen_size_inches": 6.8, "storage_gb": 128, "ram_gb": 8, "connectivity": ["4G","WiFi6","Bluetooth5.2"], "os": "HarmonyOS 4", "camera_mp": 50, "battery_mah": 5000}',
   'tenant-demo'),

  ('f1000004-0000-0000-0000-000000000000', 'NKA-G60-64-BLK', 'Nokia G60 5G 64GB Black',
   '6438409057991', 'HANDSET', 'HANDSET', 'Nokia', 'G60 5G', 299.00, NULL, 0.15,
   true, true,
   '{"screen_size_inches": 6.58, "storage_gb": 64, "ram_gb": 4, "connectivity": ["5G","WiFi5","Bluetooth5.0"], "os": "Android 14", "camera_mp": 50, "battery_mah": 4500}',
   'tenant-demo'),

  ('f1000005-0000-0000-0000-000000000000', 'MOT-G84-256-BLU', 'Motorola Moto G84 256GB Blue',
   '0840023225032', 'HANDSET', 'HANDSET', 'Motorola', 'Moto G84', 229.00, NULL, 0.15,
   true, true,
   '{"screen_size_inches": 6.55, "storage_gb": 256, "ram_gb": 12, "connectivity": ["4G","WiFi5","Bluetooth5.0"], "os": "Android 14", "camera_mp": 50, "battery_mah": 5000}',
   'tenant-demo')
ON CONFLICT (id) DO NOTHING;

-- ── Tablets ───────────────────────────────────────────────────────────────────
INSERT INTO product (id, sku, name, barcode, product_type, category, brand, model_number, unit_price, denomination, tax_rate, commission_eligible, requires_serial_tracking, specifications, tenant_id)
VALUES
  ('fa000001-0000-0000-0000-000000000000', 'SAM-TAB-S9-128', 'Samsung Galaxy Tab S9 128GB WiFi',
   '8806094760835', 'TABLET', 'TABLET', 'Samsung', 'Galaxy Tab S9', 699.00, NULL, 0.15,
   true, true,
   '{"screen_size_inches": 11.0, "storage_gb": 128, "ram_gb": 8, "connectivity": ["WiFi6","Bluetooth5.3"], "os": "Android 14", "battery_mah": 8400}',
   'tenant-demo'),

  ('fa000002-0000-0000-0000-000000000000', 'HUW-MPAD-11-64', 'Huawei MatePad 11 64GB',
   '6941487204922', 'TABLET', 'TABLET', 'Huawei', 'MatePad 11', 399.00, NULL, 0.15,
   true, true,
   '{"screen_size_inches": 10.95, "storage_gb": 64, "ram_gb": 6, "connectivity": ["WiFi6","Bluetooth5.2"], "os": "HarmonyOS 3", "battery_mah": 7250}',
   'tenant-demo')
ON CONFLICT (id) DO NOTHING;

-- ── SIM Cards ─────────────────────────────────────────────────────────────────
INSERT INTO product (id, sku, name, barcode, product_type, category, brand, model_number, unit_price, denomination, tax_rate, commission_eligible, requires_serial_tracking, specifications, tenant_id)
VALUES
  ('f2000001-0000-0000-0000-000000000000', 'SIM-PRE-STD', 'Prepaid SIM Starter Pack',
   '5060099006001', 'SIM_CARD', 'PREPAID', NULL, NULL, 1.00, NULL, 0.00,
   true, true,
   '{"sim_format": "3-in-1 (standard/micro/nano)", "included_credit_usd": 1.00, "validity_days": 90, "network": "2G/3G/4G"}',
   'tenant-demo'),

  ('f2000002-0000-0000-0000-000000000000', 'SIM-DAT-4G', 'Data SIM 4G/LTE Pack',
   '5060099006002', 'SIM_CARD', 'DATA', NULL, NULL, 2.50, NULL, 0.00,
   true, true,
   '{"sim_format": "nano", "data_allowance_gb": 1, "validity_days": 30, "network": "4G LTE", "apn": "data.telco.net"}',
   'tenant-demo'),

  ('f2000003-0000-0000-0000-000000000000', 'SIM-IOT-M2M', 'IoT / M2M SIM (multi-IMSI)',
   '5060099006003', 'SIM_CARD', 'IOT', NULL, NULL, 5.00, NULL, 0.00,
   true, true,
   '{"sim_format": "industrial (2FF/3FF)", "multi_imsi": true, "network": "2G/4G/NB-IoT", "operating_temp_c": [-40, 85]}',
   'tenant-demo'),

  ('f2000004-0000-0000-0000-000000000000', 'ESIM-BUSI', 'eSIM Business Profile',
   '5060099006004', 'ESIM', 'POSTPAID', NULL, NULL, 0.00, NULL, 0.00,
   true, false,
   '{"delivery": "QR code / push", "profile_type": "GSMA M2M", "compatible_devices": ["iPhone XS+", "Samsung S20+", "Pixel 3+"]}',
   'tenant-demo')
ON CONFLICT (id) DO NOTHING;

-- ── Set-Top Boxes ─────────────────────────────────────────────────────────────
INSERT INTO product (id, sku, name, barcode, product_type, category, brand, model_number, unit_price, denomination, tax_rate, commission_eligible, requires_serial_tracking, specifications, tenant_id)
VALUES
  ('f3000001-0000-0000-0000-000000000000', 'STB-SAT-HD', 'HD Satellite Decoder',
   '6009880910011', 'SET_TOP_BOX', 'TV', NULL, 'SkyDec HD100', 89.00, NULL, 0.15,
   true, true,
   '{"resolution": "1080p HD", "tuner": "DVB-S2", "storage_gb": 250, "connectivity": ["HDMI","USB2","Ethernet"], "smart_card": true, "pvr": true}',
   'tenant-demo'),

  ('f3000002-0000-0000-0000-000000000000', 'STB-CAB-4K', '4K UHD Cable Decoder',
   '6009880910012', 'SET_TOP_BOX', 'TV', NULL, 'CablePro 4K200', 149.00, NULL, 0.15,
   true, true,
   '{"resolution": "4K UHD", "tuner": "DVB-C2", "storage_gb": 500, "connectivity": ["HDMI2.1","USB3","Ethernet","WiFi5"], "smart_card": true, "pvr": true, "dolby_atmos": true}',
   'tenant-demo'),

  ('f3000003-0000-0000-0000-000000000000', 'STB-IPTV-4K', 'IPTV 4K Android Decoder',
   '6009880910013', 'SET_TOP_BOX', 'TV', NULL, 'IPBox 4K Pro', 119.00, NULL, 0.15,
   true, true,
   '{"resolution": "4K UHD", "os": "Android TV 11", "storage_gb": 16, "ram_gb": 2, "connectivity": ["HDMI2.0","USB2","Ethernet","WiFi5","Bluetooth4.2"], "voice_remote": true}',
   'tenant-demo')
ON CONFLICT (id) DO NOTHING;

-- ── OTT TV Boxes ──────────────────────────────────────────────────────────────
INSERT INTO product (id, sku, name, barcode, product_type, category, brand, model_number, unit_price, denomination, tax_rate, commission_eligible, requires_serial_tracking, specifications, tenant_id)
VALUES
  ('f4000001-0000-0000-0000-000000000000', 'OTT-AND-4K', 'Android TV Box 4K',
   '6009880920011', 'OTT_TV_BOX', 'TV', NULL, 'StreamBox Pro 4K', 59.00, NULL, 0.15,
   true, true,
   '{"resolution": "4K", "os": "Android TV 12", "storage_gb": 32, "ram_gb": 4, "connectivity": ["HDMI2.0","USB3","WiFi6","Bluetooth5.0"], "netflix_certified": true, "google_assistant": true}',
   'tenant-demo'),

  ('f4000002-0000-0000-0000-000000000000', 'OTT-FIRE-HD', 'Fire TV Stick 4K Max',
   '8435479922016', 'OTT_TV_BOX', 'TV', 'Amazon', 'Fire TV Stick 4K Max Gen2', 69.99, NULL, 0.15,
   true, true,
   '{"resolution": "4K Ultra HD", "connectivity": ["WiFi6E","Bluetooth5.2","HDMI"], "alexa": true, "dolby_atmos": true, "hdr": ["HDR10+","Dolby Vision"]}',
   'tenant-demo'),

  ('f4000003-0000-0000-0000-000000000000', 'OTT-CHRM-4K', 'Google Chromecast 4K',
   '0842776120152', 'OTT_TV_BOX', 'TV', 'Google', 'Chromecast with Google TV (4K)', 49.99, NULL, 0.15,
   true, true,
   '{"resolution": "4K HDR", "os": "Google TV", "connectivity": ["WiFi5","Bluetooth5.0","HDMI"], "google_assistant": true, "hdr": ["HDR10","HDR10+","HLG","Dolby Vision"]}',
   'tenant-demo')
ON CONFLICT (id) DO NOTHING;

-- ── Cash / Recharge Cards ─────────────────────────────────────────────────────
-- commission_eligible = false: vouchers are revenue pass-through, no dealer commission
INSERT INTO product (id, sku, name, barcode, product_type, category, brand, model_number, unit_price, denomination, tax_rate, commission_eligible, requires_serial_tracking, specifications, tenant_id)
VALUES
  ('f5000001-0000-0000-0000-000000000000', 'VCH-AIR-5', 'Airtime Voucher $5',
   '5060099001001', 'CASH_CARD', 'AIRTIME', NULL, NULL, 5.00, 5.00, 0.00,
   false, true,
   '{"type": "airtime", "valid_networks": ["2G","3G","4G"], "expiry_days_from_scratch": 30}',
   'tenant-demo'),

  ('f5000002-0000-0000-0000-000000000000', 'VCH-AIR-10', 'Airtime Voucher $10',
   '5060099001002', 'CASH_CARD', 'AIRTIME', NULL, NULL, 10.00, 10.00, 0.00,
   false, true,
   '{"type": "airtime", "valid_networks": ["2G","3G","4G"], "expiry_days_from_scratch": 60}',
   'tenant-demo'),

  ('f5000003-0000-0000-0000-000000000000', 'VCH-AIR-20', 'Airtime Voucher $20',
   '5060099001003', 'CASH_CARD', 'AIRTIME', NULL, NULL, 20.00, 20.00, 0.00,
   false, true,
   '{"type": "airtime", "valid_networks": ["2G","3G","4G"], "expiry_days_from_scratch": 90}',
   'tenant-demo'),

  ('f5000004-0000-0000-0000-000000000000', 'VCH-DAT-1G', 'Data Bundle Voucher 1GB',
   '5060099002001', 'CASH_CARD', 'DATA', NULL, NULL, 3.00, 3.00, 0.00,
   false, true,
   '{"type": "data_bundle", "data_gb": 1, "validity_days": 7, "network": "4G LTE"}',
   'tenant-demo'),

  ('f5000005-0000-0000-0000-000000000000', 'VCH-DAT-5G', 'Data Bundle Voucher 5GB',
   '5060099002002', 'CASH_CARD', 'DATA', NULL, NULL, 12.00, 12.00, 0.00,
   false, true,
   '{"type": "data_bundle", "data_gb": 5, "validity_days": 30, "network": "4G/5G"}',
   'tenant-demo'),

  ('f5000006-0000-0000-0000-000000000000', 'VCH-TV-MTH', 'TV Subscription Voucher 1 Month',
   '5060099003001', 'CASH_CARD', 'TV', NULL, NULL, 15.00, 15.00, 0.00,
   false, true,
   '{"type": "tv_subscription", "channels": 120, "validity_days": 30, "uhd_channels": 10}',
   'tenant-demo')
ON CONFLICT (id) DO NOTHING;

-- ── Mobile Broadband ──────────────────────────────────────────────────────────
INSERT INTO product (id, sku, name, barcode, product_type, category, brand, model_number, unit_price, denomination, tax_rate, commission_eligible, requires_serial_tracking, specifications, tenant_id)
VALUES
  ('f6000001-0000-0000-0000-000000000000', 'MBB-5G-MIFI', 'Huawei 5G Mobile WiFi (MiFi)',
   '6901443415762', 'MOBILE_BROADBAND', 'DATA', 'Huawei', '5G CPE Pro 3', 149.00, NULL, 0.15,
   true, true,
   '{"network": "5G NSA/SA", "max_speed_mbps": 3600, "wifi_standard": "WiFi 6", "battery_mah": 4000, "simultaneous_users": 32, "sim_slot": "nano"}',
   'tenant-demo'),

  ('f6000002-0000-0000-0000-000000000000', 'MBB-4G-DONGLE', '4G LTE USB Dongle',
   '6901443233335', 'MOBILE_BROADBAND', 'DATA', 'Huawei', 'E3372h-325', 49.00, NULL, 0.15,
   true, true,
   '{"network": "4G LTE Cat4", "max_speed_mbps": 150, "interface": "USB 2.0", "sim_slot": "micro"}',
   'tenant-demo')
ON CONFLICT (id) DO NOTHING;

-- ── CCTV / Surveillance ───────────────────────────────────────────────────────
INSERT INTO product (id, sku, name, barcode, product_type, category, brand, model_number, unit_price, denomination, tax_rate, commission_eligible, requires_serial_tracking, specifications, tenant_id)
VALUES
  ('f7000001-0000-0000-0000-000000000000', 'CCTV-IP-4MP', 'IP Camera 4MP PoE Outdoor',
   '6941412198866', 'CCTV', 'IOT', 'Hikvision', 'DS-2CD2T43G2-I5', 79.00, NULL, 0.15,
   true, true,
   '{"resolution_mp": 4, "night_vision_m": 60, "weatherproof": "IP67", "poe": true, "storage": "microSD+NAS", "ai_detection": ["person","vehicle"], "compression": "H.265+"}',
   'tenant-demo'),

  ('f7000002-0000-0000-0000-000000000000', 'CCTV-NVR-8CH', '8-Channel 4K NVR Recorder',
   '6941412216439', 'CCTV', 'IOT', 'Hikvision', 'DS-7608NXI-I2', 249.00, NULL, 0.15,
   true, true,
   '{"channels": 8, "max_resolution": "4K", "storage_bays": 2, "max_hdd_tb": 8, "poe_ports": 8, "ai_analytics": true, "remote_access": true}',
   'tenant-demo'),

  ('f7000003-0000-0000-0000-000000000000', 'CCTV-WIFI-2MP', 'WiFi Smart Camera 2MP Indoor',
   '6971408411038', 'CCTV', 'IOT', 'TP-Link', 'Tapo C220', 29.00, NULL, 0.15,
   true, true,
   '{"resolution_mp": 2, "night_vision": true, "wifi": "2.4/5GHz", "motion_detection": true, "two_way_audio": true, "cloud_storage": true, "local_storage": "microSD"}',
   'tenant-demo')
ON CONFLICT (id) DO NOTHING;

-- ── IoT Devices ───────────────────────────────────────────────────────────────
INSERT INTO product (id, sku, name, barcode, product_type, category, brand, model_number, unit_price, denomination, tax_rate, commission_eligible, requires_serial_tracking, specifications, tenant_id)
VALUES
  ('f8000001-0000-0000-0000-000000000000', 'IOT-MTR-SMRT', 'Smart Energy Meter (NB-IoT)',
   '6009880930011', 'IOT_DEVICE', 'IOT', NULL, 'SM-NB1', 45.00, NULL, 0.15,
   true, true,
   '{"connectivity": "NB-IoT B20/B28", "meter_type": "single_phase", "tamper_detection": true, "remote_disconnect": true, "data_interval_min": 15, "ip_rating": "IP54"}',
   'tenant-demo'),

  ('f8000002-0000-0000-0000-000000000000', 'IOT-GPS-TRACK', 'GPS Asset Tracker (4G)',
   '6009880930012', 'IOT_DEVICE', 'IOT', NULL, 'GT-4G-1', 35.00, NULL, 0.15,
   true, true,
   '{"connectivity": "4G LTE Cat-M1", "gps_accuracy_m": 3, "battery_life_days": 90, "geofencing": true, "motion_sensor": true, "ip_rating": "IP67"}',
   'tenant-demo'),

  ('f8000003-0000-0000-0000-000000000000', 'IOT-WIFI-RTR', 'Industrial WiFi Router (4G+WiFi)',
   '6009880930013', 'IOT_DEVICE', 'IOT', NULL, 'RUT240', 129.00, NULL, 0.15,
   true, true,
   '{"wan": ["4G LTE", "Ethernet"], "wifi": "802.11n 2.4GHz", "lan_ports": 2, "operating_temp_c": [-40, 75], "dual_sim": true, "din_rail": true}',
   'tenant-demo')
ON CONFLICT (id) DO NOTHING;

-- ── Fixed CPE / Home Broadband Equipment ──────────────────────────────────────
INSERT INTO product (id, sku, name, barcode, product_type, category, brand, model_number, unit_price, denomination, tax_rate, commission_eligible, requires_serial_tracking, specifications, tenant_id)
VALUES
  ('f9000001-0000-0000-0000-000000000000', 'CPE-FIBER-ONT', 'Fibre ONT (GPON)',
   '6001417011132', 'FIXED_CPE', 'FIXED_BROADBAND', 'Huawei', 'HG8245X6', 59.00, NULL, 0.15,
   true, true,
   '{"interface": "GPON", "wan_speed_gbps": 2.5, "wifi_standard": "WiFi 6", "lan_ports": 4, "usb_ports": 2, "voice_ports": 2, "pots": true}',
   'tenant-demo'),

  ('f9000002-0000-0000-0000-000000000000', 'CPE-ADSL-RTR', 'ADSL2+ Wireless Router',
   '6001417011133', 'FIXED_CPE', 'FIXED_BROADBAND', 'TP-Link', 'TD-W8961N', 39.00, NULL, 0.15,
   true, true,
   '{"interface": "ADSL2+", "max_speed_mbps": 24, "wifi_standard": "802.11n", "lan_ports": 4, "voice_ports": 1}',
   'tenant-demo'),

  ('f9000003-0000-0000-0000-000000000000', 'CPE-5G-HOME', '5G Home Gateway',
   '6001417011134', 'FIXED_CPE', 'FIXED_BROADBAND', 'Huawei', '5G CPE Win', 199.00, NULL, 0.15,
   true, true,
   '{"network": "5G NSA/SA", "max_speed_gbps": 3.6, "wifi_standard": "WiFi 6", "lan_ports": 3, "poe_out": false, "external_antenna": true}',
   'tenant-demo')
ON CONFLICT (id) DO NOTHING;

-- ── Accessories ───────────────────────────────────────────────────────────────
INSERT INTO product (id, sku, name, barcode, product_type, category, brand, model_number, unit_price, denomination, tax_rate, commission_eligible, requires_serial_tracking, specifications, tenant_id)
VALUES
  ('fb000001-0000-0000-0000-000000000000', 'ACC-CHG-65W', 'GaN Charger 65W USB-C',
   '6009880940001', 'ACCESSORY', 'ACCESSORY', NULL, NULL, 19.99, NULL, 0.15,
   true, false,
   '{"wattage": 65, "ports": ["USB-C PD3.0", "USB-A QC3.0"], "form_factor": "wall_plug", "cable_included": false}',
   'tenant-demo'),

  ('fb000002-0000-0000-0000-000000000000', 'ACC-CASE-UNV', 'Universal Phone Case (6.5")',
   '6009880940002', 'ACCESSORY', 'ACCESSORY', NULL, NULL, 4.99, NULL, 0.15,
   true, false,
   '{"compatible_screen_max_inches": 6.5, "material": "TPU", "military_grade_drop": true, "camera_cutout": true}',
   'tenant-demo'),

  ('fb000003-0000-0000-0000-000000000000', 'ACC-EARPH-TWS', 'True Wireless Earbuds',
   '6009880940003', 'ACCESSORY', 'ACCESSORY', NULL, NULL, 29.99, NULL, 0.15,
   true, false,
   '{"type": "TWS", "battery_life_hours": 8, "case_additional_hours": 24, "anc": false, "bluetooth": "5.2", "ipx": "IPX5", "charging": "USB-C"}',
   'tenant-demo'),

  ('fb000004-0000-0000-0000-000000000000', 'ACC-PWRBNK-20K', 'Power Bank 20000mAh',
   '6009880940004', 'ACCESSORY', 'ACCESSORY', NULL, NULL, 24.99, NULL, 0.15,
   true, false,
   '{"capacity_mah": 20000, "ports": ["USB-C PD 20W", "USB-A QC3.0 x2"], "pass_through": true, "display": "LED indicator"}',
   'tenant-demo')
ON CONFLICT (id) DO NOTHING;
