-- Demo seed data for local development — True Corporation (Thailand).
-- Idempotent (ON CONFLICT DO NOTHING). Run via: make seed
-- Writes directly to the databases — no auth tokens required for local dev.
--
-- All prices in THB, VAT 7% (0.07). Barcodes use Thailand EAN prefix 885
-- for True-branded items; global-brand items keep their real GTINs.
--
-- Covers:
--   party        — True distributor + two dealer chains
--   commission   — tiered agreement spec with per-category rules (THB)
--   inventory    — 5 Thai locations, SOH for seeded products
--   product_catalog — True product range (TrueMove H, TrueVisions, TrueID, Gigatex)
--   inventory.resource — sample serialised units with characteristics

-- ─── Party ───────────────────────────────────────────────────────────────────

\c party
INSERT INTO party (id, party_type, role, name, tax_number, status, parent_party_id, tenant_id)
VALUES
  ('11111111-0000-0000-0000-000000000001', 'ORGANIZATION', 'DISTRIBUTOR', 'True Distribution (Thailand) Co., Ltd.', 'TAX-0105-561-00001', 'ACTIVE', NULL,                                   'tenant-demo'),
  ('22222222-2222-2222-2222-222222222222', 'ORGANIZATION', 'DEALER',      'TG Fone — Siam Square',                  'TAX-TGF-001',        'ACTIVE', '11111111-0000-0000-0000-000000000001', 'tenant-demo'),
  ('33333333-3333-3333-3333-333333333333', 'ORGANIZATION', 'DEALER',      'Jaymart Mobile — MBK Center',            'TAX-JAY-001',        'ACTIVE', '11111111-0000-0000-0000-000000000001', 'tenant-demo')
ON CONFLICT (id) DO NOTHING;

-- ─── Commission rules ─────────────────────────────────────────────────────────

\c commission_rules

INSERT INTO agreement_spec (id, name, version, description, applicable_party_roles, effective_from, is_deleted, tenant_id)
VALUES
  ('aaaaaaaa-0000-0000-0000-000000000001', 'Standard True Dealer Commission', '2026.1', 'Tiered commission for all True dealers',          '["DEALER"]', '2026-01-01', false, 'tenant-demo'),
  ('aaaaaaaa-0000-0000-0000-000000000002', 'Handset Specialist Scheme',       '2026.1', 'Higher rates for high-volume handset dealers',    '["DEALER"]', '2026-01-01', false, 'tenant-demo'),
  ('aaaaaaaa-0000-0000-0000-000000000003', 'TrueVisions & TV Scheme',         '2026.1', 'Commission scheme for TrueVisions STBs and TV',   '["DEALER"]', '2026-01-01', false, 'tenant-demo')
ON CONFLICT (id) DO NOTHING;

-- Standard tiered rules (all categories)
INSERT INTO commission_rule (id, agreement_spec_id, product_category, channel_type, tier_min_qty, tier_max_qty, commission_type, commission_value, currency, conditions, priority, is_deleted, tenant_id)
VALUES
  ('cccccccc-0000-0000-0000-000000000001', 'aaaaaaaa-0000-0000-0000-000000000001', '*',       NULL, 1,  10,   'PERCENTAGE', 0.08, 'THB', '{}', 10, false, 'tenant-demo'),
  ('cccccccc-0000-0000-0000-000000000002', 'aaaaaaaa-0000-0000-0000-000000000001', '*',       NULL, 11, 50,   'PERCENTAGE', 0.12, 'THB', '{}', 20, false, 'tenant-demo'),
  ('cccccccc-0000-0000-0000-000000000003', 'aaaaaaaa-0000-0000-0000-000000000001', '*',       NULL, 51, NULL, 'PERCENTAGE', 0.15, 'THB', '{}', 30, false, 'tenant-demo'),
  -- SIM cards — lower margin, flat fee per unit (15 THB / SIM activation)
  ('cccccccc-0000-0000-0000-000000000004', 'aaaaaaaa-0000-0000-0000-000000000001', 'PREPAID', NULL, 1,  NULL, 'FLAT_AMOUNT', 15.00, 'THB', '{}', 5,  false, 'tenant-demo'),
  -- Cash / recharge cards — not eligible (handled by commission_eligible=false on product)
  -- Handset specialist scheme
  ('cccccccc-0000-0000-0000-000000000005', 'aaaaaaaa-0000-0000-0000-000000000002', 'HANDSET', NULL, 1,  20,   'PERCENTAGE', 0.10, 'THB', '{}', 10, false, 'tenant-demo'),
  ('cccccccc-0000-0000-0000-000000000006', 'aaaaaaaa-0000-0000-0000-000000000002', 'HANDSET', NULL, 21, NULL, 'PERCENTAGE', 0.14, 'THB', '{}', 20, false, 'tenant-demo'),
  -- TrueVisions / STB scheme
  ('cccccccc-0000-0000-0000-000000000007', 'aaaaaaaa-0000-0000-0000-000000000003', 'TV',      NULL, 1,  NULL, 'PERCENTAGE', 0.09, 'THB', '{}', 10, false, 'tenant-demo')
ON CONFLICT (id) DO NOTHING;

INSERT INTO agreement (id, agreement_spec_id, party_id, party_name, status, signed_date, tenant_id)
VALUES
  ('bbbbbbbb-0000-0000-0000-000000000001', 'aaaaaaaa-0000-0000-0000-000000000001', '22222222-2222-2222-2222-222222222222', 'TG Fone — Siam Square',       'ACTIVE', '2026-01-01', 'tenant-demo'),
  ('bbbbbbbb-0000-0000-0000-000000000002', 'aaaaaaaa-0000-0000-0000-000000000002', '33333333-3333-3333-3333-333333333333', 'Jaymart Mobile — MBK Center', 'ACTIVE', '2026-01-01', 'tenant-demo')
ON CONFLICT (id) DO NOTHING;

-- ─── Inventory: locations ─────────────────────────────────────────────────────

\c inventory
INSERT INTO location (id, name, type, address, tenant_id)
VALUES
  ('dddddddd-0000-0000-0000-000000000001', 'True Distribution Center — Bang Na', 'WAREHOUSE',           '88 Bang Na-Trat Rd, Bang Na, Bangkok 10260',     'tenant-demo'),
  ('dddddddd-0000-0000-0000-000000000002', 'True Shop — CentralWorld',           'OWN_SHOP',            '999/9 Rama I Rd, Pathum Wan, Bangkok 10330',     'tenant-demo'),
  ('dddddddd-0000-0000-0000-000000000003', 'TG Fone — Siam Square',              'DEALER_OUTLET',       '254 Phaya Thai Rd, Pathum Wan, Bangkok 10330',   'tenant-demo'),
  ('dddddddd-0000-0000-0000-000000000004', 'Jaymart Mobile — MBK Center',        'DEALER_OUTLET',       '444 Phaya Thai Rd, Wang Mai, Bangkok 10330',     'tenant-demo'),
  ('dddddddd-0000-0000-0000-000000000005', 'True Regional DC — Chiang Mai',      'DISTRIBUTION_CENTER', '199 Super Highway Rd, Chiang Mai 50000',         'tenant-demo')
ON CONFLICT (id) DO NOTHING;

-- Stock-on-hand at Bang Na DC (product IDs match product_catalog seed below)
INSERT INTO product_inventory (id, product_id, product_name, location_id, location_type, quantity, status, tenant_id)
VALUES
  -- Handsets
  ('eeeeeeee-0000-0000-0000-000000000001', 'f1000001-0000-0000-0000-000000000000', 'Apple iPhone 16 Pro 256GB Black Titanium',     'dddddddd-0000-0000-0000-000000000001', 'WAREHOUSE', 50,    'AVAILABLE', 'tenant-demo'),
  ('eeeeeeee-0000-0000-0000-000000000002', 'f1000002-0000-0000-0000-000000000000', 'Samsung Galaxy S25 Ultra 512GB Titanium Silver','dddddddd-0000-0000-0000-000000000001', 'WAREHOUSE', 80,    'AVAILABLE', 'tenant-demo'),
  ('eeeeeeee-0000-0000-0000-000000000003', 'f1000003-0000-0000-0000-000000000000', 'OPPO Find X8 256GB Space Black',               'dddddddd-0000-0000-0000-000000000001', 'WAREHOUSE', 120,   'AVAILABLE', 'tenant-demo'),
  -- SIM cards
  ('eeeeeeee-0000-0000-0000-000000000010', 'f2000001-0000-0000-0000-000000000000', 'TrueMove H Prepaid SIM Starter Pack',          'dddddddd-0000-0000-0000-000000000001', 'WAREHOUSE', 5000,  'AVAILABLE', 'tenant-demo'),
  ('eeeeeeee-0000-0000-0000-000000000011', 'f2000002-0000-0000-0000-000000000000', 'TrueMove H Tourist SIM 15GB / 8 Days',         'dddddddd-0000-0000-0000-000000000001', 'WAREHOUSE', 3000,  'AVAILABLE', 'tenant-demo'),
  -- Set-top boxes
  ('eeeeeeee-0000-0000-0000-000000000020', 'f3000001-0000-0000-0000-000000000000', 'TrueVisions HD Set-Top Box',                   'dddddddd-0000-0000-0000-000000000001', 'WAREHOUSE', 200,   'AVAILABLE', 'tenant-demo'),
  ('eeeeeeee-0000-0000-0000-000000000021', 'f3000002-0000-0000-0000-000000000000', 'TrueVisions 4K UHD Set-Top Box',               'dddddddd-0000-0000-0000-000000000001', 'WAREHOUSE', 150,   'AVAILABLE', 'tenant-demo'),
  -- OTT TV boxes
  ('eeeeeeee-0000-0000-0000-000000000025', 'f4000001-0000-0000-0000-000000000000', 'TrueID TV Box Gen 2 (4K)',                     'dddddddd-0000-0000-0000-000000000001', 'WAREHOUSE', 300,   'AVAILABLE', 'tenant-demo'),
  -- Cash / refill cards
  ('eeeeeeee-0000-0000-0000-000000000030', 'f5000001-0000-0000-0000-000000000000', 'TrueMove H Refill Card 50 THB',                'dddddddd-0000-0000-0000-000000000001', 'WAREHOUSE', 10000, 'AVAILABLE', 'tenant-demo'),
  ('eeeeeeee-0000-0000-0000-000000000031', 'f5000002-0000-0000-0000-000000000000', 'TrueMove H Refill Card 100 THB',               'dddddddd-0000-0000-0000-000000000001', 'WAREHOUSE', 5000,  'AVAILABLE', 'tenant-demo'),
  ('eeeeeeee-0000-0000-0000-000000000032', 'f5000003-0000-0000-0000-000000000000', 'TrueMove H Refill Card 300 THB',               'dddddddd-0000-0000-0000-000000000001', 'WAREHOUSE', 2000,  'AVAILABLE', 'tenant-demo'),
  -- Mobile broadband / Pocket WiFi
  ('eeeeeeee-0000-0000-0000-000000000040', 'f6000001-0000-0000-0000-000000000000', 'True 5G Pocket WiFi',                          'dddddddd-0000-0000-0000-000000000001', 'WAREHOUSE', 80,    'AVAILABLE', 'tenant-demo'),
  -- CCTV
  ('eeeeeeee-0000-0000-0000-000000000050', 'f7000001-0000-0000-0000-000000000000', 'True CCTV Outdoor 4MP PoE Camera',             'dddddddd-0000-0000-0000-000000000001', 'WAREHOUSE', 60,    'AVAILABLE', 'tenant-demo'),
  -- IoT
  ('eeeeeeee-0000-0000-0000-000000000060', 'f8000001-0000-0000-0000-000000000000', 'True IoT Smart Energy Meter (NB-IoT)',         'dddddddd-0000-0000-0000-000000000001', 'WAREHOUSE', 200,   'AVAILABLE', 'tenant-demo'),
  -- Fixed CPE / router
  ('eeeeeeee-0000-0000-0000-000000000070', 'f9000001-0000-0000-0000-000000000000', 'True Gigatex Fiber ONT (WiFi 6)',              'dddddddd-0000-0000-0000-000000000001', 'WAREHOUSE', 100,   'AVAILABLE', 'tenant-demo'),
  -- Tablet
  ('eeeeeeee-0000-0000-0000-000000000080', 'fa000001-0000-0000-0000-000000000000', 'Samsung Galaxy Tab S9 128GB WiFi',             'dddddddd-0000-0000-0000-000000000001', 'WAREHOUSE', 40,    'AVAILABLE', 'tenant-demo'),
  -- Accessories
  ('eeeeeeee-0000-0000-0000-000000000090', 'fb000001-0000-0000-0000-000000000000', 'GaN Charger 65W USB-C',                        'dddddddd-0000-0000-0000-000000000001', 'WAREHOUSE', 500,   'AVAILABLE', 'tenant-demo'),
  ('eeeeeeee-0000-0000-0000-000000000091', 'fb000002-0000-0000-0000-000000000000', 'Universal Phone Case (6.5")',                  'dddddddd-0000-0000-0000-000000000001', 'WAREHOUSE', 300,   'AVAILABLE', 'tenant-demo')
ON CONFLICT (id) DO NOTHING;

-- Sample serialised resources: 3 handsets with IMEI, 3 SIM cards with ICCID, 2 STBs
INSERT INTO resource (id, resource_name, resource_type, product_id, inventory_id, location_id, status, batch_reference, supplier_reference, tenant_id)
VALUES
  -- iPhone 16 Pro units
  ('aaaaaaaa-a0a0-0000-0000-000000000001', 'iPhone 16 Pro 256GB Black #1',     'HANDSET', 'f1000001-0000-0000-0000-000000000000', 'eeeeeeee-0000-0000-0000-000000000001', 'dddddddd-0000-0000-0000-000000000001', 'AVAILABLE', 'BATCH-2026-01', 'APPLE-PO-001', 'tenant-demo'),
  ('aaaaaaaa-a0a0-0000-0000-000000000002', 'iPhone 16 Pro 256GB Black #2',     'HANDSET', 'f1000001-0000-0000-0000-000000000000', 'eeeeeeee-0000-0000-0000-000000000001', 'dddddddd-0000-0000-0000-000000000001', 'AVAILABLE', 'BATCH-2026-01', 'APPLE-PO-001', 'tenant-demo'),
  -- Samsung Galaxy S25 Ultra
  ('aaaaaaaa-a0a0-0000-0000-000000000003', 'Samsung Galaxy S25 Ultra #1',      'HANDSET', 'f1000002-0000-0000-0000-000000000000', 'eeeeeeee-0000-0000-0000-000000000002', 'dddddddd-0000-0000-0000-000000000001', 'AVAILABLE', 'BATCH-2026-01', 'SAMSG-PO-001', 'tenant-demo'),
  -- SIM cards
  ('aaaaaaaa-a0a0-0000-0000-000000000010', 'TrueMove H Prepaid SIM #001',      'SIM_CARD', 'f2000001-0000-0000-0000-000000000000', 'eeeeeeee-0000-0000-0000-000000000010', 'dddddddd-0000-0000-0000-000000000001', 'AVAILABLE', 'SIM-BATCH-A', NULL, 'tenant-demo'),
  ('aaaaaaaa-a0a0-0000-0000-000000000011', 'TrueMove H Prepaid SIM #002',      'SIM_CARD', 'f2000001-0000-0000-0000-000000000000', 'eeeeeeee-0000-0000-0000-000000000010', 'dddddddd-0000-0000-0000-000000000001', 'AVAILABLE', 'SIM-BATCH-A', NULL, 'tenant-demo'),
  ('aaaaaaaa-a0a0-0000-0000-000000000012', 'TrueMove H Tourist SIM #001',      'SIM_CARD', 'f2000002-0000-0000-0000-000000000000', 'eeeeeeee-0000-0000-0000-000000000011', 'dddddddd-0000-0000-0000-000000000001', 'AVAILABLE', 'SIM-BATCH-B', NULL, 'tenant-demo'),
  -- TrueVisions STB
  ('aaaaaaaa-a0a0-0000-0000-000000000020', 'TrueVisions HD STB #1',            'SET_TOP_BOX', 'f3000001-0000-0000-0000-000000000000', 'eeeeeeee-0000-0000-0000-000000000020', 'dddddddd-0000-0000-0000-000000000001', 'AVAILABLE', 'STB-BATCH-01', 'STB-PO-001', 'tenant-demo'),
  ('aaaaaaaa-a0a0-0000-0000-000000000021', 'TrueVisions HD STB #2',            'SET_TOP_BOX', 'f3000001-0000-0000-0000-000000000000', 'eeeeeeee-0000-0000-0000-000000000020', 'dddddddd-0000-0000-0000-000000000001', 'AVAILABLE', 'STB-BATCH-01', 'STB-PO-001', 'tenant-demo')
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
  -- TrueMove H Prepaid SIM #001 (Thai ICCID prefix 8966: MCC 520 Thailand, True)
  ('bbbbbbbb-b0b0-0000-0000-000000000011', 'aaaaaaaa-a0a0-0000-0000-000000000010', 'ICCID',       '8966041010021111851', 'tenant-demo'),
  ('bbbbbbbb-b0b0-0000-0000-000000000012', 'aaaaaaaa-a0a0-0000-0000-000000000010', 'SIM_TYPE',    'NANO',                'tenant-demo'),
  -- TrueMove H Prepaid SIM #002 (ICCID only; SIM_TYPE='NANO' omitted — same (name,value,tenant) as #001)
  ('bbbbbbbb-b0b0-0000-0000-000000000013', 'aaaaaaaa-a0a0-0000-0000-000000000011', 'ICCID',       '8966041010021111852', 'tenant-demo'),
  -- TrueMove H Tourist SIM
  ('bbbbbbbb-b0b0-0000-0000-000000000015', 'aaaaaaaa-a0a0-0000-0000-000000000012', 'ICCID',       '8966041010021111860', 'tenant-demo'),
  ('bbbbbbbb-b0b0-0000-0000-000000000016', 'aaaaaaaa-a0a0-0000-0000-000000000012', 'SIM_TYPE',    'MICRO',               'tenant-demo'),
  ('bbbbbbbb-b0b0-0000-0000-000000000017', 'aaaaaaaa-a0a0-0000-0000-000000000012', 'APN',         'internet',            'tenant-demo'),
  -- TrueVisions HD STB #1
  ('bbbbbbbb-b0b0-0000-0000-000000000018', 'aaaaaaaa-a0a0-0000-0000-000000000020', 'SERIAL_NUMBER',       'TVS20260001A', 'tenant-demo'),
  ('bbbbbbbb-b0b0-0000-0000-000000000019', 'aaaaaaaa-a0a0-0000-0000-000000000020', 'SMART_CARD_NUMBER',   'CA-0000000001', 'tenant-demo'),
  ('bbbbbbbb-b0b0-0000-0000-000000000020', 'aaaaaaaa-a0a0-0000-0000-000000000020', 'MAC_ADDRESS',         '00:1A:79:AA:BB:01', 'tenant-demo'),
  -- TrueVisions HD STB #2
  ('bbbbbbbb-b0b0-0000-0000-000000000021', 'aaaaaaaa-a0a0-0000-0000-000000000021', 'SERIAL_NUMBER',       'TVS20260002A', 'tenant-demo'),
  ('bbbbbbbb-b0b0-0000-0000-000000000022', 'aaaaaaaa-a0a0-0000-0000-000000000021', 'SMART_CARD_NUMBER',   'CA-0000000002', 'tenant-demo'),
  ('bbbbbbbb-b0b0-0000-0000-000000000023', 'aaaaaaaa-a0a0-0000-0000-000000000021', 'MAC_ADDRESS',         '00:1A:79:AA:BB:02', 'tenant-demo')
ON CONFLICT (id) DO NOTHING;

-- ─── Product Catalog ─────────────────────────────────────────────────────────
-- Prices in THB. VAT 7% (0.07). Vouchers carry face value (denomination), 0% VAT.

\c product_catalog

-- ── Handsets ──────────────────────────────────────────────────────────────────
INSERT INTO product (id, sku, name, barcode, product_type, category, brand, model_number, unit_price, denomination, tax_rate, commission_eligible, requires_serial_tracking, specifications, tenant_id)
VALUES
  ('f1000001-0000-0000-0000-000000000000', 'APL-IP16P-256-BLK', 'Apple iPhone 16 Pro 256GB Black Titanium',
   '0194253000001', 'HANDSET', 'HANDSET', 'Apple', 'iPhone 16 Pro', 41900.00, NULL, 0.07,
   true, true,
   '{"screen_size_inches": 6.3, "storage_gb": 256, "ram_gb": 8, "connectivity": ["5G","WiFi6E","Bluetooth5.3"], "os": "iOS 18", "camera_mp": 48, "battery_mah": 3582}',
   'tenant-demo'),

  ('f1000002-0000-0000-0000-000000000000', 'SAM-S25U-512-SLV', 'Samsung Galaxy S25 Ultra 512GB Titanium Silver',
   '8806095543901', 'HANDSET', 'HANDSET', 'Samsung', 'Galaxy S25 Ultra', 47900.00, NULL, 0.07,
   true, true,
   '{"screen_size_inches": 6.9, "storage_gb": 512, "ram_gb": 12, "connectivity": ["5G","WiFi7","Bluetooth5.3"], "os": "Android 15", "camera_mp": 200, "battery_mah": 5000}',
   'tenant-demo'),

  ('f1000003-0000-0000-0000-000000000000', 'OPP-FX8-256-BLK', 'OPPO Find X8 256GB Space Black',
   '6944284600013', 'HANDSET', 'HANDSET', 'OPPO', 'Find X8', 29990.00, NULL, 0.07,
   true, true,
   '{"screen_size_inches": 6.59, "storage_gb": 256, "ram_gb": 12, "connectivity": ["5G","WiFi6","Bluetooth5.4"], "os": "Android 15 / ColorOS 15", "camera_mp": 50, "battery_mah": 5630}',
   'tenant-demo'),

  ('f1000004-0000-0000-0000-000000000000', 'VIV-V40-256-BLU', 'vivo V40 5G 256GB Moonlight Blue',
   '6935117800004', 'HANDSET', 'HANDSET', 'vivo', 'V40 5G', 13999.00, NULL, 0.07,
   true, true,
   '{"screen_size_inches": 6.78, "storage_gb": 256, "ram_gb": 8, "connectivity": ["5G","WiFi6","Bluetooth5.4"], "os": "Android 14 / Funtouch 14", "camera_mp": 50, "battery_mah": 5500}',
   'tenant-demo'),

  ('f1000005-0000-0000-0000-000000000000', 'XIA-RN14P-256-BLK', 'Xiaomi Redmi Note 14 Pro 5G 256GB Black',
   '6941812700005', 'HANDSET', 'HANDSET', 'Xiaomi', 'Redmi Note 14 Pro 5G', 9999.00, NULL, 0.07,
   true, true,
   '{"screen_size_inches": 6.67, "storage_gb": 256, "ram_gb": 8, "connectivity": ["5G","WiFi6","Bluetooth5.3"], "os": "Android 14 / HyperOS", "camera_mp": 200, "battery_mah": 5110}',
   'tenant-demo')
ON CONFLICT (id) DO NOTHING;

-- ── Tablets ───────────────────────────────────────────────────────────────────
INSERT INTO product (id, sku, name, barcode, product_type, category, brand, model_number, unit_price, denomination, tax_rate, commission_eligible, requires_serial_tracking, specifications, tenant_id)
VALUES
  ('fa000001-0000-0000-0000-000000000000', 'SAM-TAB-S9-128', 'Samsung Galaxy Tab S9 128GB WiFi',
   '8806094760835', 'TABLET', 'TABLET', 'Samsung', 'Galaxy Tab S9', 24900.00, NULL, 0.07,
   true, true,
   '{"screen_size_inches": 11.0, "storage_gb": 128, "ram_gb": 8, "connectivity": ["WiFi6","Bluetooth5.3"], "os": "Android 14", "battery_mah": 8400}',
   'tenant-demo'),

  ('fa000002-0000-0000-0000-000000000000', 'APL-IPAD10-64', 'Apple iPad 10.9" 64GB WiFi',
   '0194253390002', 'TABLET', 'TABLET', 'Apple', 'iPad (10th gen)', 13900.00, NULL, 0.07,
   true, true,
   '{"screen_size_inches": 10.9, "storage_gb": 64, "connectivity": ["WiFi6","Bluetooth5.2"], "os": "iPadOS 18", "battery_mah": 7606}',
   'tenant-demo')
ON CONFLICT (id) DO NOTHING;

-- ── SIM Cards ─────────────────────────────────────────────────────────────────
INSERT INTO product (id, sku, name, barcode, product_type, category, brand, model_number, unit_price, denomination, tax_rate, commission_eligible, requires_serial_tracking, specifications, tenant_id)
VALUES
  ('f2000001-0000-0000-0000-000000000000', 'SIM-TMH-PRE', 'TrueMove H Prepaid SIM Starter Pack',
   '8850000000001', 'SIM_CARD', 'PREPAID', 'True', NULL, 49.00, NULL, 0.07,
   true, true,
   '{"sim_format": "3-in-1 (standard/micro/nano)", "included_credit_thb": 15.00, "validity_days": 30, "network": "4G/5G TrueMove H"}',
   'tenant-demo'),

  ('f2000002-0000-0000-0000-000000000000', 'SIM-TMH-TOUR', 'TrueMove H Tourist SIM 15GB / 8 Days',
   '8850000000002', 'SIM_CARD', 'PREPAID', 'True', NULL, 299.00, NULL, 0.07,
   true, true,
   '{"sim_format": "3-in-1", "data_allowance_gb": 15, "validity_days": 8, "network": "4G/5G TrueMove H", "apn": "internet", "includes_voice_credit_thb": 50}',
   'tenant-demo'),

  ('f2000003-0000-0000-0000-000000000000', 'SIM-TRUE-IOT', 'True IoT / M2M SIM (multi-IMSI)',
   '8850000000003', 'SIM_CARD', 'IOT', 'True', NULL, 150.00, NULL, 0.07,
   true, true,
   '{"sim_format": "industrial (2FF/3FF)", "multi_imsi": true, "network": "4G/NB-IoT", "operating_temp_c": [-40, 85]}',
   'tenant-demo'),

  ('f2000004-0000-0000-0000-000000000000', 'ESIM-TMH-BIZ', 'TrueMove H eSIM Business Profile',
   '8850000000004', 'ESIM', 'POSTPAID', 'True', NULL, 0.00, NULL, 0.07,
   true, false,
   '{"delivery": "QR code / push", "profile_type": "GSMA M2M", "compatible_devices": ["iPhone XS+", "Samsung S20+", "Pixel 3+"]}',
   'tenant-demo')
ON CONFLICT (id) DO NOTHING;

-- ── Set-Top Boxes (TrueVisions) ───────────────────────────────────────────────
INSERT INTO product (id, sku, name, barcode, product_type, category, brand, model_number, unit_price, denomination, tax_rate, commission_eligible, requires_serial_tracking, specifications, tenant_id)
VALUES
  ('f3000001-0000-0000-0000-000000000000', 'STB-TV-HD', 'TrueVisions HD Set-Top Box',
   '8850000010001', 'SET_TOP_BOX', 'TV', 'True', 'TrueVisions HD2', 1990.00, NULL, 0.07,
   true, true,
   '{"resolution": "1080p HD", "tuner": "DVB-S2", "storage_gb": 250, "connectivity": ["HDMI","USB2","Ethernet"], "smart_card": true, "pvr": true}',
   'tenant-demo'),

  ('f3000002-0000-0000-0000-000000000000', 'STB-TV-4K', 'TrueVisions 4K UHD Set-Top Box',
   '8850000010002', 'SET_TOP_BOX', 'TV', 'True', 'TrueVisions 4K Pro', 3490.00, NULL, 0.07,
   true, true,
   '{"resolution": "4K UHD", "tuner": "DVB-S2X", "storage_gb": 500, "connectivity": ["HDMI2.1","USB3","Ethernet","WiFi5"], "smart_card": true, "pvr": true, "dolby_atmos": true}',
   'tenant-demo'),

  ('f3000003-0000-0000-0000-000000000000', 'STB-TV-HYB', 'TrueVisions Hybrid IPTV Box',
   '8850000010003', 'SET_TOP_BOX', 'TV', 'True', 'TrueVisions Hybrid H1', 2490.00, NULL, 0.07,
   true, true,
   '{"resolution": "4K UHD", "os": "Android TV 11", "storage_gb": 16, "ram_gb": 2, "connectivity": ["HDMI2.0","USB2","Ethernet","WiFi5","Bluetooth4.2"], "voice_remote": true}',
   'tenant-demo')
ON CONFLICT (id) DO NOTHING;

-- ── OTT TV Boxes ──────────────────────────────────────────────────────────────
INSERT INTO product (id, sku, name, barcode, product_type, category, brand, model_number, unit_price, denomination, tax_rate, commission_eligible, requires_serial_tracking, specifications, tenant_id)
VALUES
  ('f4000001-0000-0000-0000-000000000000', 'OTT-TID-G2', 'TrueID TV Box Gen 2 (4K)',
   '8850000020001', 'OTT_TV_BOX', 'TV', 'True', 'TrueID TV Box V9610', 2290.00, NULL, 0.07,
   true, true,
   '{"resolution": "4K", "os": "Android TV 12", "storage_gb": 16, "ram_gb": 2, "connectivity": ["HDMI2.0","USB2","WiFi5","Bluetooth5.0"], "trueid_content": true, "netflix_certified": true, "google_assistant": true}',
   'tenant-demo'),

  ('f4000002-0000-0000-0000-000000000000', 'OTT-FIRE-4K', 'Fire TV Stick 4K Max',
   '8435479922016', 'OTT_TV_BOX', 'TV', 'Amazon', 'Fire TV Stick 4K Max Gen2', 1990.00, NULL, 0.07,
   true, true,
   '{"resolution": "4K Ultra HD", "connectivity": ["WiFi6E","Bluetooth5.2","HDMI"], "alexa": true, "dolby_atmos": true, "hdr": ["HDR10+","Dolby Vision"]}',
   'tenant-demo'),

  ('f4000003-0000-0000-0000-000000000000', 'OTT-CHRM-4K', 'Google Chromecast 4K',
   '0842776120152', 'OTT_TV_BOX', 'TV', 'Google', 'Chromecast with Google TV (4K)', 1790.00, NULL, 0.07,
   true, true,
   '{"resolution": "4K HDR", "os": "Google TV", "connectivity": ["WiFi5","Bluetooth5.0","HDMI"], "google_assistant": true, "hdr": ["HDR10","HDR10+","HLG","Dolby Vision"]}',
   'tenant-demo')
ON CONFLICT (id) DO NOTHING;

-- ── Cash / Refill Cards ───────────────────────────────────────────────────────
-- commission_eligible = false: vouchers are revenue pass-through, no dealer commission
INSERT INTO product (id, sku, name, barcode, product_type, category, brand, model_number, unit_price, denomination, tax_rate, commission_eligible, requires_serial_tracking, specifications, tenant_id)
VALUES
  ('f5000001-0000-0000-0000-000000000000', 'VCH-TMH-50', 'TrueMove H Refill Card 50 THB',
   '8850000030001', 'CASH_CARD', 'AIRTIME', 'True', NULL, 50.00, 50.00, 0.00,
   false, true,
   '{"type": "airtime", "network": "TrueMove H", "expiry_days_from_scratch": 30}',
   'tenant-demo'),

  ('f5000002-0000-0000-0000-000000000000', 'VCH-TMH-100', 'TrueMove H Refill Card 100 THB',
   '8850000030002', 'CASH_CARD', 'AIRTIME', 'True', NULL, 100.00, 100.00, 0.00,
   false, true,
   '{"type": "airtime", "network": "TrueMove H", "expiry_days_from_scratch": 60}',
   'tenant-demo'),

  ('f5000003-0000-0000-0000-000000000000', 'VCH-TMH-300', 'TrueMove H Refill Card 300 THB',
   '8850000030003', 'CASH_CARD', 'AIRTIME', 'True', NULL, 300.00, 300.00, 0.00,
   false, true,
   '{"type": "airtime", "network": "TrueMove H", "expiry_days_from_scratch": 90}',
   'tenant-demo'),

  ('f5000004-0000-0000-0000-000000000000', 'VCH-DAT-10G', 'True 5G Data Voucher 10GB / 30 Days',
   '8850000030004', 'CASH_CARD', 'DATA', 'True', NULL, 199.00, 199.00, 0.00,
   false, true,
   '{"type": "data_bundle", "data_gb": 10, "validity_days": 30, "network": "4G/5G TrueMove H"}',
   'tenant-demo'),

  ('f5000005-0000-0000-0000-000000000000', 'VCH-DAT-30G', 'True 5G Data Voucher 30GB / 30 Days',
   '8850000030005', 'CASH_CARD', 'DATA', 'True', NULL, 399.00, 399.00, 0.00,
   false, true,
   '{"type": "data_bundle", "data_gb": 30, "validity_days": 30, "network": "4G/5G TrueMove H"}',
   'tenant-demo'),

  ('f5000006-0000-0000-0000-000000000000', 'VCH-TV-MTH', 'TrueVisions Subscription Voucher 1 Month',
   '8850000030006', 'CASH_CARD', 'TV', 'True', NULL, 299.00, 299.00, 0.00,
   false, true,
   '{"type": "tv_subscription", "channels": 120, "validity_days": 30, "uhd_channels": 10}',
   'tenant-demo')
ON CONFLICT (id) DO NOTHING;

-- ── Mobile Broadband ──────────────────────────────────────────────────────────
INSERT INTO product (id, sku, name, barcode, product_type, category, brand, model_number, unit_price, denomination, tax_rate, commission_eligible, requires_serial_tracking, specifications, tenant_id)
VALUES
  ('f6000001-0000-0000-0000-000000000000', 'MBB-5G-MIFI', 'True 5G Pocket WiFi',
   '8850000040001', 'MOBILE_BROADBAND', 'DATA', 'True', 'True 5G Pocket WiFi Pro', 2990.00, NULL, 0.07,
   true, true,
   '{"network": "5G NSA/SA", "max_speed_mbps": 3600, "wifi_standard": "WiFi 6", "battery_mah": 4000, "simultaneous_users": 32, "sim_slot": "nano"}',
   'tenant-demo'),

  ('f6000002-0000-0000-0000-000000000000', 'MBB-4G-DGL', 'True 4G LTE USB Dongle',
   '6901443233335', 'MOBILE_BROADBAND', 'DATA', 'Huawei', 'E3372h-325', 990.00, NULL, 0.07,
   true, true,
   '{"network": "4G LTE Cat4", "max_speed_mbps": 150, "interface": "USB 2.0", "sim_slot": "micro"}',
   'tenant-demo')
ON CONFLICT (id) DO NOTHING;

-- ── CCTV / Surveillance ───────────────────────────────────────────────────────
INSERT INTO product (id, sku, name, barcode, product_type, category, brand, model_number, unit_price, denomination, tax_rate, commission_eligible, requires_serial_tracking, specifications, tenant_id)
VALUES
  ('f7000001-0000-0000-0000-000000000000', 'CCTV-IP-4MP', 'True CCTV Outdoor 4MP PoE Camera',
   '6941412198866', 'CCTV', 'IOT', 'Hikvision', 'DS-2CD2T43G2-I5', 2490.00, NULL, 0.07,
   true, true,
   '{"resolution_mp": 4, "night_vision_m": 60, "weatherproof": "IP67", "poe": true, "storage": "microSD+NAS", "ai_detection": ["person","vehicle"], "compression": "H.265+"}',
   'tenant-demo'),

  ('f7000002-0000-0000-0000-000000000000', 'CCTV-NVR-8CH', '8-Channel 4K NVR Recorder',
   '6941412216439', 'CCTV', 'IOT', 'Hikvision', 'DS-7608NXI-I2', 7990.00, NULL, 0.07,
   true, true,
   '{"channels": 8, "max_resolution": "4K", "storage_bays": 2, "max_hdd_tb": 8, "poe_ports": 8, "ai_analytics": true, "remote_access": true}',
   'tenant-demo'),

  ('f7000003-0000-0000-0000-000000000000', 'CCTV-WIFI-2MP', 'True X Smart Camera 2MP Indoor',
   '6971408411038', 'CCTV', 'IOT', 'TP-Link', 'Tapo C220', 990.00, NULL, 0.07,
   true, true,
   '{"resolution_mp": 2, "night_vision": true, "wifi": "2.4/5GHz", "motion_detection": true, "two_way_audio": true, "cloud_storage": true, "local_storage": "microSD"}',
   'tenant-demo')
ON CONFLICT (id) DO NOTHING;

-- ── IoT Devices ───────────────────────────────────────────────────────────────
INSERT INTO product (id, sku, name, barcode, product_type, category, brand, model_number, unit_price, denomination, tax_rate, commission_eligible, requires_serial_tracking, specifications, tenant_id)
VALUES
  ('f8000001-0000-0000-0000-000000000000', 'IOT-MTR-NB', 'True IoT Smart Energy Meter (NB-IoT)',
   '8850000050001', 'IOT_DEVICE', 'IOT', 'True', 'SM-NB1', 1490.00, NULL, 0.07,
   true, true,
   '{"connectivity": "NB-IoT B8/B20", "meter_type": "single_phase", "tamper_detection": true, "remote_disconnect": true, "data_interval_min": 15, "ip_rating": "IP54"}',
   'tenant-demo'),

  ('f8000002-0000-0000-0000-000000000000', 'IOT-GPS-4G', 'True IoT GPS Asset Tracker (4G)',
   '8850000050002', 'IOT_DEVICE', 'IOT', 'True', 'GT-4G-1', 1190.00, NULL, 0.07,
   true, true,
   '{"connectivity": "4G LTE Cat-M1", "gps_accuracy_m": 3, "battery_life_days": 90, "geofencing": true, "motion_sensor": true, "ip_rating": "IP67"}',
   'tenant-demo'),

  ('f8000003-0000-0000-0000-000000000000', 'IOT-RTR-IND', 'Industrial 4G WiFi Router',
   '8850000050003', 'IOT_DEVICE', 'IOT', 'Teltonika', 'RUT240', 4290.00, NULL, 0.07,
   true, true,
   '{"wan": ["4G LTE", "Ethernet"], "wifi": "802.11n 2.4GHz", "lan_ports": 2, "operating_temp_c": [-40, 75], "dual_sim": true, "din_rail": true}',
   'tenant-demo')
ON CONFLICT (id) DO NOTHING;

-- ── Fixed CPE / Home Broadband (True Online / Gigatex) ────────────────────────
INSERT INTO product (id, sku, name, barcode, product_type, category, brand, model_number, unit_price, denomination, tax_rate, commission_eligible, requires_serial_tracking, specifications, tenant_id)
VALUES
  ('f9000001-0000-0000-0000-000000000000', 'CPE-GTX-ONT', 'True Gigatex Fiber ONT (WiFi 6)',
   '8850000060001', 'FIXED_CPE', 'FIXED_BROADBAND', 'Huawei', 'HG8245X6', 1990.00, NULL, 0.07,
   true, true,
   '{"interface": "GPON", "wan_speed_gbps": 2.5, "wifi_standard": "WiFi 6", "lan_ports": 4, "usb_ports": 2, "voice_ports": 2, "pots": true}',
   'tenant-demo'),

  ('f9000002-0000-0000-0000-000000000000', 'CPE-GTX-MESH', 'True Gigatex Mesh WiFi 6 Router',
   '8850000060002', 'FIXED_CPE', 'FIXED_BROADBAND', 'True', 'Gigatex Mesh AX1800', 1490.00, NULL, 0.07,
   true, true,
   '{"wifi_standard": "WiFi 6 AX1800", "mesh": true, "lan_ports": 3, "coverage_sqm": 180, "backhaul": "wired/wireless"}',
   'tenant-demo'),

  ('f9000003-0000-0000-0000-000000000000', 'CPE-5G-HOME', 'True 5G Home WiFi Gateway',
   '8850000060003', 'FIXED_CPE', 'FIXED_BROADBAND', 'Huawei', '5G CPE Win', 4990.00, NULL, 0.07,
   true, true,
   '{"network": "5G NSA/SA", "max_speed_gbps": 3.6, "wifi_standard": "WiFi 6", "lan_ports": 3, "poe_out": false, "external_antenna": true}',
   'tenant-demo')
ON CONFLICT (id) DO NOTHING;

-- ── Accessories ───────────────────────────────────────────────────────────────
INSERT INTO product (id, sku, name, barcode, product_type, category, brand, model_number, unit_price, denomination, tax_rate, commission_eligible, requires_serial_tracking, specifications, tenant_id)
VALUES
  ('fb000001-0000-0000-0000-000000000000', 'ACC-CHG-65W', 'GaN Charger 65W USB-C',
   '8850000070001', 'ACCESSORY', 'ACCESSORY', NULL, NULL, 690.00, NULL, 0.07,
   true, false,
   '{"wattage": 65, "ports": ["USB-C PD3.0", "USB-A QC3.0"], "form_factor": "wall_plug", "cable_included": false}',
   'tenant-demo'),

  ('fb000002-0000-0000-0000-000000000000', 'ACC-CASE-UNV', 'Universal Phone Case (6.5")',
   '8850000070002', 'ACCESSORY', 'ACCESSORY', NULL, NULL, 199.00, NULL, 0.07,
   true, false,
   '{"compatible_screen_max_inches": 6.5, "material": "TPU", "military_grade_drop": true, "camera_cutout": true}',
   'tenant-demo'),

  ('fb000003-0000-0000-0000-000000000000', 'ACC-TWS', 'True Wireless Earbuds',
   '8850000070003', 'ACCESSORY', 'ACCESSORY', NULL, NULL, 1290.00, NULL, 0.07,
   true, false,
   '{"type": "TWS", "battery_life_hours": 8, "case_additional_hours": 24, "anc": false, "bluetooth": "5.2", "ipx": "IPX5", "charging": "USB-C"}',
   'tenant-demo'),

  ('fb000004-0000-0000-0000-000000000000', 'ACC-PWR-20K', 'Power Bank 20000mAh',
   '8850000070004', 'ACCESSORY', 'ACCESSORY', NULL, NULL, 890.00, NULL, 0.07,
   true, false,
   '{"capacity_mah": 20000, "ports": ["USB-C PD 20W", "USB-A QC3.0 x2"], "pass_through": true, "display": "LED indicator"}',
   'tenant-demo')
ON CONFLICT (id) DO NOTHING;
