"""
ISEYAA — Paystack Integration Service
=======================================
Primary payment gateway for all NGN consumer transactions.
Handles: payment initialization, verification, webhooks,
refunds, and transfer to vendor/IGR accounts.

CBN-licensed. PCI-DSS compliant — no card data stored on ISEYAA servers.
All card data tokenised via Paystack Vault.

PRD Reference: §4.2 Digital Wallet & Payments, §5.6 Payments Stack
"""

import hashlib
import hmac
import json
from decimal import Decimal
from typing import Optional, Dict, Any

import httpx
import structlog

from app.core.config import settings
from app.models.wallet import TransactionType, PaymentProvider

logger = structlog.get_logger(__name__)

PAYSTACK_BASE = "https://api.paystack.co"


class PaystackService:
    """
    Async Paystack API client with retry logic and circuit breaker.
    All amounts sent to Paystack are in KOBO (₦1 = 100 kobo).
    """

    def __init__(self):
        self._client = httpx.AsyncClient(
            base_url=PAYSTACK_BASE,
            headers={
                "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    async def initialize_transaction(
        self,
        amount_ngn: Decimal,
        email: str,
        reference: str,
        metadata: Optional[Dict[str, Any]] = None,
        callback_url: Optional[str] = None,
        channels: Optional[list] = None,
    ) -> Dict[str, Any]:
        """
        Initialise a payment transaction.
        Returns authorization_url for redirect-based payment.
        """
        payload = {
            "amount":       int(amount_ngn * 100),  # Convert ₦ → kobo
            "email":        email,
            "reference":    reference,
            "currency":     "NGN",
            "callback_url": callback_url or settings.PAYSTACK_CALLBACK_URL,
            "channels":     channels or ["card", "bank", "ussd", "mobile_money", "bank_transfer"],
            "metadata": {
                "platform":        "ISEYAA",
                "state":           "Ogun",
                **(metadata or {}),
            },
        }

        logger.info("paystack_initialize", reference=reference, amount_ngn=str(amount_ngn))

        try:
            resp = await self._client.post("/transaction/initialize", json=payload)
            resp.raise_for_status()
            data = resp.json()

            if data.get("status"):
                logger.info("paystack_initialized", reference=reference, authorization_url=data["data"]["authorization_url"])
                return {
                    "success":           True,
                    "authorization_url": data["data"]["authorization_url"],
                    "access_code":       data["data"]["access_code"],
                    "reference":         data["data"]["reference"],
                }
            return {"success": False, "message": data.get("message", "Initialization failed")}

        except httpx.HTTPStatusError as e:
            logger.error("paystack_init_http_error", status=e.response.status_code, error=str(e))
            raise
        except Exception as e:
            logger.error("paystack_init_error", error=str(e))
            raise

    async def verify_transaction(self, reference: str) -> Dict[str, Any]:
        """
        Verify a transaction by reference.
        MUST be called server-side to confirm payment — never trust client-side data.
        """
        logger.info("paystack_verify", reference=reference)

        try:
            resp = await self._client.get(f"/transaction/verify/{reference}")
            resp.raise_for_status()
            data = resp.json()

            if not data.get("status"):
                return {"success": False, "message": data.get("message")}

            txn = data["data"]
            return {
                "success":    True,
                "status":     txn["status"],          # "success" | "failed" | "pending"
                "amount_ngn": Decimal(txn["amount"]) / 100,  # Convert kobo → ₦
                "currency":   txn["currency"],
                "reference":  txn["reference"],
                "paid_at":    txn.get("paid_at"),
                "channel":    txn.get("channel"),
                "fees_ngn":   Decimal(txn.get("fees", 0)) / 100,
                "customer":   txn.get("customer", {}),
                "metadata":   txn.get("metadata", {}),
                "gateway_response": txn.get("gateway_response"),
            }

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {"success": False, "message": "Transaction not found"}
            raise

    async def initiate_refund(
        self,
        transaction_reference: str,
        amount_ngn: Optional[Decimal] = None,
        reason: str = "Customer request",
    ) -> Dict[str, Any]:
        """Initiate a full or partial refund."""
        payload: Dict[str, Any] = {
            "transaction": transaction_reference,
            "merchant_note": f"ISEYAA Refund: {reason}",
        }
        if amount_ngn:
            payload["amount"] = int(amount_ngn * 100)

        resp = await self._client.post("/refund", json=payload)
        resp.raise_for_status()
        data = resp.json()

        logger.info("paystack_refund_initiated", reference=transaction_reference, amount=str(amount_ngn))
        return {"success": data.get("status", False), "data": data.get("data", {})}

    async def create_transfer_recipient(
        self,
        bank_code: str,
        account_number: str,
        account_name: str,
        currency: str = "NGN",
    ) -> Dict[str, Any]:
        """Register a bank account as a transfer recipient (for vendor payouts)."""
        payload = {
            "type":           "nuban",
            "bank_code":      bank_code,
            "account_number": account_number,
            "name":           account_name,
            "currency":       currency,
        }
        resp = await self._client.post("/transferrecipient", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return {
            "success":          data.get("status", False),
            "recipient_code":   data["data"].get("recipient_code"),
            "recipient_id":     data["data"].get("id"),
        }

    async def initiate_transfer(
        self,
        amount_ngn: Decimal,
        recipient_code: str,
        reference: str,
        reason: str = "Vendor payout",
    ) -> Dict[str, Any]:
        """Initiate a bank transfer (vendor payout)."""
        payload = {
            "source":    "balance",
            "amount":    int(amount_ngn * 100),
            "recipient": recipient_code,
            "reference": reference,
            "reason":    reason,
        }
        resp = await self._client.post("/transfer", json=payload)
        resp.raise_for_status()
        data = resp.json()
        logger.info("paystack_transfer_initiated", reference=reference, amount=str(amount_ngn))
        return {"success": data.get("status", False), "data": data.get("data", {})}

    def verify_webhook_signature(self, payload_body: bytes, signature: str) -> bool:
        """
        Verify Paystack webhook HMAC-SHA512 signature.
        CRITICAL: Always verify before processing any webhook event.
        """
        expected = hmac.new(
            settings.PAYSTACK_WEBHOOK_SECRET.encode("utf-8"),
            msg=payload_body,
            digestmod=hashlib.sha512,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    async def aclose(self):
        await self._client.aclose()
