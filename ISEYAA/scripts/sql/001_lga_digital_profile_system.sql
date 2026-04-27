-- ============================================================================
-- ISEYAA — LGA Digital Profile System
-- Master PostgreSQL Schema  |  v1.0  |  CONFIDENTIAL
-- ============================================================================
-- Covers:
--   Schema 1: lga        — Local Government profiles, assets, attractions
--   Schema 2: identity   — Users, roles, KYC, biometric hashes (NDPA-compliant)
--   Schema 3: wallet     — Multi-currency wallets, escrow, IGR revenue split
--   Schema 4: ai_audit   — Cross-schema AI-agent decision logs
--
-- Design rules:
--   • All PKs are UUID v4
--   • Every table has ai_agent_logs JSONB for MAS audit trail
--   • All PII fields encrypted at application layer (AES-256-GCM via AWS KMS)
--   • Monetary values: NUMERIC(15,2) in NGN; USD in separate column
--   • Timestamps: TIMESTAMPTZ (Africa/Lagos display; UTC stored)
--   • Soft deletes: deleted_at TIMESTAMPTZ NULL (never hard-delete)
-- ============================================================================

-- ── Extensions ────────────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "btree_gin";         -- GIN index on JSONB
CREATE EXTENSION IF NOT EXISTS "pg_trgm";           -- Trigram search on names
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- ── Schemas ───────────────────────────────────────────────────────────────────
CREATE SCHEMA IF NOT EXISTS lga;
CREATE SCHEMA IF NOT EXISTS identity;
CREATE SCHEMA IF NOT EXISTS wallet;
CREATE SCHEMA IF NOT EXISTS ai_audit;

-- ============================================================================
-- SCHEMA: lga — Local Government Area Profiles
-- ============================================================================

-- ── lga.local_governments ────────────────────────────────────────────────────
-- Master record for all 20 Ogun State LGAs.
-- The canonical reference for every piece of LGA-scoped data on the platform.

CREATE TABLE lga.local_governments (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code                    VARCHAR(10)  NOT NULL UNIQUE,   -- e.g. 'ABN', 'SAG'
    name                    VARCHAR(150) NOT NULL,
    slug                    VARCHAR(180) NOT NULL UNIQUE,   -- url-safe identifier
    headquarters            VARCHAR(150) NOT NULL,
    state                   VARCHAR(50)  NOT NULL DEFAULT 'Ogun',
    country                 VARCHAR(50)  NOT NULL DEFAULT 'Nigeria',
    geopolitical_zone       VARCHAR(50)  NOT NULL DEFAULT 'South West',

    -- Geography
    latitude                NUMERIC(10,8),
    longitude               NUMERIC(11,8),
    area_km2                NUMERIC(10,2),
    boundary_geojson        JSONB,                          -- GeoJSON polygon for map rendering

    -- Demographics
    population_estimate     INTEGER,
    population_year         SMALLINT,
    household_count         INTEGER,
    major_ethnic_groups     TEXT[],
    major_languages         TEXT[]       DEFAULT ARRAY['Yoruba','English'],

    -- Administrative
    local_government_chairman   VARCHAR(255),
    chairman_since              DATE,
    council_members_count       INTEGER,
    wards_count                 INTEGER,
    polling_units_count         INTEGER,
    creation_date               DATE,          -- Date LGA was created
    lga_secretariat_address     TEXT,
    lga_website_url             VARCHAR(500),
    emergency_phone             VARCHAR(20),

    -- Socioeconomic
    gdp_estimate_ngn            NUMERIC(20,2),
    gdp_year                    SMALLINT,
    primary_economic_sector     VARCHAR(100),  -- agriculture | commerce | manufacturing
    poverty_index               NUMERIC(5,2),  -- 0–100
    literacy_rate_pct           NUMERIC(5,2),
    unemployment_rate_pct       NUMERIC(5,2),
    registered_businesses       INTEGER,
    formal_employment_count     INTEGER,

    -- Infrastructure
    electricity_access_pct      NUMERIC(5,2),
    potable_water_access_pct    NUMERIC(5,2),
    road_network_km             NUMERIC(10,2),
    internet_penetration_pct    NUMERIC(5,2),
    hospitals_count             INTEGER,
    primary_schools_count       INTEGER,
    secondary_schools_count     INTEGER,
    tertiary_institutions_count INTEGER,

    -- Platform metrics (updated by analytics pipeline)
    platform_registered_citizens    INTEGER   DEFAULT 0,
    platform_registered_vendors     INTEGER   DEFAULT 0,
    platform_monthly_igr_ngn        NUMERIC(15,2) DEFAULT 0,
    platform_last_synced_at         TIMESTAMPTZ,

    -- Media
    banner_image_url            VARCHAR(500),
    coat_of_arms_url            VARCHAR(500),
    gallery_urls                TEXT[],

    -- Status
    is_active                   BOOLEAN     NOT NULL DEFAULT TRUE,
    profile_completeness_pct    NUMERIC(5,2) DEFAULT 0,    -- 0–100, updated by AI

    -- AI Agent audit log
    ai_agent_logs               JSONB        NOT NULL DEFAULT '[]'::JSONB,

    -- Metadata
    created_at                  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ,
    deleted_at                  TIMESTAMPTZ
);

-- Seed: All 20 Ogun State LGAs
INSERT INTO lga.local_governments
    (id, code, name, slug, headquarters, latitude, longitude, area_km2,
     population_estimate, population_year, major_ethnic_groups,
     wards_count, primary_economic_sector)
VALUES
    (uuid_generate_v4(),'ABN','Abeokuta North',  'abeokuta-north',  'Abeokuta',     7.1557, 3.3451,  68.0,  238598,2022,ARRAY['Egba'],'10','commerce'),
    (uuid_generate_v4(),'ABS','Abeokuta South',  'abeokuta-south',  'Abeokuta',     7.1469, 3.3578,  107.7, 268178,2022,ARRAY['Egba'],'10','commerce'),
    (uuid_generate_v4(),'ADO','Ado-Odo/Ota',     'ado-odo-ota',     'Ota',          6.6871, 3.1351,  875.0, 736662,2022,ARRAY['Awori','Yoruba'],'10','manufacturing'),
    (uuid_generate_v4(),'EWE','Ewekoro',          'ewekoro',         'Ewekoro',      6.9186, 3.0983,  248.0, 117233,2022,ARRAY['Remo','Egba'],'10','agriculture'),
    (uuid_generate_v4(),'IFO','Ifo',              'ifo',             'Ifo',          6.8142, 3.1987,  742.0, 516462,2022,ARRAY['Awori','Yoruba'],'10','agriculture'),
    (uuid_generate_v4(),'IJE','Ijebu East',       'ijebu-east',      'Ijebu-Igbo',   6.9897, 4.0167,  706.0, 143530,2022,ARRAY['Ijebu'],'10','agriculture'),
    (uuid_generate_v4(),'IJN','Ijebu North',      'ijebu-north',     'Ijebu-Igbo',   7.0228, 3.9878,  968.0, 207290,2022,ARRAY['Ijebu'],'10','commerce'),
    (uuid_generate_v4(),'IJNE','Ijebu North East','ijebu-north-east','Ago-Iwoye',    6.9628, 3.9706,  394.0, 116461,2022,ARRAY['Ijebu'],'10','agriculture'),
    (uuid_generate_v4(),'IJO','Ijebu Ode',        'ijebu-ode',       'Ijebu Ode',    6.8186, 3.9206,  648.0, 216128,2022,ARRAY['Ijebu'],'10','commerce'),
    (uuid_generate_v4(),'IKE','Ikenne',            'ikenne',          'Ikenne',       6.8899, 3.7101,  247.0, 213140,2022,ARRAY['Remo'],'10','agriculture'),
    (uuid_generate_v4(),'IME','Imeko-Afon',        'imeko-afon',      'Imeko',        7.2069, 2.9872,  1106.0, 81408,2022,ARRAY['Yewa'],'10','agriculture'),
    (uuid_generate_v4(),'IPO','Ipokia',            'ipokia',          'Ipokia',       6.6284, 2.8972,  733.0, 121960,2022,ARRAY['Awori','Anago'],'10','agriculture'),
    (uuid_generate_v4(),'OBF','Obafemi-Owode',     'obafemi-owode',   'Owode',        7.1228, 3.4867,  676.0, 313196,2022,ARRAY['Egba','Owode'],'10','agriculture'),
    (uuid_generate_v4(),'ODE','Odeda',             'odeda',           'Odeda',        7.1869, 3.2456,  912.0, 106672,2022,ARRAY['Egba'],'10','agriculture'),
    (uuid_generate_v4(),'ODO','Odogbolu',          'odogbolu',        'Odogbolu',     6.7706, 3.7922,  688.0, 104249,2022,ARRAY['Ijebu'],'10','agriculture'),
    (uuid_generate_v4(),'OGW','Ogun Waterside',    'ogun-waterside',  'Abigi',        6.5878, 3.7967,  1,143.0,77066,2022,ARRAY['Ijebu','Awori'],'10','fishing'),
    (uuid_generate_v4(),'REM','Remo North',        'remo-north',      'Sagamu',       6.8967, 3.6678,  333.0, 132286,2022,ARRAY['Remo'],'10','commerce'),
    (uuid_generate_v4(),'SAG','Sagamu',            'sagamu',          'Sagamu',       6.8389, 3.6478,  287.0, 376140,2022,ARRAY['Remo'],'10','commerce'),
    (uuid_generate_v4(),'YEW','Yewa North',        'yewa-north',      'Ilaro',        7.0678, 2.9467,  1462.0,196986,2022,ARRAY['Yewa','Ketu'],'10','agriculture'),
    (uuid_generate_v4(),'YES','Yewa South',        'yewa-south',      'Ilaro',        6.8869, 3.0167,  684.0, 192744,2022,ARRAY['Yewa'],'10','agriculture')
ON CONFLICT (code) DO NOTHING;

CREATE INDEX idx_lga_name_trgm ON lga.local_governments USING GIN (name gin_trgm_ops);
CREATE INDEX idx_lga_ai_logs   ON lga.local_governments USING GIN (ai_agent_logs);
CREATE INDEX idx_lga_active    ON lga.local_governments (is_active) WHERE is_active = TRUE;


-- ── lga.cultural_assets ───────────────────────────────────────────────────────
-- Heritage sites, festivals, artefacts, and intangible cultural properties.

CREATE TABLE lga.cultural_assets (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lga_id              UUID NOT NULL REFERENCES lga.local_governments(id) ON DELETE RESTRICT,
    name                VARCHAR(255) NOT NULL,
    slug                VARCHAR(300) NOT NULL UNIQUE,
    asset_type          VARCHAR(50)  NOT NULL,
    -- monument | festival | artefact | language | craft | cuisine |
    -- music_genre | dance_form | oral_tradition | religious_site

    description         TEXT,
    historical_period   VARCHAR(100),           -- e.g. 'Pre-colonial', '18th century'
    origin_year         INTEGER,
    significance        TEXT,                   -- Cultural/historical significance narrative

    -- Location
    physical_address    TEXT,
    latitude            NUMERIC(10,8),
    longitude           NUMERIC(11,8),
    google_maps_url     VARCHAR(500),

    -- Status & preservation
    unesco_listed       BOOLEAN DEFAULT FALSE,
    national_monument   BOOLEAN DEFAULT FALSE,
    preservation_status VARCHAR(50) DEFAULT 'good',
    -- excellent | good | fair | at_risk | critical | lost

    -- Digital
    virtual_tour_url    VARCHAR(500),
    ar_asset_url        VARCHAR(500),           -- Unity AR asset (Phase 3)
    media_urls          TEXT[],
    tags                TEXT[],

    -- Visitor info
    admission_fee_ngn   NUMERIC(10,2),
    visiting_hours      JSONB,                  -- {mon: "09:00-17:00", ...}
    annual_visitors     INTEGER,

    -- AI enrichment
    ai_generated_summary    TEXT,               -- Claude-generated public summary
    ai_agent_logs           JSONB NOT NULL DEFAULT '[]'::JSONB,

    is_active           BOOLEAN DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ,
    deleted_at          TIMESTAMPTZ
);

CREATE INDEX idx_cultural_lga      ON lga.cultural_assets (lga_id);
CREATE INDEX idx_cultural_type     ON lga.cultural_assets (asset_type);
CREATE INDEX idx_cultural_ai_logs  ON lga.cultural_assets USING GIN (ai_agent_logs);
CREATE INDEX idx_cultural_tags     ON lga.cultural_assets USING GIN (tags);
CREATE INDEX idx_cultural_name_trgm ON lga.cultural_assets USING GIN (name gin_trgm_ops);


-- ── lga.tourism_attractions ──────────────────────────────────────────────────
-- Bookable and visitable tourism assets with live availability.

CREATE TABLE lga.tourism_attractions (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lga_id              UUID NOT NULL REFERENCES lga.local_governments(id) ON DELETE RESTRICT,
    name                VARCHAR(255) NOT NULL,
    slug                VARCHAR(300) NOT NULL UNIQUE,
    category            VARCHAR(50)  NOT NULL,
    -- nature | heritage | adventure | beach | waterfall | park |
    -- museum | palace | religious | culinary | agritourism | sports

    description         TEXT,
    highlights          TEXT[],                 -- Bullet-point attractions
    best_season         VARCHAR(100),
    duration_hours      NUMERIC(4,1),           -- Average visit duration

    -- Location
    address             TEXT,
    lga_ward            VARCHAR(100),
    latitude            NUMERIC(10,8),
    longitude           NUMERIC(11,8),
    distance_from_abeokuta_km   NUMERIC(8,2),

    -- Pricing
    admission_free      BOOLEAN DEFAULT FALSE,
    adult_price_ngn     NUMERIC(10,2) DEFAULT 0,
    child_price_ngn     NUMERIC(10,2) DEFAULT 0,
    group_price_ngn     NUMERIC(10,2),          -- Per group (≥10 people)
    foreign_price_usd   NUMERIC(10,2),

    -- Capacity & booking
    daily_capacity      INTEGER,
    requires_booking    BOOLEAN DEFAULT FALSE,
    advance_days        INTEGER DEFAULT 0,      -- Days advance booking required
    is_bookable         BOOLEAN DEFAULT FALSE,  -- Listed on ISEYAA booking engine

    -- Facilities
    parking_available   BOOLEAN DEFAULT FALSE,
    accessibility       BOOLEAN DEFAULT FALSE,  -- Wheelchair/disability access
    guided_tours        BOOLEAN DEFAULT FALSE,
    facilities          TEXT[],                 -- ['restaurant','restrooms','wifi',...]

    -- Ratings
    average_rating      NUMERIC(3,2),
    total_reviews       INTEGER DEFAULT 0,

    -- Media
    cover_image_url     VARCHAR(500),
    gallery_urls        TEXT[],
    virtual_tour_url    VARCHAR(500),
    video_url           VARCHAR(500),

    -- Operational
    opening_hours       JSONB,                  -- {mon: "09:00-18:00", ...}
    contact_phone       VARCHAR(20),
    contact_email       VARCHAR(255),
    website_url         VARCHAR(500),
    tripadvisor_url     VARCHAR(500),

    -- Government
    managed_by_govt     BOOLEAN DEFAULT FALSE,
    ministry_id         UUID,                   -- Ref to ministry table (future)

    -- AI
    ai_itinerary_eligible   BOOLEAN DEFAULT TRUE,   -- Can AI include in itineraries?
    ai_agent_logs           JSONB NOT NULL DEFAULT '[]'::JSONB,

    is_active           BOOLEAN DEFAULT TRUE,
    verified_at         TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ,
    deleted_at          TIMESTAMPTZ
);

CREATE INDEX idx_tourism_lga      ON lga.tourism_attractions (lga_id);
CREATE INDEX idx_tourism_category ON lga.tourism_attractions (category);
CREATE INDEX idx_tourism_bookable ON lga.tourism_attractions (is_bookable) WHERE is_bookable = TRUE;
CREATE INDEX idx_tourism_ai_logs  ON lga.tourism_attractions USING GIN (ai_agent_logs);
CREATE INDEX idx_tourism_name_trgm ON lga.tourism_attractions USING GIN (name gin_trgm_ops);


-- ── lga.economic_activities ──────────────────────────────────────────────────
-- Sector-level economic data per LGA. Powers IGR projections and ministry reports.

CREATE TABLE lga.economic_activities (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lga_id              UUID NOT NULL REFERENCES lga.local_governments(id) ON DELETE RESTRICT,
    sector              VARCHAR(100) NOT NULL,
    -- agriculture | manufacturing | commerce | services | mining |
    -- fishing | construction | transport | ict | tourism | finance

    subsector           VARCHAR(100),           -- e.g. 'cocoa_farming', 'textile'
    reporting_year      SMALLINT NOT NULL,
    reporting_quarter   SMALLINT,               -- 1–4 (NULL = full year)

    -- Metrics
    estimated_gdp_ngn       NUMERIC(20,2),
    employed_persons        INTEGER,
    registered_businesses   INTEGER,
    fdi_inflow_usd          NUMERIC(20,2),      -- Foreign direct investment
    tax_revenue_ngn         NUMERIC(15,2),
    igr_contribution_ngn    NUMERIC(15,2),      -- Share to Ogun State IGR

    -- Platform activity (live stats from wallet/events/marketplace)
    platform_transactions   INTEGER  DEFAULT 0,
    platform_volume_ngn     NUMERIC(15,2) DEFAULT 0,

    -- Details
    major_employers         TEXT[],
    key_products            TEXT[],
    infrastructure_gaps     TEXT[],
    growth_rate_pct         NUMERIC(6,2),
    data_source             VARCHAR(255),
    notes                   TEXT,

    -- AI enrichment
    ai_sector_analysis      JSONB,              -- Claude-generated sector analysis
    ai_agent_logs           JSONB NOT NULL DEFAULT '[]'::JSONB,

    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ,

    UNIQUE (lga_id, sector, reporting_year, reporting_quarter)
);

CREATE INDEX idx_economic_lga    ON lga.economic_activities (lga_id);
CREATE INDEX idx_economic_sector ON lga.economic_activities (sector);
CREATE INDEX idx_economic_year   ON lga.economic_activities (reporting_year, reporting_quarter);
CREATE INDEX idx_economic_ai_logs ON lga.economic_activities USING GIN (ai_agent_logs);


-- ── lga.lga_news_feed ─────────────────────────────────────────────────────────
-- AI-aggregated news per LGA. Fed by the MediaIntelligenceAgent.

CREATE TABLE lga.lga_news_feed (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lga_id              UUID NOT NULL REFERENCES lga.local_governments(id),
    headline            VARCHAR(500) NOT NULL,
    ai_summary          TEXT,
    source_url          VARCHAR(1000),
    source_name         VARCHAR(255),
    published_at        TIMESTAMPTZ,
    sentiment           VARCHAR(20),            -- positive | neutral | negative
    category            VARCHAR(50),            -- governance | security | economy | health | sports
    tags                TEXT[],
    ai_agent_logs       JSONB NOT NULL DEFAULT '[]'::JSONB,
    is_published        BOOLEAN DEFAULT FALSE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_news_lga         ON lga.lga_news_feed (lga_id, published_at DESC);
CREATE INDEX idx_news_sentiment   ON lga.lga_news_feed (sentiment);
CREATE INDEX idx_news_category    ON lga.lga_news_feed (category);


-- ============================================================================
-- SCHEMA: identity — Users, Roles, KYC, Biometric
-- ============================================================================

-- ── identity.users ────────────────────────────────────────────────────────────
-- Core identity record. PII fields stored ENCRYPTED at application layer.
-- Plaintext equivalents documented in comments — never stored in DB.

CREATE TABLE identity.users (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Authentication (non-PII)
    email_hash              VARCHAR(64)  UNIQUE,     -- SHA-256 of lowercase email
    phone_hash              VARCHAR(64)  UNIQUE,     -- SHA-256 of E.164 phone
    username                VARCHAR(100) UNIQUE,

    -- Encrypted PII (AES-256-GCM via AWS KMS — decrypted in app layer only)
    -- Field naming convention: <field>_enc = encrypted ciphertext (base64)
    full_name_enc           TEXT,                    -- plaintext: "Adewale Okonkwo"
    email_enc               TEXT,                    -- plaintext: "user@example.com"
    phone_enc               TEXT,                    -- plaintext: "+2348012345678"
    date_of_birth_enc       TEXT,                    -- plaintext: "1990-04-15"
    address_enc             TEXT,                    -- plaintext: JSON address object
    gender_enc              TEXT,                    -- plaintext: "M" | "F" | "O"

    -- Biometric hashes (NDPA §2.1 — stored as irreversible hashes, never raw data)
    -- Raw biometrics NEVER stored. Only salted SHA-3-512 hashes for match verification.
    face_id_hash            VARCHAR(128),            -- SHA-3-512(face_embedding_vector)
    fingerprint_hash_r_index VARCHAR(128),           -- SHA-3-512(fingerprint_minutiae)
    fingerprint_hash_l_thumb VARCHAR(128),
    biometric_enrolled_at   TIMESTAMPTZ,
    biometric_device_id     VARCHAR(100),            -- Device that enrolled biometric
    biometric_version       SMALLINT DEFAULT 1,

    -- NIN / BVN (critical PII — encrypted + hashed)
    nin_hash                VARCHAR(64)  UNIQUE,     -- SHA-256 of NIN (for dedup)
    nin_enc                 TEXT,                    -- Encrypted NIN
    nin_verified            BOOLEAN     DEFAULT FALSE,
    nin_verified_at         TIMESTAMPTZ,
    bvn_hash                VARCHAR(64)  UNIQUE,
    bvn_enc                 TEXT,
    bvn_verified            BOOLEAN     DEFAULT FALSE,
    bvn_verified_at         TIMESTAMPTZ,

    -- Role & status
    primary_role            VARCHAR(50)  NOT NULL DEFAULT 'citizen',
    -- citizen | tourist | vendor | athlete | event_organiser |
    -- hotel_operator | transport_operator | healthcare_provider |
    -- government_officer | ministry_admin | super_admin

    account_status          VARCHAR(30)  NOT NULL DEFAULT 'pending_verification',
    -- pending_verification | active | suspended | frozen | banned | closed

    -- LGA affiliation
    home_lga_id             UUID REFERENCES lga.local_governments(id),
    current_lga_id          UUID REFERENCES lga.local_governments(id),

    -- KYC
    kyc_tier                SMALLINT     NOT NULL DEFAULT 0,
    -- 0=unverified | 1=basic(email+phone) | 2=standard(NIN) | 3=premium(BVN+biometric)
    kyc_completed_at        TIMESTAMPTZ,
    kyc_provider            VARCHAR(50),            -- nimc | youverify | smile_id

    -- Membership
    membership_tier         VARCHAR(30)  NOT NULL DEFAULT 'free',
    -- free | standard | premium | government
    membership_expires_at   TIMESTAMPTZ,

    -- 2FA (required for financial + government roles — PRD §4.1)
    two_fa_enabled          BOOLEAN      DEFAULT FALSE,
    two_fa_method           VARCHAR(20),            -- totp | sms | whatsapp
    two_fa_secret_enc       TEXT,                   -- Encrypted TOTP secret

    -- OAuth
    google_sub              VARCHAR(255) UNIQUE,
    apple_sub               VARCHAR(255) UNIQUE,

    -- Session tracking
    last_login_at           TIMESTAMPTZ,
    last_login_ip_hash      VARCHAR(64),
    failed_login_attempts   SMALLINT     DEFAULT 0,
    locked_until            TIMESTAMPTZ,

    -- Language preference
    preferred_language      VARCHAR(10)  DEFAULT 'en',
    -- en | yo (Yoruba) | ha (Hausa)

    -- Privacy & consent (NDPA compliance)
    data_processing_consent BOOLEAN      NOT NULL DEFAULT FALSE,
    consent_given_at        TIMESTAMPTZ,
    consent_version         VARCHAR(20),            -- Privacy policy version
    marketing_consent       BOOLEAN      DEFAULT FALSE,
    data_retention_end      TIMESTAMPTZ,            -- User-requested data deletion date

    -- Profile
    avatar_url              VARCHAR(500),
    cover_image_url         VARCHAR(500),
    bio                     TEXT,

    -- Digital ID
    digital_id_number       VARCHAR(30)  UNIQUE,    -- ISEYAA-OG-XXXXXXXX
    digital_id_issued_at    TIMESTAMPTZ,
    digital_id_qr_url       VARCHAR(500),

    -- AI Agent audit log
    ai_agent_logs           JSONB        NOT NULL DEFAULT '[]'::JSONB,

    -- Soft delete
    created_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ,
    deleted_at              TIMESTAMPTZ
);

-- Indexes
CREATE INDEX idx_users_role          ON identity.users (primary_role);
CREATE INDEX idx_users_status        ON identity.users (account_status);
CREATE INDEX idx_users_home_lga      ON identity.users (home_lga_id);
CREATE INDEX idx_users_kyc_tier      ON identity.users (kyc_tier);
CREATE INDEX idx_users_membership    ON identity.users (membership_tier);
CREATE INDEX idx_users_digital_id    ON identity.users (digital_id_number);
CREATE INDEX idx_users_ai_logs       ON identity.users USING GIN (ai_agent_logs);
CREATE INDEX idx_users_active        ON identity.users (account_status)
    WHERE account_status = 'active' AND deleted_at IS NULL;


-- ── identity.user_roles ────────────────────────────────────────────────────────
-- Users can hold multiple roles (e.g., citizen + vendor + event_organiser).
-- Role-level permissions and verification status tracked independently.

CREATE TABLE identity.user_roles (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES identity.users(id) ON DELETE CASCADE,
    role            VARCHAR(50)  NOT NULL,
    status          VARCHAR(30)  NOT NULL DEFAULT 'pending',
    -- pending | active | suspended | revoked
    granted_by      UUID REFERENCES identity.users(id),    -- Admin who granted
    granted_at      TIMESTAMPTZ  DEFAULT NOW(),
    expires_at      TIMESTAMPTZ,
    revoked_at      TIMESTAMPTZ,
    revocation_reason TEXT,
    role_metadata   JSONB,                  -- Role-specific data
    ai_agent_logs   JSONB NOT NULL DEFAULT '[]'::JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (user_id, role)
);

CREATE INDEX idx_user_roles_user   ON identity.user_roles (user_id);
CREATE INDEX idx_user_roles_role   ON identity.user_roles (role);
CREATE INDEX idx_user_roles_status ON identity.user_roles (status);


-- ── identity.kyc_verifications ────────────────────────────────────────────────
-- Audit log of every KYC verification attempt.

CREATE TABLE identity.kyc_verifications (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID NOT NULL REFERENCES identity.users(id) ON DELETE CASCADE,
    verification_type   VARCHAR(50) NOT NULL,
    -- nin | bvn | face_match | liveness | document | address

    status              VARCHAR(30) NOT NULL DEFAULT 'initiated',
    -- initiated | pending | passed | failed | expired | manual_review

    provider            VARCHAR(50),    -- nimc | youverify | smile_id | manual
    provider_reference  VARCHAR(255),   -- External verification ID
    provider_response   JSONB,          -- Full provider response (sensitive fields redacted)

    confidence_score    NUMERIC(5,4),   -- 0.0000–1.0000 (biometric match score)
    failure_reason      VARCHAR(255),
    reviewer_id         UUID REFERENCES identity.users(id),
    reviewed_at         TIMESTAMPTZ,
    reviewer_notes      TEXT,

    request_ip_hash     VARCHAR(64),
    device_fingerprint  VARCHAR(255),
    session_id          VARCHAR(100),

    ai_agent_logs       JSONB NOT NULL DEFAULT '[]'::JSONB,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at          TIMESTAMPTZ
);

CREATE INDEX idx_kyc_user     ON identity.kyc_verifications (user_id);
CREATE INDEX idx_kyc_type     ON identity.kyc_verifications (verification_type);
CREATE INDEX idx_kyc_status   ON identity.kyc_verifications (status);


-- ── identity.biometric_sessions ───────────────────────────────────────────────
-- Log of every biometric authentication event (FaceID, fingerprint).
-- Raw biometric data NEVER stored. Only outcome + device info.

CREATE TABLE identity.biometric_sessions (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID NOT NULL REFERENCES identity.users(id) ON DELETE CASCADE,
    session_type        VARCHAR(30) NOT NULL,
    -- face_id | fingerprint | iris | voice

    action              VARCHAR(30) NOT NULL,
    -- enroll | authenticate | re_enroll | revoke

    outcome             VARCHAR(20) NOT NULL,
    -- success | failed | spoof_detected | timeout | cancelled

    match_score         NUMERIC(5,4),           -- Similarity score (0.0000–1.0000)
    liveness_score      NUMERIC(5,4),           -- Anti-spoofing confidence
    spoof_detected      BOOLEAN DEFAULT FALSE,

    device_id           VARCHAR(100),
    device_os           VARCHAR(50),
    device_model        VARCHAR(100),
    app_version         VARCHAR(20),
    ip_hash             VARCHAR(64),

    ai_agent_logs       JSONB NOT NULL DEFAULT '[]'::JSONB,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_biometric_user    ON identity.biometric_sessions (user_id, created_at DESC);
CREATE INDEX idx_biometric_outcome ON identity.biometric_sessions (outcome);
CREATE INDEX idx_biometric_spoof   ON identity.biometric_sessions (spoof_detected)
    WHERE spoof_detected = TRUE;


-- ── identity.vendor_profiles ──────────────────────────────────────────────────
-- Extended profile for Vendor role users.

CREATE TABLE identity.vendor_profiles (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                 UUID NOT NULL UNIQUE REFERENCES identity.users(id) ON DELETE CASCADE,
    lga_id                  UUID REFERENCES lga.local_governments(id),

    business_name           VARCHAR(255) NOT NULL,
    business_slug           VARCHAR(300) NOT NULL UNIQUE,
    business_category       VARCHAR(100),
    -- food | fashion | electronics | artisan | agriculture | logistics | services

    business_description    TEXT,
    cac_registration_no     VARCHAR(50),        -- Corporate Affairs Commission
    cac_verified            BOOLEAN DEFAULT FALSE,
    tax_id                  VARCHAR(50),        -- OGIRS tax identification
    tax_verified            BOOLEAN DEFAULT FALSE,

    bank_account_name       VARCHAR(255),
    bank_account_no_enc     TEXT,               -- Encrypted account number
    bank_code               VARCHAR(10),
    paystack_recipient_code VARCHAR(100),       -- For automated payouts

    is_premium              BOOLEAN DEFAULT FALSE,
    is_featured             BOOLEAN DEFAULT FALSE,
    storefront_url          VARCHAR(500),
    average_rating          NUMERIC(3,2),
    total_orders            INTEGER DEFAULT 0,
    total_revenue_ngn       NUMERIC(15,2) DEFAULT 0,

    ai_agent_logs           JSONB NOT NULL DEFAULT '[]'::JSONB,
    onboarded_at            TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ,
    deleted_at              TIMESTAMPTZ
);

CREATE INDEX idx_vendor_lga      ON identity.vendor_profiles (lga_id);
CREATE INDEX idx_vendor_category ON identity.vendor_profiles (business_category);
CREATE INDEX idx_vendor_name_trgm ON identity.vendor_profiles USING GIN (business_name gin_trgm_ops);


-- ── identity.tourist_profiles ─────────────────────────────────────────────────
-- Extended profile for Tourist role users.

CREATE TABLE identity.tourist_profiles (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                 UUID NOT NULL UNIQUE REFERENCES identity.users(id) ON DELETE CASCADE,

    nationality             VARCHAR(100),
    passport_no_enc         TEXT,               -- Encrypted passport number
    passport_expiry_enc     TEXT,
    visa_type               VARCHAR(50),
    visa_expiry             DATE,

    tourism_interests       TEXT[],
    -- nature | culture | adventure | food | sports | business | medical

    arrival_date            DATE,
    departure_date          DATE,
    accommodation_type      VARCHAR(50),        -- hotel | airbnb | hostel | camping

    emergency_contact_name_enc  TEXT,
    emergency_contact_phone_enc TEXT,
    travel_insurance_provider   VARCHAR(100),
    travel_insurance_policy_enc TEXT,

    total_visits            INTEGER DEFAULT 1,
    total_spent_ngn         NUMERIC(15,2) DEFAULT 0,
    total_spent_usd         NUMERIC(15,2) DEFAULT 0,
    favourite_lgas          UUID[],

    ai_agent_logs           JSONB NOT NULL DEFAULT '[]'::JSONB,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ
);


-- ============================================================================
-- SCHEMA: wallet — Multi-Currency Wallets, Escrow, Revenue Split
-- ============================================================================

-- ── wallet.wallets ────────────────────────────────────────────────────────────

CREATE TABLE wallet.wallets (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                 UUID NOT NULL REFERENCES identity.users(id) ON DELETE RESTRICT,
    wallet_type             VARCHAR(30) NOT NULL DEFAULT 'personal',
    -- personal | vendor | government | escrow_pool | igr_pool

    currency                VARCHAR(5)  NOT NULL DEFAULT 'NGN',
    status                  VARCHAR(30) NOT NULL DEFAULT 'active',
    -- active | suspended | frozen | closed

    -- Balances — NUMERIC(15,2): max ₦999,999,999,999,999.99
    available_balance       NUMERIC(15,2) NOT NULL DEFAULT 0.00 CHECK (available_balance >= 0),
    ledger_balance          NUMERIC(15,2) NOT NULL DEFAULT 0.00,
    escrow_balance          NUMERIC(15,2) NOT NULL DEFAULT 0.00 CHECK (escrow_balance >= 0),
    pending_balance         NUMERIC(15,2) NOT NULL DEFAULT 0.00,    -- Unconfirmed credits
    reserved_balance        NUMERIC(15,2) NOT NULL DEFAULT 0.00,    -- Pre-authorised

    -- CBN-compliant daily/transaction limits (tier-based)
    daily_debit_limit       NUMERIC(15,2) NOT NULL DEFAULT 50000.00,
    single_txn_limit        NUMERIC(15,2) NOT NULL DEFAULT 20000.00,
    daily_used              NUMERIC(15,2) NOT NULL DEFAULT 0.00,
    daily_reset_at          TIMESTAMPTZ   NOT NULL DEFAULT (NOW() + INTERVAL '1 day'),

    -- KYC tier mirrored here for fast access
    kyc_tier                SMALLINT      NOT NULL DEFAULT 0,
    bvn_linked              BOOLEAN       DEFAULT FALSE,
    nin_verified            BOOLEAN       DEFAULT FALSE,

    -- LGA context (for IGR attribution)
    lga_id                  UUID REFERENCES lga.local_governments(id),

    -- Funding sources
    linked_bank_code        VARCHAR(10),
    linked_bank_name        VARCHAR(100),
    linked_account_last4    VARCHAR(4),         -- Last 4 digits only (PCI-DSS)
    paystack_customer_code  VARCHAR(100),

    -- Optimistic locking (prevents concurrent balance race conditions)
    version                 INTEGER       NOT NULL DEFAULT 1,

    -- AI Agent audit log
    ai_agent_logs           JSONB         NOT NULL DEFAULT '[]'::JSONB,

    created_at              TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ,
    closed_at               TIMESTAMPTZ,
    deleted_at              TIMESTAMPTZ,

    UNIQUE (user_id, currency, wallet_type)
);

CREATE INDEX idx_wallet_user        ON wallet.wallets (user_id);
CREATE INDEX idx_wallet_status      ON wallet.wallets (status) WHERE status = 'active';
CREATE INDEX idx_wallet_lga         ON wallet.wallets (lga_id);
CREATE INDEX idx_wallet_ai_logs     ON wallet.wallets USING GIN (ai_agent_logs);


-- ── wallet.transactions ───────────────────────────────────────────────────────
-- Immutable double-entry ledger. Every debit has a paired credit.

CREATE TABLE wallet.transactions (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Parties
    wallet_id               UUID NOT NULL REFERENCES wallet.wallets(id) ON DELETE RESTRICT,
    counterparty_wallet_id  UUID REFERENCES wallet.wallets(id),
    user_id                 UUID NOT NULL REFERENCES identity.users(id),
    lga_id                  UUID REFERENCES lga.local_governments(id),

    -- Classification
    transaction_type        VARCHAR(50) NOT NULL,
    -- credit | debit | escrow_hold | escrow_release | escrow_refund |
    -- igr_remittance | platform_fee | vendor_payout | refund |
    -- wallet_topup | utility_payment | tax_payment | p2p_transfer |
    -- event_ticket | marketplace_purchase | transport_fare | hmo_premium

    direction               VARCHAR(10) NOT NULL CHECK (direction IN ('credit','debit')),
    status                  VARCHAR(30) NOT NULL DEFAULT 'pending',
    -- pending | processing | completed | failed | reversed | disputed

    -- Amounts
    currency                VARCHAR(5)  NOT NULL DEFAULT 'NGN',
    gross_amount            NUMERIC(15,2) NOT NULL CHECK (gross_amount > 0),
    platform_fee_amount     NUMERIC(15,2) NOT NULL DEFAULT 0.00,
    igr_amount              NUMERIC(15,2) NOT NULL DEFAULT 0.00,
    provider_fee_amount     NUMERIC(15,2) NOT NULL DEFAULT 0.00,
    net_amount              NUMERIC(15,2) NOT NULL,              -- gross - all fees
    exchange_rate           NUMERIC(15,6),                       -- For USD transactions
    usd_equivalent          NUMERIC(15,2),

    -- Balance snapshot (immutable audit trail)
    balance_before          NUMERIC(15,2) NOT NULL,
    balance_after           NUMERIC(15,2) NOT NULL,

    -- Revenue split (PRD §4.2)
    igr_split_pct           NUMERIC(5,2)  NOT NULL DEFAULT 0.00,
    platform_fee_pct        NUMERIC(5,2)  NOT NULL DEFAULT 0.00,
    igr_remitted            BOOLEAN       DEFAULT FALSE,
    igr_remitted_at         TIMESTAMPTZ,
    ogirs_batch_id          VARCHAR(100),

    -- Payment provider
    provider                VARCHAR(30)   NOT NULL,
    -- paystack | flutterwave | mono | nibss | internal | ogirs
    provider_reference      VARCHAR(255)  UNIQUE,
    provider_metadata       JSONB,
    gateway_response        VARCHAR(100),

    -- Module context
    module                  VARCHAR(50),
    -- events | marketplace | transport | utilities | hmo | sports | wallet | tax
    module_reference_id     UUID,           -- event_id, order_id, ride_id, etc.
    module_reference_type   VARCHAR(50),    -- 'event' | 'order' | 'ride'

    -- CBN / regulatory
    narration               VARCHAR(255),
    session_id              VARCHAR(100),   -- NIBSS session ID
    channel                 VARCHAR(30),    -- card | bank_transfer | ussd | wallet | mobile_money
    tax_category            VARCHAR(50),

    -- Failure
    failure_reason          TEXT,
    retry_count             SMALLINT DEFAULT 0,
    reversed_by_txn_id      UUID REFERENCES wallet.transactions(id),

    -- AI Agent audit log
    ai_agent_logs           JSONB         NOT NULL DEFAULT '[]'::JSONB,

    created_at              TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    completed_at            TIMESTAMPTZ,
    updated_at              TIMESTAMPTZ
);

CREATE INDEX idx_txn_wallet_created  ON wallet.transactions (wallet_id, created_at DESC);
CREATE INDEX idx_txn_user            ON wallet.transactions (user_id);
CREATE INDEX idx_txn_lga             ON wallet.transactions (lga_id);
CREATE INDEX idx_txn_status          ON wallet.transactions (status);
CREATE INDEX idx_txn_type            ON wallet.transactions (transaction_type);
CREATE INDEX idx_txn_provider_ref    ON wallet.transactions (provider_reference);
CREATE INDEX idx_txn_module          ON wallet.transactions (module, module_reference_id);
CREATE INDEX idx_txn_igr_pending     ON wallet.transactions (igr_remitted)
    WHERE igr_remitted = FALSE AND igr_amount > 0 AND status = 'completed';
CREATE INDEX idx_txn_ai_logs         ON wallet.transactions USING GIN (ai_agent_logs);


-- ── wallet.escrow_accounts ────────────────────────────────────────────────────
-- Marketplace and service transaction escrow.
-- Funds held until delivery confirmed; auto-release after N days.

CREATE TABLE wallet.escrow_accounts (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    reference               VARCHAR(50)  NOT NULL UNIQUE,   -- ESCRW-XXXXXXXX

    -- Parties
    buyer_wallet_id         UUID NOT NULL REFERENCES wallet.wallets(id),
    seller_wallet_id        UUID NOT NULL REFERENCES wallet.wallets(id),
    buyer_user_id           UUID NOT NULL REFERENCES identity.users(id),
    seller_user_id          UUID NOT NULL REFERENCES identity.users(id),
    lga_id                  UUID REFERENCES lga.local_governments(id),

    -- Amount
    currency                VARCHAR(5)  NOT NULL DEFAULT 'NGN',
    gross_amount            NUMERIC(15,2) NOT NULL CHECK (gross_amount > 0),
    platform_fee_ngn        NUMERIC(15,2) NOT NULL DEFAULT 0.00,
    igr_amount_ngn          NUMERIC(15,2) NOT NULL DEFAULT 0.00,
    seller_payout_amount    NUMERIC(15,2) NOT NULL,         -- gross - fees

    -- Funding transaction
    hold_transaction_id     UUID REFERENCES wallet.transactions(id),

    -- Status
    status                  VARCHAR(30) NOT NULL DEFAULT 'holding',
    -- holding | delivery_confirmed | disputed | released | refunded | expired

    -- Module
    module                  VARCHAR(50) NOT NULL,
    module_reference_id     UUID,
    module_reference_type   VARCHAR(50),
    description             VARCHAR(500),

    -- Auto-release
    auto_release_at         TIMESTAMPTZ NOT NULL,
    auto_release_days       SMALLINT    NOT NULL DEFAULT 7,

    -- Release
    release_triggered_by    VARCHAR(30),        -- buyer_confirm | auto | admin | dispute_resolution
    release_transaction_id  UUID REFERENCES wallet.transactions(id),
    released_at             TIMESTAMPTZ,

    -- Refund
    refund_transaction_id   UUID REFERENCES wallet.transactions(id),
    refunded_at             TIMESTAMPTZ,
    refund_reason           TEXT,

    -- Dispute
    dispute_raised_at       TIMESTAMPTZ,
    dispute_raised_by       UUID REFERENCES identity.users(id),
    dispute_reason          TEXT,
    dispute_evidence_urls   TEXT[],
    dispute_resolved_at     TIMESTAMPTZ,
    dispute_resolved_by     UUID REFERENCES identity.users(id),
    dispute_resolution      VARCHAR(30),        -- release_to_seller | refund_to_buyer | partial_split
    dispute_resolution_notes TEXT,

    -- AI Agent audit log
    ai_agent_logs           JSONB       NOT NULL DEFAULT '[]'::JSONB,

    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ,

    CHECK (seller_payout_amount > 0)
);

CREATE INDEX idx_escrow_buyer        ON wallet.escrow_accounts (buyer_wallet_id);
CREATE INDEX idx_escrow_seller       ON wallet.escrow_accounts (seller_wallet_id);
CREATE INDEX idx_escrow_status       ON wallet.escrow_accounts (status);
CREATE INDEX idx_escrow_auto_release ON wallet.escrow_accounts (auto_release_at)
    WHERE status = 'holding';
CREATE INDEX idx_escrow_module       ON wallet.escrow_accounts (module, module_reference_id);
CREATE INDEX idx_escrow_ai_logs      ON wallet.escrow_accounts USING GIN (ai_agent_logs);


-- ── wallet.revenue_split_config ───────────────────────────────────────────────
-- Configurable IGR split percentages per module and LGA.
-- Managed by super_admin. Used by the revenue-split engine at transaction time.

CREATE TABLE wallet.revenue_split_config (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    module              VARCHAR(50)  NOT NULL,
    lga_id              UUID REFERENCES lga.local_governments(id),
    -- NULL = applies to all LGAs (default); specific row overrides default

    currency            VARCHAR(5)   NOT NULL DEFAULT 'NGN',

    igr_pct             NUMERIC(5,2) NOT NULL CHECK (igr_pct BETWEEN 0 AND 100),
    platform_fee_pct    NUMERIC(5,2) NOT NULL CHECK (platform_fee_pct BETWEEN 0 AND 100),
    -- seller_pct = 100 - igr_pct - platform_fee_pct (enforced in app layer)

    effective_from      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    effective_to        TIMESTAMPTZ,            -- NULL = currently active
    approved_by         UUID REFERENCES identity.users(id),
    notes               TEXT,

    ai_agent_logs       JSONB        NOT NULL DEFAULT '[]'::JSONB,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    UNIQUE (module, lga_id, currency, effective_from),
    CHECK ((igr_pct + platform_fee_pct) <= 100)
);

-- Default split configs (aligned with PRD §4.2)
INSERT INTO wallet.revenue_split_config (module, lga_id, igr_pct, platform_fee_pct, notes)
VALUES
    ('events',       NULL, 5.00, 2.50, 'Default: 5% IGR + 2.5% platform on event tickets'),
    ('marketplace',  NULL, 2.50, 2.50, 'Default: 2.5% IGR + 2.5% platform on marketplace'),
    ('transport',    NULL, 3.00, 2.00, 'Default: 3% IGR + 2% platform on rides'),
    ('utilities',    NULL, 0.00, 1.00, 'Utilities pass-through: 1% platform fee only'),
    ('hmo',          NULL, 1.50, 1.50, 'HMO premiums: 1.5% IGR + 1.5% platform'),
    ('sports',       NULL, 2.00, 2.00, 'Sports registrations: 2% IGR + 2% platform'),
    ('accommodation',NULL, 4.00, 3.00, 'Accommodation: 4% IGR + 3% platform')
ON CONFLICT DO NOTHING;

CREATE INDEX idx_split_config_module ON wallet.revenue_split_config (module);
CREATE INDEX idx_split_config_lga    ON wallet.revenue_split_config (lga_id);
CREATE INDEX idx_split_active        ON wallet.revenue_split_config (effective_from, effective_to)
    WHERE effective_to IS NULL;


-- ── wallet.igr_remittance_log ─────────────────────────────────────────────────
-- Immutable audit log for every IGR remittance to OGIRS.

CREATE TABLE wallet.igr_remittance_log (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    batch_reference         VARCHAR(100) NOT NULL UNIQUE,   -- OGIRS batch ref
    lga_id                  UUID NOT NULL REFERENCES lga.local_governments(id),
    module                  VARCHAR(50)  NOT NULL,
    period_start            TIMESTAMPTZ  NOT NULL,
    period_end              TIMESTAMPTZ  NOT NULL,
    transaction_count       INTEGER      NOT NULL,
    gross_txn_volume_ngn    NUMERIC(15,2) NOT NULL,
    igr_amount_ngn          NUMERIC(15,2) NOT NULL CHECK (igr_amount_ngn > 0),
    ogirs_acknowledged      BOOLEAN      DEFAULT FALSE,
    ogirs_acknowledged_at   TIMESTAMPTZ,
    ogirs_receipt_url       VARCHAR(500),
    remittance_transaction_id UUID REFERENCES wallet.transactions(id),
    ai_agent_logs           JSONB        NOT NULL DEFAULT '[]'::JSONB,
    created_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_igr_log_lga    ON wallet.igr_remittance_log (lga_id);
CREATE INDEX idx_igr_log_period ON wallet.igr_remittance_log (period_start, period_end);


-- ── wallet.vendor_payout_schedule ─────────────────────────────────────────────
-- Vendor settlement configuration and payout history.

CREATE TABLE wallet.vendor_payout_schedule (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vendor_id           UUID NOT NULL REFERENCES identity.users(id),
    wallet_id           UUID NOT NULL REFERENCES wallet.wallets(id),
    payout_frequency    VARCHAR(20) NOT NULL DEFAULT 'weekly',
    -- daily | weekly | fortnightly | monthly | on_demand
    next_payout_at      TIMESTAMPTZ,
    minimum_payout_ngn  NUMERIC(15,2) NOT NULL DEFAULT 1000.00,
    recipient_code      VARCHAR(100),           -- Paystack recipient code
    bank_code           VARCHAR(10),
    account_last4       VARCHAR(4),
    is_active           BOOLEAN DEFAULT TRUE,
    total_paid_ngn      NUMERIC(15,2) DEFAULT 0,
    last_payout_at      TIMESTAMPTZ,
    last_payout_amount  NUMERIC(15,2),
    ai_agent_logs       JSONB NOT NULL DEFAULT '[]'::JSONB,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ,

    UNIQUE (vendor_id)
);


-- ============================================================================
-- SCHEMA: ai_audit — Cross-Schema AI Agent Decision Logs
-- ============================================================================
-- Central store for all AI agent decisions, actions, and traces.
-- Referenced by the JSONB ai_agent_logs field in every table above.
-- Enables full explainability and government-grade audit trail.

CREATE TABLE ai_audit.agent_logs (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Agent identity
    agent_type          VARCHAR(50)  NOT NULL,
    -- orchestrator | lga_intelligence | events | fraud_detection |
    -- media_intelligence | itinerary | citizen_chat | kyc_reviewer

    task_id             UUID,                   -- Maps to OrchestratorAgent task.id
    parent_log_id       UUID REFERENCES ai_audit.agent_logs(id),

    -- Subject entity (what the agent acted on)
    entity_type         VARCHAR(50)  NOT NULL,
    -- user | lga | transaction | event | escrow | vendor | ticket
    entity_id           UUID,

    -- Action
    action              VARCHAR(100) NOT NULL,
    -- igr_report_generated | kyc_decision | fraud_score | itinerary_created |
    -- news_published | escrow_auto_released | ...

    -- Input / Output (sanitised — no raw PII)
    input_summary       TEXT,
    output_summary      TEXT,
    full_trace          JSONB,                  -- Complete agent reasoning trace
    model_used          VARCHAR(100),           -- e.g. 'claude-opus-4-20250514'
    prompt_tokens       INTEGER,
    completion_tokens   INTEGER,
    latency_ms          INTEGER,

    -- Confidence & decision
    confidence_score    NUMERIC(5,4),
    decision            VARCHAR(50),            -- approve | reject | escalate | flag
    decision_reason     TEXT,
    human_review_required BOOLEAN DEFAULT FALSE,
    human_reviewed_by   UUID,
    human_reviewed_at   TIMESTAMPTZ,
    human_decision      VARCHAR(50),

    -- Context
    session_id          VARCHAR(100),
    user_id             UUID REFERENCES identity.users(id),
    ip_hash             VARCHAR(64),

    -- Compliance
    ndpa_pii_accessed   BOOLEAN DEFAULT FALSE,  -- Did this action access PII?
    data_categories     TEXT[],                 -- Categories of data accessed
    legal_basis         VARCHAR(50),            -- consent | legitimate_interest | legal_obligation

    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_ai_logs_agent      ON ai_audit.agent_logs (agent_type, created_at DESC);
CREATE INDEX idx_ai_logs_task       ON ai_audit.agent_logs (task_id);
CREATE INDEX idx_ai_logs_entity     ON ai_audit.agent_logs (entity_type, entity_id);
CREATE INDEX idx_ai_logs_user       ON ai_audit.agent_logs (user_id);
CREATE INDEX idx_ai_logs_action     ON ai_audit.agent_logs (action);
CREATE INDEX idx_ai_logs_review     ON ai_audit.agent_logs (human_review_required)
    WHERE human_review_required = TRUE AND human_reviewed_at IS NULL;
CREATE INDEX idx_ai_logs_full_trace ON ai_audit.agent_logs USING GIN (full_trace);


-- ============================================================================
-- UTILITY FUNCTIONS
-- ============================================================================

-- Function: update updated_at automatically
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at trigger to all relevant tables
DO $$
DECLARE tbl RECORD;
BEGIN
    FOR tbl IN SELECT schemaname, tablename FROM pg_tables
               WHERE schemaname IN ('lga','identity','wallet')
               AND tablename NOT IN ('revenue_split_config') LOOP
        EXECUTE format(
            'CREATE OR REPLACE TRIGGER trg_set_updated_at
             BEFORE UPDATE ON %I.%I
             FOR EACH ROW EXECUTE FUNCTION set_updated_at()',
            tbl.schemaname, tbl.tablename
        );
    END LOOP;
END;
$$ LANGUAGE plpgsql;


-- Function: append entry to ai_agent_logs JSONB column
CREATE OR REPLACE FUNCTION append_ai_agent_log(
    p_table TEXT,
    p_schema TEXT,
    p_entity_id UUID,
    p_log_entry JSONB
) RETURNS VOID AS $$
BEGIN
    EXECUTE format(
        'UPDATE %I.%I SET ai_agent_logs = ai_agent_logs || $1::JSONB WHERE id = $2',
        p_schema, p_table
    ) USING jsonb_build_array(p_log_entry), p_entity_id;
END;
$$ LANGUAGE plpgsql;


-- View: Active wallets with user context
CREATE OR REPLACE VIEW wallet.v_active_wallets AS
SELECT
    w.id, w.user_id, w.wallet_type, w.currency,
    w.available_balance, w.escrow_balance, w.pending_balance,
    w.status, w.kyc_tier, w.lga_id,
    u.primary_role,
    u.digital_id_number,
    u.membership_tier,
    lg.name  AS lga_name,
    lg.code  AS lga_code
FROM wallet.wallets w
JOIN identity.users u ON u.id = w.user_id
LEFT JOIN lga.local_governments lg ON lg.id = w.lga_id
WHERE w.status = 'active'
  AND w.deleted_at IS NULL
  AND u.deleted_at IS NULL;


-- View: Pending IGR remittances (for OGIRS settlement job)
CREATE OR REPLACE VIEW wallet.v_pending_igr AS
SELECT
    t.id, t.lga_id, t.module, t.igr_amount, t.currency,
    t.created_at, t.completed_at,
    lg.name  AS lga_name,
    lg.code  AS lga_code,
    u.digital_id_number
FROM wallet.transactions t
LEFT JOIN lga.local_governments lg ON lg.id = t.lga_id
LEFT JOIN identity.users u ON u.id = t.user_id
WHERE t.igr_remitted = FALSE
  AND t.igr_amount > 0
  AND t.status = 'completed';


-- View: Escrow accounts due for auto-release
CREATE OR REPLACE VIEW wallet.v_escrow_due_release AS
SELECT
    e.id, e.reference, e.module, e.seller_payout_amount, e.currency,
    e.auto_release_at, e.buyer_user_id, e.seller_user_id,
    e.lga_id, lg.name AS lga_name
FROM wallet.escrow_accounts e
LEFT JOIN lga.local_governments lg ON lg.id = e.lga_id
WHERE e.status = 'holding'
  AND e.auto_release_at <= NOW();


\echo '✅ ISEYAA LGA Digital Profile System schema applied.'
\echo '   Schemas: lga | identity | wallet | ai_audit'
