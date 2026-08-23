"""
Pydantic v2 schemas for the recovery agent pipeline and core domain models.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

# Re-export core models
try:
    from models.schemas import (
        FailReason,
        PaymentStatus,
        InterventionAction,
        FailedPayment,
        AuditLogEntry,
    )
except ImportError:
    from backend.models.schemas import (
        FailReason,
        PaymentStatus,
        InterventionAction,
        FailedPayment,
        AuditLogEntry,
    )


# ── Failure classification (Agent Pipeline) ──────────────────────────

class FailureCategory(str, Enum):
    """Root-cause categories for a failed payment."""
    INSUFFICIENT_FUNDS = "insufficient_funds"
    EXPIRED_CARD = "expired_card"
    BANK_DECLINE = "bank_decline"
    NETWORK_ERROR = "network_error"
    AUTHENTICATION_FAILED = "authentication_failed"
    MANDATE_REVOKED = "mandate_revoked"
    ACCOUNT_CLOSED = "account_closed"
    TECHNICAL_ERROR = "technical_error"
    UNKNOWN = "unknown"


class FailureClassification(BaseModel):
    """LLM-produced classification of a payment failure."""
    category: FailureCategory = Field(
        description="Root-cause category for the failure"
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Model confidence in the classification (0–1)"
    )
    reasoning: str = Field(
        description="Brief explanation of why this category was chosen"
    )


# ── Intervention selection (Agent Pipeline) ──────────────────────────

class InterventionType(str, Enum):
    """Bounded recovery actions the agent may take."""
    RETRY_NOW = "retry_now"
    RETRY_LATER = "retry_later"
    SWITCH_PAYMENT_METHOD = "switch_payment_method"
    ESCALATE_HUMAN = "escalate_human"
    STOP_NO_ACTION = "stop_no_action"
    # Backwards compatibility aliases
    RETRY_PAYMENT = "retry_now"
    SEND_REMINDER = "retry_later"
    UPDATE_PAYMENT_METHOD = "switch_payment_method"
    ESCALATE_TO_SUPPORT = "escalate_human"
    SCHEDULE_RETRY = "retry_later"
    NO_ACTION = "stop_no_action"


class InterventionDecision(BaseModel):
    """LLM-produced intervention recommendation."""
    action: InterventionAction = Field(
        description="Recommended bounded recovery action"
    )
    priority: int = Field(
        ge=1, le=5,
        description="Priority level (1 = highest, 5 = lowest)"
    )
    reasoning: str = Field(
        description="Brief explanation of why this action was chosen"
    )
    estimated_success_rate: float = Field(
        ge=0.0, le=1.0,
        description="Estimated probability of successful recovery (0–1)"
    )


# ── Agent State I/O DTOs ─────────────────────────────────────────────

class PaymentFailureInput(BaseModel):
    """Input payload describing a failed payment for the agent graph."""
    payment_id: str
    customer_id: str
    amount: float
    currency: str = "INR"
    error_code: str
    error_description: str
    retry_count: int = 0
    payment_method: str = "mandate"


class RecoveryResult(BaseModel):
    """Final output of the recovery agent pipeline."""
    payment_id: str
    classification: FailureClassification
    intervention: InterventionDecision


__all__ = [
    "FailReason",
    "PaymentStatus",
    "InterventionAction",
    "FailedPayment",
    "AuditLogEntry",
    "FailureCategory",
    "FailureClassification",
    "InterventionType",
    "InterventionDecision",
    "PaymentFailureInput",
    "RecoveryResult",
]
