"""
ISEYAA — Wallet Service Database Models
=========================================
ACID-compliant financial schema. All monetary values stored as NUMERIC(15,2).
Double-entry bookkeeping pattern for audit trail integrity.
CBN-compliant transaction logging.

PRD Reference: §4.2 Digital Wallet & Payments, §6.1 PCI-DSS
"""

import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, ForeignKey,
    Index, Integer, Numeric, String, Text, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class WalletStatus(str, PyEnum):
    ACTIVE    = "active"
    SUSPENDED = "suspended"
    FROZEN    = "frozen"     # Regulatory hold
    CLOSED    = "closed"


class Currency(str, PyEnum):
    NGN = "NGN"  # Nigerian Naira (primary)
    USD = "USD"  # Cross-border / diaspora


class TransactionType(str, PyEnum):
    CREDIT          = "credit"
    DEBIT           = "debit"
    ESCROW_HOLD     = "escrow_hold"
    ESCROW_RELEASE  = "escrow_release"
    ESCROW_REFUND   = "escrow_refund"
    IGR_REMITTANCE  = "igr_remittance"   # To Ogun State revenue
    PLATFORM_FEE    = "platform_fee"
    VENDOR_PAYOUT   = "vendor_payout"
    REFUND          = "refund"
    WALLET_TOPUP    = "wallet_topup"
    UTILITY_PAYMENT = "utility_payment"
    TAX_PAYMENT     = "tax_payment"


class TransactionStatus(str, PyEnum):
    PENDING    = "pending"
    PROCESSING = "processing"
    COMPLETED  = "completed"
    FAILED     = "failed"
    REVERSED   = "reversed"
    DISPUTED   = "disputed"


class PaymentProvider(str, PyEnum):
    PAYSTACK    = "paystack"
    FLUTTERWAVE = "flutterwave"
    MONO        = "mono"
    NIBSS       = "nibss"
    INTERNAL    = "internal"    # Wallet-to-wallet


class EscrowStatus(str, PyEnum):
    HOLDING   = "holding"
    RELEASED  = "released"
    REFUNDED  = "refunded"
    DISPUTED  = "disputed"


class Wallet(Base):
    __tablename__ = "wallets"
    __table_args__ = (
        Index("idx_wallets_user_currency", "user_id", "currency"),
        {"schema": "wallet"},
    )

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id     = Column(UUID(as_uuid=True), nullable=False, index=True)
    currency    = Column(Enum(Currency), nullable=False, default=Currency.NGN)
    status      = Column(Enum(WalletStatus), default=WalletStatus.ACTIVE, index=True)

    # Balances — always use NUMERIC for money, never FLOAT
    available_balance  = Column(Numeric(15, 2), nullable=False, default=Decimal("0.00"))
    ledger_balance     = Column(Numeric(15, 2), nullable=False, default=Decimal("0.00"))
    escrow_balance     = Column(Numeric(15, 2), nullable=False, default=Decimal("0.00"))  # Held funds

    # Limits (CBN-compliant)
    daily_transaction_limit  = Column(Numeric(15, 2), default=Decimal("500000.00"))  # ₦500k/day
    single_transaction_limit = Column(Numeric(15, 2), default=Decimal("200000.00"))  # ₦200k/txn

    # KYC tier affects limits (NDPC-compliant)
    kyc_tier        = Column(Integer, default=1)   # 1=basic, 2=standard, 3=premium
    bvn_linked      = Column(Boolean, default=False)
    nin_verified    = Column(Boolean, default=False)

    # Audit
    version         = Column(Integer, default=1, nullable=False)  # Optimistic locking
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())

    transactions = relationship("Transaction", back_populates="wallet",
                                foreign_keys="[Transaction.wallet_id]")

    def __repr__(self):
        return f"<Wallet user={self.user_id} balance={self.available_balance} {self.currency}>"


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        Index("idx_txn_wallet_created",  "wallet_id", "created_at"),
        Index("idx_txn_reference",       "provider_reference"),
        Index("idx_txn_status",          "status"),
        Index("idx_txn_type_created",    "transaction_type", "created_at"),
        {"schema": "wallet"},
    )

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wallet_id         = Column(UUID(as_uuid=True), ForeignKey("wallet.wallets.id"), nullable=False, index=True)
    counterparty_wallet_id = Column(UUID(as_uuid=True), ForeignKey("wallet.wallets.id"), nullable=True)

    transaction_type  = Column(Enum(TransactionType), nullable=False, index=True)
    status            = Column(Enum(TransactionStatus), default=TransactionStatus.PENDING, index=True)
    currency          = Column(Enum(Currency), nullable=False, default=Currency.NGN)

    # Amounts
    amount            = Column(Numeric(15, 2), nullable=False)
    fee               = Column(Numeric(15, 2), default=Decimal("0.00"))
    igr_amount        = Column(Numeric(15, 2), default=Decimal("0.00"))   # Ogun State IGR share
    platform_fee      = Column(Numeric(15, 2), default=Decimal("0.00"))
    net_amount        = Column(Numeric(15, 2), nullable=False)            # amount - fee

    # Balance snapshot (for audit)
    balance_before    = Column(Numeric(15, 2), nullable=False)
    balance_after     = Column(Numeric(15, 2), nullable=False)

    # Payment provider
    provider          = Column(Enum(PaymentProvider), nullable=False)
    provider_reference = Column(String(255), index=True)   # Paystack/Flutterwave reference
    provider_metadata  = Column(JSONB)

    # Context
    module            = Column(String(50))   # events | marketplace | transport | utilities
    module_reference  = Column(UUID(as_uuid=True))   # event_id, order_id, ride_id, etc.
    description       = Column(String(500))
    metadata          = Column(JSONB)

    # OGIRS tax tagging
    ogirs_reference   = Column(String(100))
    tax_category      = Column(String(50))

    # Failure tracking
    failure_reason    = Column(Text)
    retry_count       = Column(Integer, default=0)

    # CBN audit fields
    narration         = Column(String(255))
    session_id        = Column(String(100))  # NIBSS session ID

    created_at        = Column(DateTime(timezone=True), server_default=func.now())
    completed_at      = Column(DateTime(timezone=True))

    wallet = relationship("Wallet", back_populates="transactions",
                          foreign_keys=[wallet_id])

    def __repr__(self):
        return f"<Transaction id={self.id} type={self.transaction_type} amount={self.amount} {self.currency}>"


class EscrowAccount(Base):
    """
    Escrow holds funds for marketplace transactions until delivery confirmed.
    Funds released to vendor on confirmation; returned to buyer on dispute resolution.
    """
    __tablename__ = "escrow_accounts"
    __table_args__ = (
        Index("idx_escrow_module_ref", "module", "module_reference"),
        {"schema": "wallet"},
    )

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    buyer_wallet_id     = Column(UUID(as_uuid=True), ForeignKey("wallet.wallets.id"), nullable=False)
    seller_wallet_id    = Column(UUID(as_uuid=True), ForeignKey("wallet.wallets.id"), nullable=False)
    amount              = Column(Numeric(15, 2), nullable=False)
    currency            = Column(Enum(Currency), default=Currency.NGN)
    status              = Column(Enum(EscrowStatus), default=EscrowStatus.HOLDING, index=True)

    module              = Column(String(50), nullable=False)    # marketplace | events | transport
    module_reference    = Column(UUID(as_uuid=True), nullable=False)   # order_id, booking_id

    # Release conditions
    auto_release_at     = Column(DateTime(timezone=True))   # Auto-release if no dispute
    release_transaction_id = Column(UUID(as_uuid=True), ForeignKey("wallet.transactions.id"))
    dispute_raised_at   = Column(DateTime(timezone=True))
    dispute_resolved_by = Column(UUID(as_uuid=True))   # Admin user ID
    resolution_notes    = Column(Text)

    created_at          = Column(DateTime(timezone=True), server_default=func.now())
    updated_at          = Column(DateTime(timezone=True), onupdate=func.now())


class IGRRemittanceLog(Base):
    """
    Audit log for all IGR remittances to Ogun State Government.
    Every transaction involving state revenue must have an entry here.
    """
    __tablename__ = "igr_remittance_logs"
    __table_args__ = ({"schema": "wallet"},)

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id      = Column(UUID(as_uuid=True), ForeignKey("wallet.transactions.id"), nullable=False)
    amount_ngn          = Column(Numeric(15, 2), nullable=False)
    source_module       = Column(String(50), nullable=False)
    source_lga          = Column(String(100))
    ogirs_batch_id      = Column(String(100))         # OGIRS remittance batch reference
    ogirs_acknowledged  = Column(Boolean, default=False)
    ogirs_acknowledged_at = Column(DateTime(timezone=True))
    created_at          = Column(DateTime(timezone=True), server_default=func.now())
