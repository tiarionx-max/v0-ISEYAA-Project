# ISEYAA — LGA Digital Profile System
## Schema Reference Card  |  v1.0  |  Confidential

---

## Architecture at a Glance

```
PostgreSQL (AWS RDS Multi-AZ, af-south-1)
│
├── Schema: lga              ← LGA Profiles, Cultural, Tourism, Economic
│   ├── local_governments    (20 rows seeded — all Ogun State LGAs)
│   ├── cultural_assets      (monuments, festivals, artefacts...)
│   ├── tourism_attractions  (bookable venues, heritage sites...)
│   ├── economic_activities  (sector GDP, IGR contribution by year)
│   └── lga_news_feed        (AI-aggregated news per LGA)
│
├── Schema: identity         ← Users, KYC, Biometrics, Roles
│   ├── users                (all roles: citizen/tourist/vendor/admin)
│   ├── user_roles           (multi-role assignments)
│   ├── kyc_verifications    (NIN, BVN, face, liveness audit)
│   ├── biometric_sessions   (FaceID / fingerprint auth log)
│   ├── vendor_profiles      (extended vendor data)
│   └── tourist_profiles     (extended tourist data)
│
├── Schema: wallet           ← Finance (isolated RDS instance)
│   ├── wallets              (NGN + USD, personal/vendor/govt)
│   ├── transactions         (immutable double-entry ledger)
│   ├── escrow_accounts      (marketplace hold & release)
│   ├── revenue_split_config (IGR % by module & LGA)
│   ├── igr_remittance_log   (OGIRS batch audit)
│   └── vendor_payout_schedule
│
└── Schema: ai_audit         ← Central AI Decision Audit
    └── agent_logs           (all MAS actions, NDPA-compliant)
```

---

## Design Invariants

| Rule | Detail |
|------|--------|
| All PKs | `UUID v4` — `uuid_generate_v4()` |
| All monetary values | `NUMERIC(15,2)` — never `FLOAT` |
| All timestamps | `TIMESTAMPTZ` (stored UTC, displayed Africa/Lagos) |
| All PII fields | `_enc` suffix — AES-256-GCM via AWS KMS |
| All lookup fields | `_hash` suffix — SHA-256 (SHA-3-512 for biometrics) |
| AI audit | `ai_agent_logs JSONB NOT NULL DEFAULT '[]'` on every table |
| Soft deletes | `deleted_at TIMESTAMPTZ NULL` — never `DELETE` |
| Optimistic locking | `version INTEGER` on wallets — prevents race conditions |

---

## PII Encryption Architecture (NDPA §2.1)

```
Plaintext PII (in app memory only)
          │
          ▼
   EncryptionService.encrypt(plaintext)
          │
          ├── generate data key from AWS KMS
          ├── AES-256-GCM encrypt
          └── store ciphertext as base64 in <field>_enc
                          │
               DB stores: "AQIDBA...base64...==" (opaque)
                          │
          ┌───────────────┘
          │
   EncryptionService.decrypt(<field>_enc)
          │
          └── returns plaintext (only in app layer, never logged)
```

**Biometric-specific rule:** Raw biometric data processed entirely on-device.
Only `SHA-3-512(salt + feature_vector)` sent to server. 128-char hex string stored.
Match verification: `hash(incoming_feature) == stored_hash` — no reconstruction possible.

---

## Revenue Split Engine

For every transaction, the `RevenueSplitConfig` table determines:

```
gross_amount
    │
    ├── igr_amount     = gross × igr_pct / 100        → OGIRS (Ogun State IGR)
    ├── platform_fee   = gross × platform_fee_pct / 100 → ISEYAA platform
    └── net_amount     = gross − igr − platform_fee   → Seller / vendor payout

Default splits (seeded):
  Module          IGR%    Platform%   Seller%
  ─────────────────────────────────────────────
  events          5.00    2.50        92.50
  marketplace     2.50    2.50        95.00
  transport       3.00    2.00        95.00
  utilities       0.00    1.00        99.00
  hmo             1.50    1.50        97.00
  sports          2.00    2.00        96.00
  accommodation   4.00    3.00        93.00
```

LGA-specific overrides supported: insert row with `lga_id != NULL`.

---

## Escrow State Machine

```
                 ┌──────────────────────┐
  buyer pays ──▶ │       HOLDING        │
                 └──────┬───────┬───────┘
                        │       │
          buyer confirms│       │buyer raises dispute
                        │       │
                        ▼       ▼
                ┌────────┐  ┌──────────┐
                │RELEASED│  │DISPUTED  │──▶ admin review
                └────────┘  └──────────┘
                                │
                         ┌──────┴──────┐
                         ▼             ▼
                    ┌─────────┐  ┌──────────┐
                    │RELEASED │  │ REFUNDED │
                    │(seller) │  │ (buyer)  │
                    └─────────┘  └──────────┘

Auto-release: fires after auto_release_days (default 7) if status = 'holding'
              and no dispute raised. Handled by SettlementWorker background job.
```

---

## KYC Tiers & Wallet Limits (CBN-Compliant)

| Tier | Verifications Required | Daily Limit | Single Txn Limit |
|------|------------------------|-------------|-----------------|
| 0 | None (email+phone only) | ₦10,000 | ₦5,000 |
| 1 | Email + Phone OTP | ₦50,000 | ₦20,000 |
| 2 | NIN verified | ₦200,000 | ₦100,000 |
| 3 | BVN + Biometric | ₦500,000 | ₦200,000 |

Government/corporate wallets: custom limits, KYC tier 3 minimum.

---

## JSONB: ai_agent_logs Schema

Every entry appended to `ai_agent_logs` JSONB arrays follows this structure:

```json
{
  "log_id":         "uuid-v4",
  "agent_type":     "lga_intelligence | fraud_detection | kyc_reviewer | ...",
  "task_id":        "uuid-v4",
  "action":         "igr_report_generated | fraud_flagged | kyc_approved | ...",
  "timestamp":      "2026-04-24T12:00:00Z",
  "summary":        "Human-readable summary of what the agent did",
  "confidence":     0.9432,
  "decision":       "approve | reject | escalate | flag | null",
  "model":          "claude-opus-4-20250514",
  "tokens_used":    1247,
  "latency_ms":     834,
  "human_review":   false,
  "ndpa_pii":       false
}
```

The same event also writes a full record to `ai_audit.agent_logs` with the
complete reasoning trace in `full_trace JSONB`.

---

## FastAPI Endpoints Summary

### LGA Router (`/api/v1/lga`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | List all 20 Ogun State LGAs |
| GET | `/{code}` | Full LGA profile by code (ABN, SAG, ...) |
| GET | `/{lga_id}/cultural-assets` | Cultural assets for LGA |
| POST | `/{lga_id}/cultural-assets` | Register new cultural asset |
| GET | `/{lga_id}/tourism` | Tourism attractions |
| GET | `/{lga_id}/economic-activities` | Economic sector data |
| GET | `/{lga_id}/news` | AI-aggregated news feed |

### Identity Router (`/api/v1/identity`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/register` | Register new user (all roles) |
| GET | `/me` | Authenticated user profile |
| POST | `/kyc/verify` | Initiate KYC (NIN/BVN/face) |
| GET | `/kyc/{id}` | Poll KYC verification status |
| POST | `/biometric/enroll` | Enroll biometric (hash only) |
| POST | `/biometric/authenticate` | Biometric authentication |
| POST | `/vendor/onboard` | Vendor profile creation |

### Wallet Router (`/api/v1/wallet`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/me` | Current wallet balance |
| POST | `/topup` | Initiate Paystack top-up |
| GET | `/transactions` | Paginated transaction history |
| POST | `/escrow` | Create marketplace escrow |
| POST | `/escrow/{id}/confirm-delivery` | Release funds to seller |
| POST | `/escrow/{id}/dispute` | Raise escrow dispute |
| GET | `/revenue-split` | Active IGR split configuration |

### AI Audit Router (`/api/v1/ai-audit`) — government_officer+ only
| Method | Path | Description |
|--------|------|-------------|
| GET | `/logs` | Paginated AI agent audit log |

---

## Files in This Module

```
iseyaa-lga/
├── sql/
│   └── 001_lga_digital_profile_system.sql   ← Master DDL (run first)
├── models/
│   ├── database.py          ← SQLAlchemy engine + sessions
│   ├── lga_models.py        ← LGA schema ORM models
│   ├── identity_models.py   ← Identity schema ORM models
│   ├── wallet_models.py     ← Wallet schema ORM models
│   ├── ai_audit_model.py    ← AgentLog ORM + all Pydantic schemas
│   └── routers.py           ← All FastAPI routers
└── migrations/
    └── 0001_lga_digital_profile_system.py   ← Alembic migration
```

---

*ISEYAA LGA Digital Profile System  |  PRD v2.0  |  Ogun State Government  |  Confidential*
