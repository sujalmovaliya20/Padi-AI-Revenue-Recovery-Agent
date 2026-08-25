"""
Razorpay Tool Functions for Revenue Recovery Agent.

Tools:
1. retry_charge(payment_id, amount, ...) — Attempt to recreate/retry payment via Razorpay Orders/Payments API in test mode.
2. send_payment_link(customer_id, amount, reason, ...) — Create a Razorpay Payment Link and simulate dispatch.
3. check_mandate_status(subscription_id) — Query Razorpay Subscriptions API for mandate status.

Includes controlled failure injection mode for Resilience Testing:
- API_TIMEOUT (Simulate hanging gateway / 30s timeout)
- RATE_LIMIT (Simulate HTTP 429 rate limit exceeded)
- INVALID_ORDER (Simulate HTTP 400 bad request / invalid order ID)
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any, Dict, Optional

# Path setup for config
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
REPO_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "../.."))
for p in [BACKEND_DIR, REPO_ROOT]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    import razorpay
    from razorpay.errors import BadRequestError, GatewayError, ServerError, SignatureVerificationError
except ImportError:
    razorpay = None
    BadRequestError = GatewayError = ServerError = SignatureVerificationError = Exception

try:
    from app.config import get_settings
except ImportError:
    from backend.app.config import get_settings

logger = logging.getLogger(__name__)


# ── Custom Exceptions for Resilience Testing ────────────────────────

class RazorpayAPIError(Exception):
    """Base exception for Razorpay tool execution errors."""
    pass


class RazorpayTimeoutError(RazorpayAPIError):
    """Simulated or real gateway connection timeout error."""
    pass


class RazorpayRateLimitError(RazorpayAPIError):
    """Simulated or real HTTP 429 Too Many Requests error."""
    pass


class RazorpayInvalidOrderError(RazorpayAPIError):
    """Simulated or real HTTP 400 Bad Request / Invalid Order error."""
    pass


# Global Controlled Failure Injection State
_FAILURE_INJECTION_MODE: Optional[str] = None
_INJECTION_COUNT: int = 0


def inject_failure(failure_type: Optional[str] = None) -> None:
    """
    Configure or clear the failure injection mode for resilience testing.
    Supported types: 'API_TIMEOUT', 'RATE_LIMIT', 'INVALID_ORDER', or None to reset.
    """
    global _FAILURE_INJECTION_MODE, _INJECTION_COUNT
    _FAILURE_INJECTION_MODE = failure_type
    _INJECTION_COUNT = 0
    logger.info("Controlled failure injection mode set to: %s", failure_type)


def get_injected_failure() -> Optional[str]:
    """Return active failure injection type if any."""
    return _FAILURE_INJECTION_MODE or os.getenv("INJECT_FAILURE", None)


def check_and_raise_injected_failure():
    """Evaluate if an injected failure should be raised for the current call."""
    global _INJECTION_COUNT
    failure = get_injected_failure()
    if not failure:
        return

    _INJECTION_COUNT += 1
    if failure == "API_TIMEOUT":
        raise RazorpayTimeoutError("Gateway connection timed out after 30000ms: api.razorpay.com unreachable")
    elif failure == "RATE_LIMIT":
        raise RazorpayRateLimitError("HTTP 429: Too Many Requests: Rate limit quota exceeded for merchant key")
    elif failure == "INVALID_ORDER":
        raise RazorpayInvalidOrderError("HTTP 400: BAD_REQUEST_ERROR: Order ID 'order_invalid_999' does not exist or has expired")


def get_razorpay_client() -> Optional[Any]:
    """
    Instantiate and return Razorpay client using configured credentials.
    Returns None if razorpay package is missing or credentials not provided.
    """
    if razorpay is None:
        logger.warning("Razorpay Python SDK not installed.")
        return None

    settings = get_settings()
    key_id = settings.RAZORPAY_KEY_ID or os.getenv("RAZORPAY_KEY_ID", "")
    key_secret = settings.RAZORPAY_KEY_SECRET or os.getenv("RAZORPAY_KEY_SECRET", "")

    if not key_id or not key_secret:
        return None

    client = razorpay.Client(auth=(key_id, key_secret))
    try:
        client.set_app_details({"title": "Revenue Recovery Agent", "version": "0.1.0"})
    except Exception:
        pass
    return client


def is_live_test_mode_configured() -> bool:
    """Check if valid non-placeholder Razorpay test keys are present."""
    settings = get_settings()
    key_id = settings.RAZORPAY_KEY_ID or os.getenv("RAZORPAY_KEY_ID", "")
    key_secret = settings.RAZORPAY_KEY_SECRET or os.getenv("RAZORPAY_KEY_SECRET", "")

    if not key_id or not key_secret:
        return False
    if "xxxxxxxx" in key_id or "your_razorpay" in key_secret:
        return False
    return True


# ── Tool 1: retry_charge ──────────────────────────────────────────

def retry_charge(
    payment_id: str,
    amount: float,
    customer_id: Optional[str] = None,
    order_id: Optional[str] = None,
    notes: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Attempt to recreate/retry a payment via Razorpay Orders/Payments API in test mode.
    
    Creates a real Razorpay Order (amount in paise = amount * 100) linked to the
    receipt/payment_id so a retry transaction can be authorized or tracked.
    """
    # Check failure injection hook first
    check_and_raise_injected_failure()

    client = get_razorpay_client()
    amount_in_paise = int(round(amount * 100))
    receipt_id = f"rcpt_{payment_id[-20:]}" if len(payment_id) > 20 else payment_id

    order_notes = {
        "payment_id": payment_id,
        "customer_id": customer_id or "unknown",
        "agent": "AI_Revenue_Recovery",
        **(notes or {}),
    }

    if client is not None and is_live_test_mode_configured():
        try:
            logger.info("Executing Razorpay order.create for payment %s (₹%.2f)", payment_id, amount)
            order_payload = {
                "amount": amount_in_paise,
                "currency": "INR",
                "receipt": receipt_id,
                "notes": order_notes,
                "payment_capture": 1,
            }
            order = client.order.create(data=order_payload)

            return {
                "status": "order_created",
                "success": True,
                "razorpay_order_id": order.get("id"),
                "amount": amount,
                "amount_paid": order.get("amount_paid", 0) / 100.0,
                "amount_due": order.get("amount_due", 0) / 100.0,
                "currency": order.get("currency", "INR"),
                "receipt": order.get("receipt"),
                "order_status": order.get("status"),
                "created_at": order.get("created_at"),
                "raw_response": order,
                "message": f"Real Razorpay test Order '{order.get('id')}' provisioned for retry attempt.",
            }
        except Exception as e:
            logger.error("Razorpay order.create API error for %s: %s", payment_id, e)
            return {
                "status": "api_error",
                "success": False,
                "error": str(e),
                "payment_id": payment_id,
                "amount": amount,
                "message": f"Razorpay API call failed: {e}",
            }
    else:
        # Test-mode adapter fallback when keys are placeholder
        mock_order_id = f"order_test_{payment_id[-10:]}"
        return {
            "status": "order_created",
            "success": True,
            "razorpay_order_id": mock_order_id,
            "amount": amount,
            "amount_due": amount,
            "currency": "INR",
            "receipt": receipt_id,
            "order_status": "created",
            "message": f"Test-mode Order '{mock_order_id}' created for payment retry (₹{amount:.2f} INR).",
            "adapter_mode": "test_simulation",
        }


# ── Tool 2: send_payment_link ─────────────────────────────────────

def send_payment_link(
    customer_id: str,
    amount: float,
    reason: str,
    payment_id: Optional[str] = None,
    customer_name: Optional[str] = None,
    customer_email: Optional[str] = None,
    customer_contact: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a Razorpay Payment Link and simulate dispatching it.
    
    Generates an authentic payment link via Razorpay Payment Links API in test mode.
    Disables real SMS/Email sending in test mode while logging the real payment URL.
    """
    # Check failure injection hook first
    check_and_raise_injected_failure()

    client = get_razorpay_client()
    amount_in_paise = int(round(amount * 100))
    desc = f"Update subscription payment: {reason[:80]}" if reason else "Subscription Mandate Payment Update"

    customer_info = {
        "name": customer_name or "Valued Customer",
        "email": customer_email or f"{customer_id}@example.com",
        "contact": customer_contact or "+919876543210",
    }

    if client is not None and is_live_test_mode_configured():
        try:
            logger.info("Executing Razorpay payment_link.create for customer %s (₹%.2f)", customer_id, amount)
            link_payload = {
                "amount": amount_in_paise,
                "currency": "INR",
                "accept_partial": False,
                "description": desc,
                "customer": customer_info,
                "notify": {"sms": False, "email": False},  # Do not spam real notifications during test
                "reminder_enable": False,
                "notes": {
                    "customer_id": customer_id,
                    "payment_id": payment_id or "",
                    "source": "AI_Revenue_Recovery_Agent",
                },
            }
            link = client.payment_link.create(data=link_payload)

            return {
                "status": "link_created",
                "success": True,
                "payment_link_id": link.get("id"),
                "short_url": link.get("short_url"),
                "amount": amount,
                "currency": link.get("currency", "INR"),
                "link_status": link.get("status"),
                "description": link.get("description"),
                "customer": customer_info,
                "raw_response": link,
                "message": f"Real Razorpay payment link created: {link.get('short_url')}",
            }
        except Exception as e:
            logger.error("Razorpay payment_link.create API error for customer %s: %s", customer_id, e)
            return {
                "status": "api_error",
                "success": False,
                "error": str(e),
                "customer_id": customer_id,
                "amount": amount,
                "message": f"Razorpay Payment Link API failed: {e}",
            }
    else:
        # Test-mode adapter fallback
        mock_link_id = f"plink_test_{customer_id[-6:]}"
        mock_short_url = f"https://rzp.io/i/{mock_link_id}"
        return {
            "status": "link_created",
            "success": True,
            "payment_link_id": mock_link_id,
            "short_url": mock_short_url,
            "amount": amount,
            "currency": "INR",
            "link_status": "created",
            "customer": customer_info,
            "message": f"Test-mode payment link generated: {mock_short_url}",
            "adapter_mode": "test_simulation",
        }


# ── Tool 3: check_mandate_status ──────────────────────────────────

def check_mandate_status(subscription_id: str) -> Dict[str, Any]:
    """
    Query Razorpay Subscriptions API for mandate status.
    """
    # Check failure injection hook first
    check_and_raise_injected_failure()

    client = get_razorpay_client()

    if client is not None and is_live_test_mode_configured():
        try:
            logger.info("Executing Razorpay subscription.fetch for %s", subscription_id)
            sub = client.subscription.fetch(subscription_id)
            return {
                "status": "success",
                "success": True,
                "subscription_id": sub.get("id"),
                "plan_id": sub.get("plan_id"),
                "mandate_status": sub.get("status"),
                "current_start": sub.get("current_start"),
                "current_end": sub.get("current_end"),
                "charge_at": sub.get("charge_at"),
                "raw_response": sub,
                "message": f"Subscription '{subscription_id}' status is '{sub.get('status')}'.",
            }
        except Exception as e:
            logger.warning("Razorpay subscription.fetch API error for %s: %s", subscription_id, e)
            return {
                "status": "not_found_or_error",
                "success": False,
                "subscription_id": subscription_id,
                "error": str(e),
                "message": f"Mandate status query returned: {e}",
            }
    else:
        # Test-mode adapter fallback
        return {
            "status": "active",
            "success": True,
            "subscription_id": subscription_id,
            "mandate_status": "active",
            "message": f"Test-mode mandate for subscription '{subscription_id}' is active.",
            "adapter_mode": "test_simulation",
        }
