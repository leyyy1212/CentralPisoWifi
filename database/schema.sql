-- ============================================================
-- Central PisoWiFi - Full Database Schema
-- Apply this in Supabase SQL Editor
-- ============================================================


-- ------------------------------------------------------------
-- TABLE 1: vouchers
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS vouchers (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    voucher_code        TEXT NOT NULL UNIQUE,
    total_minutes       INTEGER NOT NULL CHECK (total_minutes > 0),
    remaining_minutes   INTEGER NOT NULL CHECK (remaining_minutes >= 0),
    status              TEXT NOT NULL DEFAULT 'active'
                            CHECK (status IN ('active', 'used', 'suspended', 'exhausted')),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_vouchers_code ON vouchers (voucher_code);
CREATE INDEX IF NOT EXISTS idx_vouchers_status ON vouchers (status);


-- ------------------------------------------------------------
-- TABLE 2: hotspots
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS hotspots (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hotspot_code    TEXT NOT NULL UNIQUE,
    hotspot_name    TEXT NOT NULL,
    city            TEXT NOT NULL,
    latitude        NUMERIC(9, 6),
    longitude       NUMERIC(9, 6),
    status          TEXT NOT NULL DEFAULT 'active'
                        CHECK (status IN ('active', 'inactive', 'maintenance')),
    api_key         TEXT NOT NULL UNIQUE DEFAULT gen_random_uuid()::TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_hotspots_code ON hotspots (hotspot_code);
CREATE INDEX IF NOT EXISTS idx_hotspots_status ON hotspots (status);
CREATE INDEX IF NOT EXISTS idx_hotspots_city ON hotspots (city);


-- ------------------------------------------------------------
-- TABLE 3: devices
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS devices (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mac_address     TEXT NOT NULL UNIQUE,
    device_name     TEXT,
    last_seen       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_devices_mac ON devices (mac_address);


-- ------------------------------------------------------------
-- TABLE 4: sessions
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    voucher_code    TEXT NOT NULL REFERENCES vouchers (voucher_code) ON DELETE CASCADE,
    hotspot_code    TEXT NOT NULL REFERENCES hotspots (hotspot_code) ON DELETE CASCADE,
    device_mac      TEXT REFERENCES devices (mac_address) ON DELETE SET NULL,
    login_time      TIMESTAMPTZ NOT NULL DEFAULT now(),
    logout_time     TIMESTAMPTZ,
    active          BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_sessions_voucher  ON sessions (voucher_code);
CREATE INDEX IF NOT EXISTS idx_sessions_hotspot  ON sessions (hotspot_code);
CREATE INDEX IF NOT EXISTS idx_sessions_active   ON sessions (active);
CREATE INDEX IF NOT EXISTS idx_sessions_mac      ON sessions (device_mac);


-- ------------------------------------------------------------
-- TABLE 5: transactions
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS transactions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    voucher_code    TEXT NOT NULL REFERENCES vouchers (voucher_code) ON DELETE CASCADE,
    amount          NUMERIC(10, 2) NOT NULL CHECK (amount > 0),
    minutes         INTEGER NOT NULL CHECK (minutes > 0),
    payment_method  TEXT NOT NULL DEFAULT 'cash'
                        CHECK (payment_method IN ('cash', 'gcash', 'maya', 'card', 'other')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_transactions_voucher ON transactions (voucher_code);
CREATE INDEX IF NOT EXISTS idx_transactions_date    ON transactions (created_at);


-- ------------------------------------------------------------
-- TABLE 6: admins
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS admins (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username        TEXT NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,
    role            TEXT NOT NULL DEFAULT 'staff'
                        CHECK (role IN ('superadmin', 'admin', 'staff')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_admins_username ON admins (username);


-- ------------------------------------------------------------
-- SAMPLE DATA (optional - delete before production)
-- ------------------------------------------------------------

INSERT INTO hotspots (hotspot_code, hotspot_name, city, latitude, longitude)
VALUES
    ('DAV001', 'Davao Main', 'Davao City', 7.1907, 125.4553),
    ('GEN001', 'GenSan Hub', 'General Santos', 6.1164, 125.1716),
    ('CDO001', 'Cagayan Branch', 'Cagayan de Oro', 8.4542, 124.6319)
ON CONFLICT DO NOTHING;

INSERT INTO vouchers (voucher_code, total_minutes, remaining_minutes, status)
VALUES
    ('ABC123',   60, 60, 'active'),
    ('DAVAO001', 45, 45, 'active'),
    ('TEST001',  30, 30, 'active')
ON CONFLICT DO NOTHING;
