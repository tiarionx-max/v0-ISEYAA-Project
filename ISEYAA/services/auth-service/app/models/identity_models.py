"""
ISEYAA — Identity Schema ORM Models
=====================================
SQLAlchemy 2.x async models for the `identity` PostgreSQL schema.

NDPA Compliance Architecture:
  ┌─────────────────────────────────────────────────────┐
  │  PII Field Strategy                                  │
  │  ─────────────────                                  │
  │  <field>_enc   → AES-256-GCM ciphertext (base64)   │
  │                  encrypted/decrypted in app layer    │
  │                  using AWS KMS data key              │
  │                                                     │
  │  <field>_hash  → SHA-256 (non-PII fields) or        │
  │                  SHA-3-512 (biometric) of plaintext  │
  │                  used for deduplication/lookup only  │
  │                                                     │
  │  Raw biometrics NEVER stored.                       │
  │  Only salted SHA-3-512 of feature vectors.          │
  └─────────────────────────────────────────────────────┘
"""

import uuid
from decimal import Decimal

from sqlalchemy import (
    Boolean, Column, Date, DateTime, ForeignKey,
    Index, Integer, Numeric, SmallInteger, String, Text,
    UniqueConstraint
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .database import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        Index("idx_users_role",       "primary_role"),
        Index("idx_users_status",     "account_status"),
        Index("idx_users_home_lga",   "home_lga_id"),
        Index("idx_users_kyc_tier",   "kyc_tier"),
        Index("idx_users_membership", "membership_tier"),
        Index("idx_users_digital_id", "digital_id_number"),
        Index("idx_users_ai_logs",    "ai_agent_logs", postgresql_using="gin"),
        {"schema": "identity"},
    )

    id                      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # ── Authentication (non-PII lookup fields) ────────────────────────────────
    email_hash              = Column(String(64), unique=True)      # SHA-256(lowercase email)
    phone_hash              = Column(String(64), unique=True)      # SHA-256(E.164 phone)
    username                = Column(String(100), unique=True)

    # ── Encrypted PII (AES-256-GCM via AWS KMS) ───────────────────────────────
    # These columns store base64-encoded ciphertext. Decryption happens in
    # app/services/encryption.py — NEVER in DB queries.
    full_name_enc           = Column(Text)
    email_enc               = Column(Text)
    phone_enc               = Column(Text)
    date_of_birth_enc       = Column(Text)
    address_enc             = Column(Text)
    gender_enc              = Column(Text)

    # ── Biometric hashes (SHA-3-512, salted — NDPA §2.1) ─────────────────────
    # Original biometric data is processed on-device and never transmitted raw.
    # Only the irreversible hash of the extracted feature vector is stored.
    face_id_hash             = Column(String(128))
    fingerprint_hash_r_index = Column(String(128))
    fingerprint_hash_l_thumb = Column(String(128))
    biometric_enrolled_at    = Column(DateTime(timezone=True))
    biometric_device_id      = Column(String(100))
    biometric_version        = Column(SmallInteger, default=1)

    # ── Government ID (encrypted + hashed) ────────────────────────────────────
    nin_hash                = Column(String(64), unique=True)
    nin_enc                 = Column(Text)
    nin_verified            = Column(Boolean, default=False)
    nin_verified_at         = Column(DateTime(timezone=True))
    bvn_hash                = Column(String(64), unique=True)
    bvn_enc                 = Column(Text)
    bvn_verified            = Column(Boolean, default=False)
    bvn_verified_at         = Column(DateTime(timezone=True))

    # ── Role & Status ─────────────────────────────────────────────────────────
    primary_role            = Column(String(50), nullable=False, default="citizen")
    account_status          = Column(String(30), nullable=False, default="pending_verification")

    # ── LGA Affiliation ───────────────────────────────────────────────────────
    home_lga_id             = Column(UUID(as_uuid=True), ForeignKey("lga.local_governments.id"))
    current_lga_id          = Column(UUID(as_uuid=True), ForeignKey("lga.local_governments.id"))

    # ── KYC ──────────────────────────────────────────────────────────────────
    kyc_tier                = Column(SmallInteger, nullable=False, default=0)
    kyc_completed_at        = Column(DateTime(timezone=True))
    kyc_provider            = Column(String(50))

    # ── Membership ───────────────────────────────────────────────────────────
    membership_tier         = Column(String(30), nullable=False, default="free")
    membership_expires_at   = Column(DateTime(timezone=True))

    # ── 2FA ──────────────────────────────────────────────────────────────────
    two_fa_enabled          = Column(Boolean, default=False)
    two_fa_method           = Column(String(20))               # totp | sms | whatsapp
    two_fa_secret_enc       = Column(Text)                     # Encrypted TOTP secret

    # ── OAuth ─────────────────────────────────────────────────────────────────
    google_sub              = Column(String(255), unique=True)
    apple_sub               = Column(String(255), unique=True)

    # ── Session ───────────────────────────────────────────────────────────────
    last_login_at           = Column(DateTime(timezone=True))
    last_login_ip_hash      = Column(String(64))
    failed_login_attempts   = Column(SmallInteger, default=0)
    locked_until            = Column(DateTime(timezone=True))

    # ── Language Preference ───────────────────────────────────────────────────
    preferred_language      = Column(String(10), default="en")   # en | yo | ha

    # ── NDPA Consent ─────────────────────────────────────────────────────────
    data_processing_consent = Column(Boolean, nullable=False, default=False)
    consent_given_at        = Column(DateTime(timezone=True))
    consent_version         = Column(String(20))
    marketing_consent       = Column(Boolean, default=False)
    data_retention_end      = Column(DateTime(timezone=True))

    # ── Profile ───────────────────────────────────────────────────────────────
    avatar_url              = Column(String(500))
    cover_image_url         = Column(String(500))
    bio                     = Column(Text)

    # ── Digital ID ───────────────────────────────────────────────────────────
    digital_id_number       = Column(String(30), unique=True)    # ISEYAA-OG-XXXXXXXX
    digital_id_issued_at    = Column(DateTime(timezone=True))
    digital_id_qr_url       = Column(String(500))

    # ── AI Agent audit log ────────────────────────────────────────────────────
    ai_agent_logs           = Column(JSONB, nullable=False, default=list)

    # ── Soft delete ───────────────────────────────────────────────────────────
    created_at              = Column(DateTime(timezone=True), server_default=func.now())
    updated_at              = Column(DateTime(timezone=True), onupdate=func.now())
    deleted_at              = Column(DateTime(timezone=True))

    # ── Relationships ──────────────────────────────────────────────────────────
    roles               = relationship("UserRole",           back_populates="user", lazy="select")
    kyc_verifications   = relationship("KYCVerification",    back_populates="user", lazy="select")
    biometric_sessions  = relationship("BiometricSession",   back_populates="user", lazy="select")
    vendor_profile      = relationship("VendorProfile",      back_populates="user", uselist=False)
    tourist_profile     = relationship("TouristProfile",     back_populates="user", uselist=False)

    def __repr__(self):
        return f"<User id={self.id} role={self.primary_role} kyc_tier={self.kyc_tier}>"

    @property
    def is_active(self) -> bool:
        return self.account_status == "active" and self.deleted_at is None

    @property
    def has_biometric(self) -> bool:
        return bool(self.face_id_hash or self.fingerprint_hash_r_index)

    @property
    def is_kyc_verified(self) -> bool:
        return self.kyc_tier >= 2

    def append_ai_log(self, entry: dict) -> None:
        current = list(self.ai_agent_logs or [])
        current.append(entry)
        self.ai_agent_logs = current


class UserRole(Base):
    __tablename__ = "user_roles"
    __table_args__ = (
        Index("idx_user_roles_user",   "user_id"),
        Index("idx_user_roles_role",   "role"),
        Index("idx_user_roles_status", "status"),
        UniqueConstraint("user_id", "role"),
        {"schema": "identity"},
    )

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id         = Column(UUID(as_uuid=True), ForeignKey("identity.users.id", ondelete="CASCADE"), nullable=False)
    role            = Column(String(50),  nullable=False)
    status          = Column(String(30),  nullable=False, default="pending")
    granted_by      = Column(UUID(as_uuid=True), ForeignKey("identity.users.id"))
    granted_at      = Column(DateTime(timezone=True), server_default=func.now())
    expires_at      = Column(DateTime(timezone=True))
    revoked_at      = Column(DateTime(timezone=True))
    revocation_reason = Column(Text)
    role_metadata   = Column(JSONB)
    ai_agent_logs   = Column(JSONB, nullable=False, default=list)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="roles", foreign_keys=[user_id])


class KYCVerification(Base):
    __tablename__ = "kyc_verifications"
    __table_args__ = (
        Index("idx_kyc_user",   "user_id"),
        Index("idx_kyc_type",   "verification_type"),
        Index("idx_kyc_status", "status"),
        {"schema": "identity"},
    )

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id             = Column(UUID(as_uuid=True), ForeignKey("identity.users.id", ondelete="CASCADE"), nullable=False)
    verification_type   = Column(String(50), nullable=False)
    # nin | bvn | face_match | liveness | document | address

    status              = Column(String(30), nullable=False, default="initiated")
    # initiated | pending | passed | failed | expired | manual_review

    provider            = Column(String(50))
    provider_reference  = Column(String(255))
    provider_response   = Column(JSONB)       # Sensitive fields redacted before storage

    confidence_score    = Column(Numeric(5, 4))
    failure_reason      = Column(String(255))
    reviewer_id         = Column(UUID(as_uuid=True), ForeignKey("identity.users.id"))
    reviewed_at         = Column(DateTime(timezone=True))
    reviewer_notes      = Column(Text)

    request_ip_hash     = Column(String(64))
    device_fingerprint  = Column(String(255))
    session_id          = Column(String(100))

    ai_agent_logs       = Column(JSONB, nullable=False, default=list)
    created_at          = Column(DateTime(timezone=True), server_default=func.now())
    expires_at          = Column(DateTime(timezone=True))

    user = relationship("User", back_populates="kyc_verifications", foreign_keys=[user_id])

    def __repr__(self):
        return f"<KYCVerification user={self.user_id} type={self.verification_type} status={self.status}>"


class BiometricSession(Base):
    """
    Log of every biometric authentication event.
    Raw biometric data NEVER stored — only outcome metrics and device info.
    Spoof detection results are flagged for security review.
    """
    __tablename__ = "biometric_sessions"
    __table_args__ = (
        Index("idx_biometric_user",    "user_id", "created_at"),
        Index("idx_biometric_outcome", "outcome"),
        Index("idx_biometric_spoof",   "spoof_detected"),
        {"schema": "identity"},
    )

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id             = Column(UUID(as_uuid=True), ForeignKey("identity.users.id", ondelete="CASCADE"), nullable=False)
    session_type        = Column(String(30), nullable=False)
    # face_id | fingerprint | iris | voice

    action              = Column(String(30), nullable=False)
    # enroll | authenticate | re_enroll | revoke

    outcome             = Column(String(20), nullable=False)
    # success | failed | spoof_detected | timeout | cancelled

    match_score         = Column(Numeric(5, 4))   # 0.0000–1.0000
    liveness_score      = Column(Numeric(5, 4))   # Anti-spoofing confidence
    spoof_detected      = Column(Boolean, default=False)

    device_id           = Column(String(100))
    device_os           = Column(String(50))
    device_model        = Column(String(100))
    app_version         = Column(String(20))
    ip_hash             = Column(String(64))

    ai_agent_logs       = Column(JSONB, nullable=False, default=list)
    created_at          = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="biometric_sessions")

    def __repr__(self):
        return f"<BiometricSession user={self.user_id} type={self.session_type} outcome={self.outcome}>"


class VendorProfile(Base):
    __tablename__ = "vendor_profiles"
    __table_args__ = (
        Index("idx_vendor_lga",       "lga_id"),
        Index("idx_vendor_category",  "business_category"),
        {"schema": "identity"},
    )

    id                      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id                 = Column(UUID(as_uuid=True), ForeignKey("identity.users.id", ondelete="CASCADE"), nullable=False, unique=True)
    lga_id                  = Column(UUID(as_uuid=True), ForeignKey("lga.local_governments.id"))

    business_name           = Column(String(255), nullable=False)
    business_slug           = Column(String(300), nullable=False, unique=True)
    business_category       = Column(String(100))
    business_description    = Column(Text)
    cac_registration_no     = Column(String(50))
    cac_verified            = Column(Boolean, default=False)
    tax_id                  = Column(String(50))
    tax_verified            = Column(Boolean, default=False)

    bank_account_name       = Column(String(255))
    bank_account_no_enc     = Column(Text)         # Encrypted
    bank_code               = Column(String(10))
    paystack_recipient_code = Column(String(100))

    is_premium              = Column(Boolean, default=False)
    is_featured             = Column(Boolean, default=False)
    storefront_url          = Column(String(500))
    average_rating          = Column(Numeric(3, 2))
    total_orders            = Column(Integer, default=0)
    total_revenue_ngn       = Column(Numeric(15, 2), default=Decimal("0"))

    ai_agent_logs           = Column(JSONB, nullable=False, default=list)
    onboarded_at            = Column(DateTime(timezone=True))
    created_at              = Column(DateTime(timezone=True), server_default=func.now())
    updated_at              = Column(DateTime(timezone=True), onupdate=func.now())
    deleted_at              = Column(DateTime(timezone=True))

    user = relationship("User", back_populates="vendor_profile")

    def __repr__(self):
        return f"<VendorProfile business={self.business_name!r}>"


class TouristProfile(Base):
    __tablename__ = "tourist_profiles"
    __table_args__ = {"schema": "identity"}

    id                          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id                     = Column(UUID(as_uuid=True), ForeignKey("identity.users.id", ondelete="CASCADE"), nullable=False, unique=True)

    nationality                 = Column(String(100))
    passport_no_enc             = Column(Text)
    passport_expiry_enc         = Column(Text)
    visa_type                   = Column(String(50))
    visa_expiry                 = Column(Date)

    tourism_interests           = Column(ARRAY(String))
    arrival_date                = Column(Date)
    departure_date              = Column(Date)
    accommodation_type          = Column(String(50))

    emergency_contact_name_enc  = Column(Text)
    emergency_contact_phone_enc = Column(Text)
    travel_insurance_provider   = Column(String(100))
    travel_insurance_policy_enc = Column(Text)

    total_visits                = Column(Integer, default=1)
    total_spent_ngn             = Column(Numeric(15, 2), default=Decimal("0"))
    total_spent_usd             = Column(Numeric(15, 2), default=Decimal("0"))
    favourite_lgas              = Column(ARRAY(UUID))

    ai_agent_logs               = Column(JSONB, nullable=False, default=list)
    created_at                  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at                  = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="tourist_profile")
