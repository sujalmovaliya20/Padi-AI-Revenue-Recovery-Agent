"""
SQLAlchemy ORM models for PostgreSQL persistence.

Tables:
- failed_payments: Stores failed subscription/mandate payments
- audit_logs: Stores agent execution steps and audit trail
"""

from __future__ import annotations

from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    DateTime,
    Text,
    JSON,
    ForeignKey,
    Enum as SQLEnum,
    func,
)
from sqlalchemy.orm import relationship

from app.database import Base
try:
    from models.schemas import FailReason, PaymentStatus
except ImportError:
    from backend.models.schemas import FailReason, PaymentStatus


class FailedPaymentModel(Base):
    """SQLAlchemy model for failed payments."""
    __tablename__ = "failed_payments"

    payment_id = Column(String(64), primary_key=True, index=True)
    customer_id = Column(String(64), nullable=False, index=True)
    customer_name = Column(String(255), nullable=False)
    amount = Column(Float, nullable=False)
    subscription_id = Column(String(64), nullable=False, index=True)
    fail_reason = Column(
        SQLEnum(FailReason, name="fail_reason_enum", native_enum=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True,
    )
    fail_timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    retry_count = Column(Integer, default=0, nullable=False)
    status = Column(
        SQLEnum(PaymentStatus, name="payment_status_enum", native_enum=False, values_callable=lambda x: [e.value for e in x]),
        default=PaymentStatus.PENDING,
        nullable=False,
        index=True,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    audit_logs = relationship(
        "AuditLogEntryModel",
        back_populates="failed_payment",
        cascade="all, delete-orphan",
        order_by="AuditLogEntryModel.timestamp",
    )

    def __repr__(self) -> str:
        return f"<FailedPayment(id={self.payment_id}, customer={self.customer_name}, amount={self.amount}, status={self.status})>"


class AuditLogEntryModel(Base):
    """SQLAlchemy model for agent step audit log entries."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    payment_id = Column(
        String(64),
        ForeignKey("failed_payments.payment_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    node_name = Column(String(100), nullable=False, index=True)
    input_snapshot = Column(JSON, nullable=False, default=dict)
    decision = Column(String(255), nullable=False)
    reason = Column(Text, nullable=False)
    tool_called = Column(String(255), nullable=True)
    tool_result = Column(JSON, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # Relationships
    failed_payment = relationship("FailedPaymentModel", back_populates="audit_logs")

    def __repr__(self) -> str:
        return f"<AuditLogEntry(id={self.id}, payment_id={self.payment_id}, node={self.node_name}, decision={self.decision})>"
