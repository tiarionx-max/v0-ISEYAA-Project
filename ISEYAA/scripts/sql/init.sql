-- ============================================================
-- ISEYAA — PostgreSQL Initialization Script
-- Runs once on first container start (docker-entrypoint-initdb.d)
-- ============================================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- Schemas per service (logical isolation within shared RDS)
CREATE SCHEMA IF NOT EXISTS auth;
CREATE SCHEMA IF NOT EXISTS events;
CREATE SCHEMA IF NOT EXISTS lga;
CREATE SCHEMA IF NOT EXISTS notifications;

-- Wallet DB has its own RDS instance — schema created in wallet_init.sql

-- Users and roles
CREATE USER iseyaa_auth WITH PASSWORD 'CHANGE_ME_IN_SECRETS';
CREATE USER iseyaa_events WITH PASSWORD 'CHANGE_ME_IN_SECRETS';
CREATE USER iseyaa_lga WITH PASSWORD 'CHANGE_ME_IN_SECRETS';
CREATE USER iseyaa_notifications WITH PASSWORD 'CHANGE_ME_IN_SECRETS';

GRANT USAGE ON SCHEMA auth          TO iseyaa_auth;
GRANT USAGE ON SCHEMA events        TO iseyaa_events;
GRANT USAGE ON SCHEMA lga           TO iseyaa_lga;
GRANT USAGE ON SCHEMA notifications TO iseyaa_notifications;

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA auth          TO iseyaa_auth;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA events        TO iseyaa_events;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA lga           TO iseyaa_lga;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA notifications TO iseyaa_notifications;

-- Set default search paths
ALTER ROLE iseyaa_auth          SET search_path = auth, public;
ALTER ROLE iseyaa_events        SET search_path = events, public;
ALTER ROLE iseyaa_lga           SET search_path = lga, public;
ALTER ROLE iseyaa_notifications SET search_path = notifications, public;

-- Ogun State LGAs reference table (shared)
CREATE TABLE IF NOT EXISTS public.ogun_lgas (
    id          SERIAL PRIMARY KEY,
    code        VARCHAR(10) UNIQUE NOT NULL,
    name        VARCHAR(100) NOT NULL,
    headquarters VARCHAR(100),
    population  INTEGER,
    area_km2    NUMERIC(10,2),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO public.ogun_lgas (code, name, headquarters) VALUES
    ('ABN', 'Abeokuta North',   'Abeokuta'),
    ('ABS', 'Abeokuta South',   'Abeokuta'),
    ('ADO', 'Ado-Odo/Ota',      'Ota'),
    ('EWE', 'Ewekoro',          'Ewekoro'),
    ('IFO', 'Ifo',              'Ifo'),
    ('IJE', 'Ijebu East',       'Ijebu-Igbo'),
    ('IJN', 'Ijebu North',      'Ijebu-Igbo'),
    ('IJNE','Ijebu North East', 'Ago-Iwoye'),
    ('IJO', 'Ijebu Ode',        'Ijebu Ode'),
    ('IKE', 'Ikenne',           'Ikenne'),
    ('IME', 'Imeko-Afon',       'Imeko'),
    ('IPO', 'Ipokia',           'Ipokia'),
    ('OBF', 'Obafemi-Owode',    'Owode'),
    ('ODE', 'Odeda',            'Odeda'),
    ('ODO', 'Odogbolu',         'Odogbolu'),
    ('OGW', 'Ogun Waterside',   'Abigi'),
    ('REM', 'Remo North',       'Sagamu'),
    ('SAG', 'Sagamu',           'Sagamu'),
    ('YEW', 'Yewa North',       'Ilaro'),
    ('YES', 'Yewa South',       'Ilaro')
ON CONFLICT (code) DO NOTHING;

-- Platform configuration table
CREATE TABLE IF NOT EXISTS public.platform_config (
    key         VARCHAR(100) PRIMARY KEY,
    value       TEXT NOT NULL,
    description TEXT,
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO public.platform_config (key, value, description) VALUES
    ('igr_split_events_pct',      '5.00',  'IGR % remitted to Ogun State from event tickets'),
    ('igr_split_marketplace_pct', '2.50',  'IGR % from marketplace transactions'),
    ('igr_split_transport_pct',   '3.00',  'IGR % from ride-hailing fares'),
    ('platform_fee_pct',          '2.50',  'Platform service fee %'),
    ('escrow_auto_release_days',  '7',     'Days before escrow auto-releases to vendor'),
    ('kyc_tier1_daily_limit',     '50000', 'Daily transaction limit for KYC Tier 1 (₦)'),
    ('kyc_tier2_daily_limit',     '200000','Daily transaction limit for KYC Tier 2 (₦)'),
    ('kyc_tier3_daily_limit',     '500000','Daily transaction limit for KYC Tier 3 (₦)')
ON CONFLICT (key) DO NOTHING;

\echo 'ISEYAA PostgreSQL initialization complete.'
