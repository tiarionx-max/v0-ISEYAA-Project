"""
ISEYAA — Alembic Migration
Initial: LGA Digital Profile System
Revision: 0001_lga_digital_profile_system
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_lga_digital_profile"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Extensions ────────────────────────────────────────────────────────────
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "btree_gin"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pg_trgm"')

    # ── Schemas ───────────────────────────────────────────────────────────────
    op.execute("CREATE SCHEMA IF NOT EXISTS lga")
    op.execute("CREATE SCHEMA IF NOT EXISTS identity")
    op.execute("CREATE SCHEMA IF NOT EXISTS wallet")
    op.execute("CREATE SCHEMA IF NOT EXISTS ai_audit")

    # ── lga.local_governments ─────────────────────────────────────────────────
    op.create_table(
        "local_governments",
        sa.Column("id",                  postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code",                sa.String(10),   nullable=False, unique=True),
        sa.Column("name",                sa.String(150),  nullable=False),
        sa.Column("slug",                sa.String(180),  nullable=False, unique=True),
        sa.Column("headquarters",        sa.String(150),  nullable=False),
        sa.Column("state",               sa.String(50),   nullable=False, default="Ogun"),
        sa.Column("country",             sa.String(50),   nullable=False, default="Nigeria"),
        sa.Column("geopolitical_zone",   sa.String(50),   nullable=False, default="South West"),
        sa.Column("latitude",            sa.Numeric(10, 8)),
        sa.Column("longitude",           sa.Numeric(11, 8)),
        sa.Column("area_km2",            sa.Numeric(10, 2)),
        sa.Column("boundary_geojson",    postgresql.JSONB),
        sa.Column("population_estimate", sa.Integer),
        sa.Column("population_year",     sa.SmallInteger),
        sa.Column("major_ethnic_groups", postgresql.ARRAY(sa.String)),
        sa.Column("major_languages",     postgresql.ARRAY(sa.String)),
        sa.Column("wards_count",         sa.Integer),
        sa.Column("gdp_estimate_ngn",    sa.Numeric(20, 2)),
        sa.Column("primary_economic_sector", sa.String(100)),
        sa.Column("literacy_rate_pct",   sa.Numeric(5, 2)),
        sa.Column("hospitals_count",     sa.Integer),
        sa.Column("electricity_access_pct", sa.Numeric(5, 2)),
        sa.Column("platform_registered_citizens", sa.Integer, default=0),
        sa.Column("platform_registered_vendors",  sa.Integer, default=0),
        sa.Column("platform_monthly_igr_ngn",  sa.Numeric(15, 2), default=0),
        sa.Column("is_active",           sa.Boolean, nullable=False, default=True),
        sa.Column("profile_completeness_pct", sa.Numeric(5, 2), default=0),
        sa.Column("ai_agent_logs",       postgresql.JSONB, nullable=False, server_default="'[]'"),
        sa.Column("created_at",          sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at",          sa.DateTime(timezone=True)),
        sa.Column("deleted_at",          sa.DateTime(timezone=True)),
        schema="lga",
    )
    op.create_index("idx_lga_ai_logs", "local_governments", ["ai_agent_logs"],
                    schema="lga", postgresql_using="gin")
    op.create_index("idx_lga_active", "local_governments", ["is_active"], schema="lga")

    # ── lga.cultural_assets ───────────────────────────────────────────────────
    op.create_table(
        "cultural_assets",
        sa.Column("id",           postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("lga_id",       postgresql.UUID(as_uuid=True), sa.ForeignKey("lga.local_governments.id"), nullable=False),
        sa.Column("name",         sa.String(255), nullable=False),
        sa.Column("slug",         sa.String(300), nullable=False, unique=True),
        sa.Column("asset_type",   sa.String(50),  nullable=False),
        sa.Column("description",  sa.Text),
        sa.Column("historical_period", sa.String(100)),
        sa.Column("significance", sa.Text),
        sa.Column("preservation_status", sa.String(50), default="good"),
        sa.Column("tags",         postgresql.ARRAY(sa.String)),
        sa.Column("virtual_tour_url", sa.String(500)),
        sa.Column("ai_generated_summary", sa.Text),
        sa.Column("ai_agent_logs", postgresql.JSONB, nullable=False, server_default="'[]'"),
        sa.Column("is_active",    sa.Boolean, default=True),
        sa.Column("created_at",   sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at",   sa.DateTime(timezone=True)),
        sa.Column("deleted_at",   sa.DateTime(timezone=True)),
        schema="lga",
    )

    # ── lga.tourism_attractions ───────────────────────────────────────────────
    op.create_table(
        "tourism_attractions",
        sa.Column("id",               postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("lga_id",           postgresql.UUID(as_uuid=True), sa.ForeignKey("lga.local_governments.id"), nullable=False),
        sa.Column("name",             sa.String(255), nullable=False),
        sa.Column("slug",             sa.String(300), nullable=False, unique=True),
        sa.Column("category",         sa.String(50),  nullable=False),
        sa.Column("description",      sa.Text),
        sa.Column("adult_price_ngn",  sa.Numeric(10, 2), default=0),
        sa.Column("is_bookable",      sa.Boolean, default=False),
        sa.Column("average_rating",   sa.Numeric(3, 2)),
        sa.Column("total_reviews",    sa.Integer, default=0),
        sa.Column("opening_hours",    postgresql.JSONB),
        sa.Column("ai_agent_logs",    postgresql.JSONB, nullable=False, server_default="'[]'"),
        sa.Column("is_active",        sa.Boolean, default=True),
        sa.Column("created_at",       sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at",       sa.DateTime(timezone=True)),
        sa.Column("deleted_at",       sa.DateTime(timezone=True)),
        schema="lga",
    )

    # ── lga.economic_activities ───────────────────────────────────────────────
    op.create_table(
        "economic_activities",
        sa.Column("id",                   postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("lga_id",               postgresql.UUID(as_uuid=True), sa.ForeignKey("lga.local_governments.id"), nullable=False),
        sa.Column("sector",               sa.String(100), nullable=False),
        sa.Column("reporting_year",       sa.SmallInteger, nullable=False),
        sa.Column("reporting_quarter",    sa.SmallInteger),
        sa.Column("estimated_gdp_ngn",    sa.Numeric(20, 2)),
        sa.Column("igr_contribution_ngn", sa.Numeric(15, 2)),
        sa.Column("platform_volume_ngn",  sa.Numeric(15, 2), default=0),
        sa.Column("ai_sector_analysis",   postgresql.JSONB),
        sa.Column("ai_agent_logs",        postgresql.JSONB, nullable=False, server_default="'[]'"),
        sa.Column("created_at",           sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        schema="lga",
    )

    # ── identity.users ────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id",                   postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email_hash",           sa.String(64), unique=True),
        sa.Column("phone_hash",           sa.String(64), unique=True),
        sa.Column("username",             sa.String(100), unique=True),
        sa.Column("full_name_enc",        sa.Text),
        sa.Column("email_enc",            sa.Text),
        sa.Column("phone_enc",            sa.Text),
        sa.Column("date_of_birth_enc",    sa.Text),
        sa.Column("address_enc",          sa.Text),
        sa.Column("face_id_hash",         sa.String(128)),
        sa.Column("fingerprint_hash_r_index", sa.String(128)),
        sa.Column("fingerprint_hash_l_thumb", sa.String(128)),
        sa.Column("biometric_enrolled_at", sa.DateTime(timezone=True)),
        sa.Column("nin_hash",             sa.String(64), unique=True),
        sa.Column("nin_enc",              sa.Text),
        sa.Column("nin_verified",         sa.Boolean, default=False),
        sa.Column("bvn_hash",             sa.String(64), unique=True),
        sa.Column("bvn_enc",              sa.Text),
        sa.Column("bvn_verified",         sa.Boolean, default=False),
        sa.Column("primary_role",         sa.String(50), nullable=False, default="citizen"),
        sa.Column("account_status",       sa.String(30), nullable=False, default="pending_verification"),
        sa.Column("home_lga_id",          postgresql.UUID(as_uuid=True), sa.ForeignKey("lga.local_governments.id")),
        sa.Column("kyc_tier",             sa.SmallInteger, nullable=False, default=0),
        sa.Column("membership_tier",      sa.String(30), nullable=False, default="free"),
        sa.Column("two_fa_enabled",       sa.Boolean, default=False),
        sa.Column("two_fa_secret_enc",    sa.Text),
        sa.Column("preferred_language",   sa.String(10), default="en"),
        sa.Column("data_processing_consent", sa.Boolean, nullable=False, default=False),
        sa.Column("consent_given_at",     sa.DateTime(timezone=True)),
        sa.Column("digital_id_number",    sa.String(30), unique=True),
        sa.Column("ai_agent_logs",        postgresql.JSONB, nullable=False, server_default="'[]'"),
        sa.Column("created_at",           sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at",           sa.DateTime(timezone=True)),
        sa.Column("deleted_at",           sa.DateTime(timezone=True)),
        schema="identity",
    )
    op.create_index("idx_users_ai_logs", "users", ["ai_agent_logs"],
                    schema="identity", postgresql_using="gin")

    # ── wallet.wallets ────────────────────────────────────────────────────────
    op.create_table(
        "wallets",
        sa.Column("id",                   postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id",              postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("wallet_type",          sa.String(30), nullable=False, default="personal"),
        sa.Column("currency",             sa.String(5),  nullable=False, default="NGN"),
        sa.Column("status",               sa.String(30), nullable=False, default="active"),
        sa.Column("available_balance",    sa.Numeric(15, 2), nullable=False, default=0),
        sa.Column("ledger_balance",       sa.Numeric(15, 2), nullable=False, default=0),
        sa.Column("escrow_balance",       sa.Numeric(15, 2), nullable=False, default=0),
        sa.Column("pending_balance",      sa.Numeric(15, 2), nullable=False, default=0),
        sa.Column("daily_debit_limit",    sa.Numeric(15, 2), nullable=False, default=50000),
        sa.Column("single_txn_limit",     sa.Numeric(15, 2), nullable=False, default=20000),
        sa.Column("daily_used",           sa.Numeric(15, 2), nullable=False, default=0),
        sa.Column("kyc_tier",             sa.SmallInteger, nullable=False, default=0),
        sa.Column("version",              sa.Integer, nullable=False, default=1),
        sa.Column("ai_agent_logs",        postgresql.JSONB, nullable=False, server_default="'[]'"),
        sa.Column("created_at",           sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at",           sa.DateTime(timezone=True)),
        schema="wallet",
    )

    # ── wallet.transactions ───────────────────────────────────────────────────
    op.create_table(
        "transactions",
        sa.Column("id",                   postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("wallet_id",            postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id",              postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lga_id",               postgresql.UUID(as_uuid=True)),
        sa.Column("transaction_type",     sa.String(50), nullable=False),
        sa.Column("direction",            sa.String(10), nullable=False),
        sa.Column("status",               sa.String(30), nullable=False, default="pending"),
        sa.Column("currency",             sa.String(5),  nullable=False, default="NGN"),
        sa.Column("gross_amount",         sa.Numeric(15, 2), nullable=False),
        sa.Column("platform_fee_amount",  sa.Numeric(15, 2), nullable=False, default=0),
        sa.Column("igr_amount",           sa.Numeric(15, 2), nullable=False, default=0),
        sa.Column("net_amount",           sa.Numeric(15, 2), nullable=False),
        sa.Column("balance_before",       sa.Numeric(15, 2), nullable=False),
        sa.Column("balance_after",        sa.Numeric(15, 2), nullable=False),
        sa.Column("igr_split_pct",        sa.Numeric(5, 2),  nullable=False, default=0),
        sa.Column("igr_remitted",         sa.Boolean, default=False),
        sa.Column("provider",             sa.String(30), nullable=False),
        sa.Column("provider_reference",   sa.String(255), unique=True),
        sa.Column("provider_metadata",    postgresql.JSONB),
        sa.Column("module",               sa.String(50)),
        sa.Column("module_reference_id",  postgresql.UUID(as_uuid=True)),
        sa.Column("narration",            sa.String(255)),
        sa.Column("ai_agent_logs",        postgresql.JSONB, nullable=False, server_default="'[]'"),
        sa.Column("created_at",           sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("completed_at",         sa.DateTime(timezone=True)),
        schema="wallet",
    )

    # ── ai_audit.agent_logs ───────────────────────────────────────────────────
    op.create_table(
        "agent_logs",
        sa.Column("id",                   postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("agent_type",           sa.String(50),  nullable=False),
        sa.Column("task_id",              postgresql.UUID(as_uuid=True)),
        sa.Column("entity_type",          sa.String(50),  nullable=False),
        sa.Column("entity_id",            postgresql.UUID(as_uuid=True)),
        sa.Column("action",               sa.String(100), nullable=False),
        sa.Column("input_summary",        sa.Text),
        sa.Column("output_summary",       sa.Text),
        sa.Column("full_trace",           postgresql.JSONB),
        sa.Column("model_used",           sa.String(100)),
        sa.Column("prompt_tokens",        sa.Integer),
        sa.Column("completion_tokens",    sa.Integer),
        sa.Column("latency_ms",           sa.Integer),
        sa.Column("confidence_score",     sa.Numeric(5, 4)),
        sa.Column("decision",             sa.String(50)),
        sa.Column("human_review_required", sa.Boolean, default=False),
        sa.Column("ndpa_pii_accessed",    sa.Boolean, default=False),
        sa.Column("data_categories",      postgresql.ARRAY(sa.String)),
        sa.Column("legal_basis",          sa.String(50)),
        sa.Column("user_id",              postgresql.UUID(as_uuid=True)),
        sa.Column("created_at",           sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        schema="ai_audit",
    )
    op.create_index("idx_ai_full_trace", "agent_logs", ["full_trace"],
                    schema="ai_audit", postgresql_using="gin")

    # ── updated_at trigger ────────────────────────────────────────────────────
    op.execute("""
    CREATE OR REPLACE FUNCTION set_updated_at()
    RETURNS TRIGGER AS $$
    BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
    $$ LANGUAGE plpgsql;
    """)
    for schema, table in [
        ("lga", "local_governments"), ("lga", "cultural_assets"),
        ("lga", "tourism_attractions"), ("identity", "users"),
        ("wallet", "wallets"),
    ]:
        op.execute(f"""
        CREATE OR REPLACE TRIGGER trg_set_updated_at
        BEFORE UPDATE ON {schema}.{table}
        FOR EACH ROW EXECUTE FUNCTION set_updated_at();
        """)


def downgrade() -> None:
    for schema, table in [
        ("ai_audit", "agent_logs"),
        ("wallet", "transactions"), ("wallet", "wallets"),
        ("identity", "users"),
        ("lga", "economic_activities"), ("lga", "tourism_attractions"),
        ("lga", "cultural_assets"), ("lga", "local_governments"),
    ]:
        op.execute(f"DROP TABLE IF EXISTS {schema}.{table} CASCADE")

    for schema in ["ai_audit", "wallet", "identity", "lga"]:
        op.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
