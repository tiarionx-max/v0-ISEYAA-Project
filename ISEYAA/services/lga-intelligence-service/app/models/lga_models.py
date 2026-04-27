"""
ISEYAA — LGA Schema ORM Models
================================
SQLAlchemy 2.x async models for the `lga` PostgreSQL schema.
Covers: local_governments, cultural_assets, tourism_attractions,
        economic_activities, lga_news_feed.

All models use UUID PKs, JSONB ai_agent_logs, and soft deletes.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    Boolean, Column, Date, DateTime, ForeignKey,
    Index, Integer, Numeric, SmallInteger, String, Text
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from .database import Base


class LocalGovernment(Base):
    __tablename__ = "local_governments"
    __table_args__ = (
        Index("idx_lga_name_trgm",  "name"),
        Index("idx_lga_ai_logs",    "ai_agent_logs", postgresql_using="gin"),
        Index("idx_lga_active",     "is_active"),
        {"schema": "lga"},
    )

    id                      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code                    = Column(String(10),  nullable=False, unique=True)
    name                    = Column(String(150), nullable=False)
    slug                    = Column(String(180), nullable=False, unique=True)
    headquarters            = Column(String(150), nullable=False)
    state                   = Column(String(50),  nullable=False, default="Ogun")
    country                 = Column(String(50),  nullable=False, default="Nigeria")
    geopolitical_zone       = Column(String(50),  nullable=False, default="South West")

    # Geography
    latitude                = Column(Numeric(10, 8))
    longitude               = Column(Numeric(11, 8))
    area_km2                = Column(Numeric(10, 2))
    boundary_geojson        = Column(JSONB)

    # Demographics
    population_estimate     = Column(Integer)
    population_year         = Column(SmallInteger)
    household_count         = Column(Integer)
    major_ethnic_groups     = Column(ARRAY(String))
    major_languages         = Column(ARRAY(String), default=["Yoruba", "English"])

    # Administrative
    local_government_chairman       = Column(String(255))
    chairman_since                  = Column(Date)
    council_members_count           = Column(Integer)
    wards_count                     = Column(Integer)
    polling_units_count             = Column(Integer)
    creation_date                   = Column(Date)
    lga_secretariat_address         = Column(Text)
    lga_website_url                 = Column(String(500))
    emergency_phone                 = Column(String(20))

    # Socioeconomic
    gdp_estimate_ngn                = Column(Numeric(20, 2))
    gdp_year                        = Column(SmallInteger)
    primary_economic_sector         = Column(String(100))
    poverty_index                   = Column(Numeric(5, 2))
    literacy_rate_pct               = Column(Numeric(5, 2))
    unemployment_rate_pct           = Column(Numeric(5, 2))
    registered_businesses           = Column(Integer)
    formal_employment_count         = Column(Integer)

    # Infrastructure
    electricity_access_pct          = Column(Numeric(5, 2))
    potable_water_access_pct        = Column(Numeric(5, 2))
    road_network_km                 = Column(Numeric(10, 2))
    internet_penetration_pct        = Column(Numeric(5, 2))
    hospitals_count                 = Column(Integer)
    primary_schools_count           = Column(Integer)
    secondary_schools_count         = Column(Integer)
    tertiary_institutions_count     = Column(Integer)

    # Platform metrics
    platform_registered_citizens    = Column(Integer, default=0)
    platform_registered_vendors     = Column(Integer, default=0)
    platform_monthly_igr_ngn        = Column(Numeric(15, 2), default=Decimal("0"))
    platform_last_synced_at         = Column(DateTime(timezone=True))

    # Media
    banner_image_url                = Column(String(500))
    coat_of_arms_url                = Column(String(500))
    gallery_urls                    = Column(ARRAY(String))

    # Status
    is_active                       = Column(Boolean, nullable=False, default=True)
    profile_completeness_pct        = Column(Numeric(5, 2), default=Decimal("0"))

    # AI Agent audit log — every AI interaction with this LGA record is appended here
    ai_agent_logs                   = Column(JSONB, nullable=False, default=list)

    # Metadata
    created_at                      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at                      = Column(DateTime(timezone=True), onupdate=func.now())
    deleted_at                      = Column(DateTime(timezone=True))

    # Relationships
    cultural_assets     = relationship("CulturalAsset",      back_populates="lga", lazy="select")
    tourism_attractions = relationship("TourismAttraction",   back_populates="lga", lazy="select")
    economic_activities = relationship("EconomicActivity",    back_populates="lga", lazy="select")
    news_feed           = relationship("LGANewsFeed",         back_populates="lga", lazy="select")

    def __repr__(self):
        return f"<LocalGovernment code={self.code} name={self.name!r}>"

    def append_ai_log(self, entry: dict) -> None:
        """Append an AI agent action to the audit log."""
        current = list(self.ai_agent_logs or [])
        current.append(entry)
        self.ai_agent_logs = current


class CulturalAsset(Base):
    __tablename__ = "cultural_assets"
    __table_args__ = (
        Index("idx_cultural_lga",     "lga_id"),
        Index("idx_cultural_type",    "asset_type"),
        Index("idx_cultural_ai_logs", "ai_agent_logs", postgresql_using="gin"),
        Index("idx_cultural_tags",    "tags",          postgresql_using="gin"),
        {"schema": "lga"},
    )

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lga_id              = Column(UUID(as_uuid=True), ForeignKey("lga.local_governments.id"), nullable=False)
    name                = Column(String(255), nullable=False)
    slug                = Column(String(300), nullable=False, unique=True)
    asset_type          = Column(String(50),  nullable=False)
    # monument | festival | artefact | language | craft | cuisine |
    # music_genre | dance_form | oral_tradition | religious_site

    description         = Column(Text)
    historical_period   = Column(String(100))
    origin_year         = Column(Integer)
    significance        = Column(Text)

    # Location
    physical_address    = Column(Text)
    latitude            = Column(Numeric(10, 8))
    longitude           = Column(Numeric(11, 8))
    google_maps_url     = Column(String(500))

    # Status
    unesco_listed       = Column(Boolean, default=False)
    national_monument   = Column(Boolean, default=False)
    preservation_status = Column(String(50), default="good")
    # excellent | good | fair | at_risk | critical | lost

    # Digital
    virtual_tour_url    = Column(String(500))
    ar_asset_url        = Column(String(500))
    media_urls          = Column(ARRAY(String))
    tags                = Column(ARRAY(String))

    # Visitor info
    admission_fee_ngn   = Column(Numeric(10, 2))
    visiting_hours      = Column(JSONB)
    annual_visitors     = Column(Integer)

    # AI enrichment
    ai_generated_summary = Column(Text)
    ai_agent_logs        = Column(JSONB, nullable=False, default=list)

    is_active           = Column(Boolean, default=True)
    created_at          = Column(DateTime(timezone=True), server_default=func.now())
    updated_at          = Column(DateTime(timezone=True), onupdate=func.now())
    deleted_at          = Column(DateTime(timezone=True))

    lga = relationship("LocalGovernment", back_populates="cultural_assets")

    def __repr__(self):
        return f"<CulturalAsset name={self.name!r} type={self.asset_type}>"


class TourismAttraction(Base):
    __tablename__ = "tourism_attractions"
    __table_args__ = (
        Index("idx_tourism_lga",      "lga_id"),
        Index("idx_tourism_category", "category"),
        Index("idx_tourism_bookable", "is_bookable"),
        Index("idx_tourism_ai_logs",  "ai_agent_logs", postgresql_using="gin"),
        {"schema": "lga"},
    )

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lga_id              = Column(UUID(as_uuid=True), ForeignKey("lga.local_governments.id"), nullable=False)
    name                = Column(String(255), nullable=False)
    slug                = Column(String(300), nullable=False, unique=True)
    category            = Column(String(50),  nullable=False)
    # nature | heritage | adventure | beach | waterfall | park |
    # museum | palace | religious | culinary | agritourism | sports

    description                     = Column(Text)
    highlights                      = Column(ARRAY(String))
    best_season                     = Column(String(100))
    duration_hours                  = Column(Numeric(4, 1))

    # Location
    address                         = Column(Text)
    lga_ward                        = Column(String(100))
    latitude                        = Column(Numeric(10, 8))
    longitude                       = Column(Numeric(11, 8))
    distance_from_abeokuta_km       = Column(Numeric(8, 2))

    # Pricing
    admission_free                  = Column(Boolean, default=False)
    adult_price_ngn                 = Column(Numeric(10, 2), default=Decimal("0"))
    child_price_ngn                 = Column(Numeric(10, 2), default=Decimal("0"))
    group_price_ngn                 = Column(Numeric(10, 2))
    foreign_price_usd               = Column(Numeric(10, 2))

    # Capacity & booking
    daily_capacity                  = Column(Integer)
    requires_booking                = Column(Boolean, default=False)
    advance_days                    = Column(Integer, default=0)
    is_bookable                     = Column(Boolean, default=False)

    # Facilities
    parking_available               = Column(Boolean, default=False)
    accessibility                   = Column(Boolean, default=False)
    guided_tours                    = Column(Boolean, default=False)
    facilities                      = Column(ARRAY(String))

    # Ratings
    average_rating                  = Column(Numeric(3, 2))
    total_reviews                   = Column(Integer, default=0)

    # Media
    cover_image_url                 = Column(String(500))
    gallery_urls                    = Column(ARRAY(String))
    virtual_tour_url                = Column(String(500))
    video_url                       = Column(String(500))

    # Operational
    opening_hours                   = Column(JSONB)
    contact_phone                   = Column(String(20))
    contact_email                   = Column(String(255))
    website_url                     = Column(String(500))
    tripadvisor_url                 = Column(String(500))
    managed_by_govt                 = Column(Boolean, default=False)

    # AI
    ai_itinerary_eligible           = Column(Boolean, default=True)
    ai_agent_logs                   = Column(JSONB, nullable=False, default=list)

    is_active                       = Column(Boolean, default=True)
    verified_at                     = Column(DateTime(timezone=True))
    created_at                      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at                      = Column(DateTime(timezone=True), onupdate=func.now())
    deleted_at                      = Column(DateTime(timezone=True))

    lga = relationship("LocalGovernment", back_populates="tourism_attractions")

    def __repr__(self):
        return f"<TourismAttraction name={self.name!r} category={self.category}>"


class EconomicActivity(Base):
    __tablename__ = "economic_activities"
    __table_args__ = (
        Index("idx_economic_lga",     "lga_id"),
        Index("idx_economic_sector",  "sector"),
        Index("idx_economic_year",    "reporting_year", "reporting_quarter"),
        Index("idx_economic_ai_logs", "ai_agent_logs", postgresql_using="gin"),
        {"schema": "lga"},
    )

    id                          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lga_id                      = Column(UUID(as_uuid=True), ForeignKey("lga.local_governments.id"), nullable=False)
    sector                      = Column(String(100), nullable=False)
    subsector                   = Column(String(100))
    reporting_year              = Column(SmallInteger, nullable=False)
    reporting_quarter           = Column(SmallInteger)

    estimated_gdp_ngn           = Column(Numeric(20, 2))
    employed_persons            = Column(Integer)
    registered_businesses       = Column(Integer)
    fdi_inflow_usd              = Column(Numeric(20, 2))
    tax_revenue_ngn             = Column(Numeric(15, 2))
    igr_contribution_ngn        = Column(Numeric(15, 2))
    platform_transactions       = Column(Integer, default=0)
    platform_volume_ngn         = Column(Numeric(15, 2), default=Decimal("0"))

    major_employers             = Column(ARRAY(String))
    key_products                = Column(ARRAY(String))
    infrastructure_gaps         = Column(ARRAY(String))
    growth_rate_pct             = Column(Numeric(6, 2))
    data_source                 = Column(String(255))
    notes                       = Column(Text)

    ai_sector_analysis          = Column(JSONB)
    ai_agent_logs               = Column(JSONB, nullable=False, default=list)

    created_at                  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at                  = Column(DateTime(timezone=True), onupdate=func.now())

    lga = relationship("LocalGovernment", back_populates="economic_activities")

    def __repr__(self):
        return f"<EconomicActivity lga={self.lga_id} sector={self.sector} year={self.reporting_year}>"


class LGANewsFeed(Base):
    __tablename__ = "lga_news_feed"
    __table_args__ = (
        Index("idx_news_lga",       "lga_id", "published_at"),
        Index("idx_news_sentiment", "sentiment"),
        {"schema": "lga"},
    )

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lga_id          = Column(UUID(as_uuid=True), ForeignKey("lga.local_governments.id"), nullable=False)
    headline        = Column(String(500), nullable=False)
    ai_summary      = Column(Text)
    source_url      = Column(String(1000))
    source_name     = Column(String(255))
    published_at    = Column(DateTime(timezone=True))
    sentiment       = Column(String(20))
    category        = Column(String(50))
    tags            = Column(ARRAY(String))
    ai_agent_logs   = Column(JSONB, nullable=False, default=list)
    is_published    = Column(Boolean, default=False)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    lga = relationship("LocalGovernment", back_populates="news_feed")
