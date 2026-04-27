"""
ISEYAA — AI Audit ORM Model + All Pydantic Schemas
====================================================
1. AgentLog — SQLAlchemy model for ai_audit.agent_logs
2. Pydantic v2 schemas for every model:
   LGA, Identity, Wallet, Escrow, RevenueSplit, AgentLog
"""

# ── Part 1: ORM Model ─────────────────────────────────────────────────────────

import uuid
from decimal import Decimal
from typing import Any, Dict, List, Optional
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Index,
    Integer, Numeric, SmallInteger, String, Text
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID, JSONB
from sqlalchemy.sql import func

from .database import Base


class AgentLog(Base):
    """
    Central AI agent decision log. Every AI action across all schemas
    writes here AND appends a summary to the entity's ai_agent_logs JSONB.
    Enables full audit trail for government-grade explainability.
    """
    __tablename__ = "agent_logs"
    __table_args__ = (
        Index("idx_ai_logs_agent",      "agent_type", "created_at"),
        Index("idx_ai_logs_task",       "task_id"),
        Index("idx_ai_logs_entity",     "entity_type", "entity_id"),
        Index("idx_ai_logs_user",       "user_id"),
        Index("idx_ai_logs_action",     "action"),
        Index("idx_ai_logs_review",     "human_review_required"),
        Index("idx_ai_full_trace",      "full_trace", postgresql_using="gin"),
        {"schema": "ai_audit"},
    )

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Agent identity
    agent_type          = Column(String(50),  nullable=False)
    task_id             = Column(UUID(as_uuid=True))
    parent_log_id       = Column(UUID(as_uuid=True), ForeignKey("ai_audit.agent_logs.id"))

    # Subject entity
    entity_type         = Column(String(50),  nullable=False)
    entity_id           = Column(UUID(as_uuid=True))

    # Action
    action              = Column(String(100), nullable=False)

    # Input / Output (sanitised — no raw PII)
    input_summary       = Column(Text)
    output_summary      = Column(Text)
    full_trace          = Column(JSONB)
    model_used          = Column(String(100))
    prompt_tokens       = Column(Integer)
    completion_tokens   = Column(Integer)
    latency_ms          = Column(Integer)

    # Confidence & decision
    confidence_score    = Column(Numeric(5, 4))
    decision            = Column(String(50))
    decision_reason     = Column(Text)
    human_review_required = Column(Boolean, default=False)
    human_reviewed_by   = Column(UUID(as_uuid=True))
    human_reviewed_at   = Column(DateTime(timezone=True))
    human_decision      = Column(String(50))

    # Context
    session_id          = Column(String(100))
    user_id             = Column(UUID(as_uuid=True))
    ip_hash             = Column(String(64))

    # NDPA compliance fields
    ndpa_pii_accessed   = Column(Boolean, default=False)
    data_categories     = Column(ARRAY(String))
    legal_basis         = Column(String(50))
    # consent | legitimate_interest | legal_obligation

    created_at          = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<AgentLog agent={self.agent_type} action={self.action} entity={self.entity_type}:{self.entity_id}>"


# ── Part 2: Pydantic v2 Schemas ───────────────────────────────────────────────

from pydantic import BaseModel, Field, field_validator, model_validator, UUID4, EmailStr
from typing import Annotated


# ── LGA Schemas ───────────────────────────────────────────────────────────────

class LocalGovernmentBase(BaseModel):
    code:               str   = Field(..., max_length=10)
    name:               str   = Field(..., max_length=150)
    headquarters:       str   = Field(..., max_length=150)
    latitude:           Optional[float] = None
    longitude:          Optional[float] = None
    area_km2:           Optional[float] = None
    population_estimate: Optional[int]  = None
    primary_economic_sector: Optional[str] = None

class LocalGovernmentResponse(LocalGovernmentBase):
    id:                 UUID4
    slug:               str
    state:              str
    profile_completeness_pct: float
    platform_registered_citizens:  int
    platform_registered_vendors:   int
    platform_monthly_igr_ngn:      Decimal
    is_active:          bool
    created_at:         datetime

    model_config = {"from_attributes": True}

class LocalGovernmentDetail(LocalGovernmentResponse):
    """Full detail — includes all demographic and infrastructure fields."""
    gdp_estimate_ngn:       Optional[Decimal]
    literacy_rate_pct:      Optional[float]
    unemployment_rate_pct:  Optional[float]
    hospitals_count:        Optional[int]
    electricity_access_pct: Optional[float]
    major_ethnic_groups:    Optional[List[str]]
    ai_agent_logs:          List[Dict[str, Any]] = []

    model_config = {"from_attributes": True}


class CulturalAssetCreate(BaseModel):
    lga_id:             UUID4
    name:               str   = Field(..., max_length=255)
    asset_type:         str   = Field(..., description="monument|festival|artefact|language|craft|cuisine|music_genre|dance_form|oral_tradition|religious_site")
    description:        Optional[str] = None
    historical_period:  Optional[str] = None
    significance:       Optional[Text] = None
    preservation_status: str = "good"
    tags:               Optional[List[str]] = None

class CulturalAssetResponse(CulturalAssetCreate):
    id:             UUID4
    slug:           str
    is_active:      bool
    created_at:     datetime
    ai_agent_logs:  List[Dict[str, Any]] = []

    model_config = {"from_attributes": True}


class TourismAttractionCreate(BaseModel):
    lga_id:             UUID4
    name:               str   = Field(..., max_length=255)
    category:           str   = Field(..., description="nature|heritage|adventure|beach|waterfall|park|museum|palace|religious|culinary|agritourism|sports")
    description:        Optional[str] = None
    highlights:         Optional[List[str]] = None
    admission_free:     bool  = False
    adult_price_ngn:    Decimal = Decimal("0")
    requires_booking:   bool  = False
    is_bookable:        bool  = False
    latitude:           Optional[float] = None
    longitude:          Optional[float] = None

class TourismAttractionResponse(TourismAttractionCreate):
    id:             UUID4
    slug:           str
    average_rating: Optional[float]
    total_reviews:  int
    is_active:      bool
    created_at:     datetime
    ai_agent_logs:  List[Dict[str, Any]] = []

    model_config = {"from_attributes": True}


# ── Identity Schemas ──────────────────────────────────────────────────────────

class UserRegisterRequest(BaseModel):
    """
    Registration request. Raw PII provided here; encrypted in service layer
    before DB persistence. Never log or cache this object.
    """
    full_name:          str   = Field(..., min_length=2, max_length=255)
    email:              EmailStr
    phone:              str   = Field(..., description="Nigerian phone in E.164 format: +2348XXXXXXXXX")
    password:           str   = Field(..., min_length=8, max_length=128)
    primary_role:       str   = Field(default="citizen", description="citizen|tourist|vendor|athlete|event_organiser|hotel_operator|transport_operator")
    home_lga_id:        Optional[UUID4] = None
    preferred_language: str   = Field(default="en", description="en|yo|ha")
    data_processing_consent: bool = Field(..., description="NDPA consent — required")
    marketing_consent:  bool  = False

    @field_validator("phone")
    @classmethod
    def validate_nigerian_phone(cls, v: str) -> str:
        import re
        if not re.match(r"^\+234[789][01]\d{8}$", v):
            raise ValueError("Must be a valid Nigerian mobile number in E.164 format (+234XXXXXXXXXX)")
        return v

    @field_validator("data_processing_consent")
    @classmethod
    def consent_required(cls, v: bool) -> bool:
        if not v:
            raise ValueError("Data processing consent is required under NDPA.")
        return v

class UserResponse(BaseModel):
    """Public-safe user response. Never expose encrypted fields or hashes."""
    id:                     UUID4
    username:               Optional[str]
    primary_role:           str
    account_status:         str
    kyc_tier:               int
    membership_tier:        str
    home_lga_id:            Optional[UUID4]
    preferred_language:     str
    digital_id_number:      Optional[str]
    two_fa_enabled:         bool
    has_biometric:          bool
    avatar_url:             Optional[str]
    created_at:             datetime

    model_config = {"from_attributes": True}

class UserDetailResponse(UserResponse):
    """Extended response for authenticated user's own profile."""
    marketing_consent:      bool
    data_processing_consent: bool
    consent_version:        Optional[str]
    ai_agent_logs:          List[Dict[str, Any]] = []

    model_config = {"from_attributes": True}


class KYCVerificationRequest(BaseModel):
    verification_type:  str   = Field(..., description="nin|bvn|face_match|liveness|document|address")
    provider:           str   = Field(..., description="nimc|youverify|smile_id|manual")
    nin:                Optional[str] = Field(None, min_length=11, max_length=11, description="11-digit NIN")
    bvn:                Optional[str] = Field(None, min_length=11, max_length=11, description="11-digit BVN")
    provider_reference: Optional[str] = None

    @field_validator("nin", "bvn", mode="before")
    @classmethod
    def validate_id_format(cls, v: Optional[str]) -> Optional[str]:
        if v and not v.isdigit():
            raise ValueError("NIN/BVN must be numeric only")
        return v

class KYCVerificationResponse(BaseModel):
    id:                 UUID4
    user_id:            UUID4
    verification_type:  str
    status:             str
    confidence_score:   Optional[float]
    created_at:         datetime
    ai_agent_logs:      List[Dict[str, Any]] = []

    model_config = {"from_attributes": True}


class BiometricEnrollRequest(BaseModel):
    session_type:       str   = Field(..., description="face_id|fingerprint|iris|voice")
    # Note: Raw biometric data processed on-device.
    # Only the SHA-3-512 hash of the feature vector is sent to the server.
    feature_hash:       str   = Field(..., min_length=128, max_length=128, description="SHA-3-512 of biometric feature vector")
    liveness_score:     float = Field(..., ge=0.0, le=1.0)
    device_id:          str
    device_os:          str
    device_model:       str
    app_version:        str

class BiometricAuthRequest(BaseModel):
    session_type:       str
    feature_hash:       str   = Field(..., min_length=128, max_length=128)
    liveness_score:     float = Field(..., ge=0.0, le=1.0)
    device_id:          str

class BiometricSessionResponse(BaseModel):
    id:                 UUID4
    session_type:       str
    action:             str
    outcome:            str
    match_score:        Optional[float]
    liveness_score:     Optional[float]
    spoof_detected:     bool
    created_at:         datetime

    model_config = {"from_attributes": True}


class VendorProfileCreate(BaseModel):
    business_name:          str   = Field(..., max_length=255)
    business_category:      str
    business_description:   Optional[str] = None
    lga_id:                 Optional[UUID4] = None
    cac_registration_no:    Optional[str] = None
    tax_id:                 Optional[str] = None

class VendorProfileResponse(VendorProfileCreate):
    id:             UUID4
    user_id:        UUID4
    business_slug:  str
    cac_verified:   bool
    tax_verified:   bool
    is_premium:     bool
    average_rating: Optional[float]
    total_orders:   int
    created_at:     datetime

    model_config = {"from_attributes": True}


# ── Wallet Schemas ────────────────────────────────────────────────────────────

class WalletResponse(BaseModel):
    id:                     UUID4
    user_id:                UUID4
    wallet_type:            str
    currency:               str
    status:                 str
    available_balance:      Decimal
    escrow_balance:         Decimal
    pending_balance:        Decimal
    total_balance:          Decimal
    kyc_tier:               int
    daily_debit_limit:      Decimal
    daily_used:             Decimal
    lga_id:                 Optional[UUID4]
    created_at:             datetime

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def compute_total_balance(cls, data: Any) -> Any:
        if hasattr(data, "available_balance") and hasattr(data, "escrow_balance"):
            data.__dict__["total_balance"] = (
                (data.available_balance or Decimal("0"))
                + (data.escrow_balance or Decimal("0"))
            )
        return data


class TopUpRequest(BaseModel):
    amount_ngn:         Decimal = Field(..., gt=0, le=Decimal("1000000"), description="Amount in NGN")
    provider:           str     = Field(default="paystack", description="paystack|flutterwave")
    callback_url:       Optional[str] = None

class TransferRequest(BaseModel):
    recipient_wallet_id: UUID4
    amount_ngn:          Decimal = Field(..., gt=0)
    narration:           str     = Field(..., max_length=255)

    @field_validator("amount_ngn")
    @classmethod
    def validate_min_transfer(cls, v: Decimal) -> Decimal:
        if v < Decimal("10"):
            raise ValueError("Minimum transfer amount is ₦10.00")
        return v


class TransactionResponse(BaseModel):
    id:                 UUID4
    wallet_id:          UUID4
    transaction_type:   str
    direction:          str
    status:             str
    currency:           str
    gross_amount:       Decimal
    net_amount:         Decimal
    platform_fee_amount: Decimal
    igr_amount:         Decimal
    provider:           str
    provider_reference: Optional[str]
    module:             Optional[str]
    narration:          Optional[str]
    balance_before:     Decimal
    balance_after:      Decimal
    created_at:         datetime
    completed_at:       Optional[datetime]
    ai_agent_logs:      List[Dict[str, Any]] = []

    model_config = {"from_attributes": True}


class EscrowCreateRequest(BaseModel):
    seller_user_id:         UUID4
    amount_ngn:             Decimal = Field(..., gt=0)
    module:                 str     = Field(..., description="marketplace|events|transport|services")
    module_reference_id:    UUID4
    module_reference_type:  str
    description:            str     = Field(..., max_length=500)
    auto_release_days:      int     = Field(default=7, ge=1, le=90)

class EscrowResponse(BaseModel):
    id:                     UUID4
    reference:              str
    status:                 str
    currency:               str
    gross_amount:           Decimal
    seller_payout_amount:   Decimal
    platform_fee_ngn:       Decimal
    igr_amount_ngn:         Decimal
    module:                 str
    auto_release_at:        datetime
    dispute_raised_at:      Optional[datetime]
    released_at:            Optional[datetime]
    created_at:             datetime
    ai_agent_logs:          List[Dict[str, Any]] = []

    model_config = {"from_attributes": True}


class RevenueSplitConfigResponse(BaseModel):
    id:                 UUID4
    module:             str
    lga_id:             Optional[UUID4]
    currency:           str
    igr_pct:            Decimal
    platform_fee_pct:   Decimal
    seller_pct:         Decimal
    effective_from:     datetime
    effective_to:       Optional[datetime]
    notes:              Optional[str]

    model_config = {"from_attributes": True}


# ── AI Audit Schemas ──────────────────────────────────────────────────────────

class AgentLogCreate(BaseModel):
    agent_type:             str
    task_id:                Optional[UUID4] = None
    entity_type:            str
    entity_id:              Optional[UUID4] = None
    action:                 str
    input_summary:          Optional[str] = None
    output_summary:         Optional[str] = None
    full_trace:             Optional[Dict[str, Any]] = None
    model_used:             Optional[str] = None
    prompt_tokens:          Optional[int] = None
    completion_tokens:      Optional[int] = None
    latency_ms:             Optional[int] = None
    confidence_score:       Optional[float] = None
    decision:               Optional[str] = None
    decision_reason:        Optional[str] = None
    human_review_required:  bool = False
    ndpa_pii_accessed:      bool = False
    data_categories:        Optional[List[str]] = None
    legal_basis:            Optional[str] = None
    user_id:                Optional[UUID4] = None

class AgentLogResponse(AgentLogCreate):
    id:             UUID4
    created_at:     datetime

    model_config = {"from_attributes": True}


# ── Pagination ────────────────────────────────────────────────────────────────

class PaginatedResponse(BaseModel):
    items:      List[Any]
    total:      int
    page:       int
    page_size:  int
    pages:      int

    @model_validator(mode="before")
    @classmethod
    def compute_pages(cls, data: Any) -> Any:
        if isinstance(data, dict):
            total     = data.get("total", 0)
            page_size = data.get("page_size", 20)
            data["pages"] = max(1, -(-total // page_size))  # ceiling division
        return data
