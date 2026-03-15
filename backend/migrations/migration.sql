-- ============================================================
-- PO Management System - Database Migration + Seed Data
-- IV Innovations Private Limited
-- Run: psql -U postgres -d po_management -f migration.sql
-- ============================================================

-- Create database (run separately if needed)
-- CREATE DATABASE po_management;

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ─── DROP TABLES (clean slate) ──────────────────────────────
DROP TABLE IF EXISTS purchase_order_items CASCADE;
DROP TABLE IF EXISTS purchase_orders CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS vendors CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TYPE IF EXISTS postatus CASCADE;

-- ─── ENUM TYPE ──────────────────────────────────────────────
CREATE TYPE postatus AS ENUM ('draft', 'pending', 'approved', 'received', 'cancelled');

-- ─── USERS TABLE ────────────────────────────────────────────
CREATE TABLE users (
    id              SERIAL PRIMARY KEY,
    email           VARCHAR(255) UNIQUE NOT NULL,
    full_name       VARCHAR(255) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ─── VENDORS TABLE ──────────────────────────────────────────
CREATE TABLE vendors (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(255) NOT NULL,
    contact_email   VARCHAR(255) NOT NULL,
    contact_phone   VARCHAR(50),
    address         TEXT,
    rating          FLOAT DEFAULT 0.0 CHECK (rating >= 0 AND rating <= 5),
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ
);

CREATE INDEX idx_vendors_name ON vendors(name);
CREATE INDEX idx_vendors_is_active ON vendors(is_active);

-- ─── PRODUCTS TABLE ─────────────────────────────────────────
CREATE TABLE products (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(255) NOT NULL,
    sku             VARCHAR(100) UNIQUE NOT NULL,
    category        VARCHAR(100),
    unit_price      FLOAT NOT NULL CHECK (unit_price > 0),
    stock_level     INTEGER DEFAULT 0 CHECK (stock_level >= 0),
    unit            VARCHAR(50) DEFAULT 'unit',
    description     TEXT,
    ai_description  TEXT,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ
);

CREATE INDEX idx_products_sku ON products(sku);
CREATE INDEX idx_products_category ON products(category);
CREATE INDEX idx_products_is_active ON products(is_active);

-- ─── PURCHASE ORDERS TABLE ──────────────────────────────────
CREATE TABLE purchase_orders (
    id              SERIAL PRIMARY KEY,
    reference_no    VARCHAR(50) UNIQUE NOT NULL,
    vendor_id       INTEGER NOT NULL REFERENCES vendors(id) ON DELETE RESTRICT,
    status          postatus DEFAULT 'draft' NOT NULL,
    subtotal        FLOAT DEFAULT 0.0,
    tax_rate        FLOAT DEFAULT 0.05,
    tax_amount      FLOAT DEFAULT 0.0,
    total_amount    FLOAT DEFAULT 0.0,
    notes           TEXT,
    created_by      VARCHAR(255),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ
);

CREATE INDEX idx_po_vendor_id ON purchase_orders(vendor_id);
CREATE INDEX idx_po_status ON purchase_orders(status);
CREATE INDEX idx_po_reference_no ON purchase_orders(reference_no);

-- ─── PURCHASE ORDER ITEMS TABLE ─────────────────────────────
CREATE TABLE purchase_order_items (
    id                  SERIAL PRIMARY KEY,
    purchase_order_id   INTEGER NOT NULL REFERENCES purchase_orders(id) ON DELETE CASCADE,
    product_id          INTEGER NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    quantity            INTEGER NOT NULL CHECK (quantity > 0),
    unit_price          FLOAT NOT NULL CHECK (unit_price > 0),
    line_total          FLOAT NOT NULL
);

CREATE INDEX idx_poi_po_id ON purchase_order_items(purchase_order_id);
CREATE INDEX idx_poi_product_id ON purchase_order_items(product_id);

-- ─── SEED DATA ──────────────────────────────────────────────

-- Demo user (password: admin123)
INSERT INTO users (email, full_name, hashed_password) VALUES
(
    'admin@iv-innovations.com',
    'Admin User',
    '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW'  -- "secret" bcrypt
);

-- Vendors
INSERT INTO vendors (name, contact_email, contact_phone, address, rating) VALUES
('Tech Supplies Co.', 'sales@techsupplies.com', '+91-9876543210', '12, Industrial Area, Delhi', 4.5),
('Global Parts Ltd.', 'orders@globalparts.com', '+91-9988776655', '45, MIDC, Pune', 4.2),
('Reliable Hardware Inc.', 'contact@reliablehw.com', '+91-8877665544', 'Sector 18, Noida', 3.8),
('FastShip Electronics', 'b2b@fastship.in', '+91-7766554433', 'Electronics City, Bangalore', 4.7),
('Prime Materials', 'supply@primematerials.co', '+91-6655443322', 'Industrial Zone, Chennai', 4.0);

-- Products
INSERT INTO products (name, sku, category, unit_price, stock_level, unit) VALUES
('Intel Core i7 Processor',     'PROC-I7-001',   'Electronics',     28500.00,  50, 'unit'),
('Samsung 16GB DDR5 RAM',       'RAM-SAM-16G',   'Electronics',      6800.00, 120, 'unit'),
('WD 1TB SSD NVMe',             'SSD-WD-1TB',    'Storage',          8200.00,  80, 'unit'),
('Dell 27" 4K Monitor',         'MON-DEL-27',    'Peripherals',     32000.00,  25, 'unit'),
('Logitech MX Keys Keyboard',   'KEY-LOG-MX',    'Peripherals',      9500.00,  60, 'unit'),
('HP LaserJet Printer',         'PRT-HP-LJ',     'Office Equipment', 18500.00, 15, 'unit'),
('Cisco Gigabit Switch 24-port','NET-CIS-24P',   'Networking',      22000.00,  10, 'unit'),
('APC UPS 1000VA',              'UPS-APC-1K',    'Power',           12500.00,  30, 'unit'),
('Cat6 Network Cable (100m)',    'CAB-CAT6-100',  'Networking',       2800.00, 200, 'roll'),
('Thermal Paste (10g)',          'ACC-THRM-10G',  'Accessories',       350.00, 500, 'unit');

-- Sample Purchase Orders with Calculate Total (5% tax) applied
-- PO 1: Draft order
INSERT INTO purchase_orders (reference_no, vendor_id, status, subtotal, tax_rate, tax_amount, total_amount, notes, created_by)
VALUES ('PO-2024-DEMO01', 1, 'draft', 35300.00, 0.05, 1765.00, 37065.00, 'Initial hardware procurement', 'admin@iv-innovations.com');

INSERT INTO purchase_order_items (purchase_order_id, product_id, quantity, unit_price, line_total)
VALUES
    (1, 1, 1, 28500.00, 28500.00),
    (1, 2, 1, 6800.00, 6800.00);

-- PO 2: Approved order
INSERT INTO purchase_orders (reference_no, vendor_id, status, subtotal, tax_rate, tax_amount, total_amount, notes, created_by)
VALUES ('PO-2024-DEMO02', 4, 'approved', 40800.00, 0.05, 2040.00, 42840.00, 'Monitor and keyboard batch', 'admin@iv-innovations.com');

INSERT INTO purchase_order_items (purchase_order_id, product_id, quantity, unit_price, line_total)
VALUES
    (2, 4, 1, 32000.00, 32000.00),
    (2, 5, 2, 9500.00, 19000.00);  -- Note: 2 keyboards = wait, let's fix math

-- PO 3: Received
INSERT INTO purchase_orders (reference_no, vendor_id, status, subtotal, tax_rate, tax_amount, total_amount, notes, created_by)
VALUES ('PO-2024-DEMO03', 2, 'received', 25300.00, 0.05, 1265.00, 26565.00, 'Networking equipment', 'admin@iv-innovations.com');

INSERT INTO purchase_order_items (purchase_order_id, product_id, quantity, unit_price, line_total)
VALUES
    (3, 7, 1, 22000.00, 22000.00),
    (3, 9, 2, 2800.00, 5600.00);   -- Hmm 22000+5600=27600, let me restate: adjust totals for demo accuracy

-- Update PO3 subtotal to be correct
UPDATE purchase_orders SET subtotal=27600.00, tax_amount=1380.00, total_amount=28980.00 WHERE id=3;

-- PO2 fix: 32000 + 9500*1 = 41500 subtotal
UPDATE purchase_orders SET subtotal=41500.00, tax_amount=2075.00, total_amount=43575.00 WHERE id=2;
UPDATE purchase_order_items SET quantity=1, line_total=9500.00 WHERE purchase_order_id=2 AND product_id=5;

-- ─── VERIFY ─────────────────────────────────────────────────
SELECT 'Migration complete!' AS status;
SELECT COUNT(*) AS vendor_count FROM vendors;
SELECT COUNT(*) AS product_count FROM products;
SELECT COUNT(*) AS po_count FROM purchase_orders;
