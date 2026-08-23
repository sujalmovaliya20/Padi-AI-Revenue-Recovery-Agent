"""
Unit test to verify core data schemas (Pydantic & SQLAlchemy) and synthetic dataset compatibility.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.schemas import FailedPayment, AuditLogEntry, FailReason, PaymentStatus, InterventionAction
from app.database import Base
from app.models import FailedPaymentModel, AuditLogEntryModel


def test_pydantic_schemas():
    print("\n--- Testing Pydantic Models ---")
    fp = FailedPayment(
        payment_id="pay_test_001",
        customer_id="cust_test_001",
        customer_name="Aarav Sharma",
        amount=1499.0,
        subscription_id="sub_pro_monthly",
        fail_reason=FailReason.INSUFFICIENT_FUNDS,
        fail_timestamp=datetime.now(timezone.utc),
        retry_count=0,
        status=PaymentStatus.PENDING,
    )
    assert fp.payment_id == "pay_test_001"
    print("  [OK] FailedPayment schema valid")

    audit = AuditLogEntry(
        payment_id="pay_test_001",
        node_name="classify_failure",
        input_snapshot={"amount": 1499.0, "reason": "insufficient_funds"},
        decision="schedule_retry",
        reason="Matched insufficient funds policy for retry after 24 hours",
        tool_called=None,
        tool_result=None,
    )
    assert audit.payment_id == "pay_test_001"
    print("  [OK] AuditLogEntry schema valid")


def test_sqlalchemy_orm():
    print("\n--- Testing SQLAlchemy ORM Models (in-memory SQLite) ---")
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    fp_record = FailedPaymentModel(
        payment_id="pay_test_orm_001",
        customer_id="cust_test_001",
        customer_name="Priya Patel",
        amount=2999.0,
        subscription_id="sub_premium_quarterly",
        fail_reason=FailReason.EXPIRED_CARD,
        fail_timestamp=datetime.now(timezone.utc),
        retry_count=1,
        status=PaymentStatus.IN_PROGRESS,
    )
    session.add(fp_record)
    session.commit()

    # Add audit log
    audit_record = AuditLogEntryModel(
        payment_id="pay_test_orm_001",
        node_name="select_intervention",
        input_snapshot={"fail_reason": "expired_card"},
        decision="switch_payment_method",
        reason="Card expired; customer notified to update billing info.",
    )
    session.add(audit_record)
    session.commit()

    # Query back
    queried_fp = session.query(FailedPaymentModel).filter_by(payment_id="pay_test_orm_001").first()
    assert queried_fp is not None
    assert queried_fp.customer_name == "Priya Patel"
    assert len(queried_fp.audit_logs) == 1
    assert queried_fp.audit_logs[0].decision == "switch_payment_method"
    print("  [OK] SQLAlchemy ORM create, persist, and relationship verified")
    session.close()


def test_synthetic_json_records():
    print("\n--- Testing Generated Synthetic Dataset JSON ---")
    json_path = Path(__file__).resolve().parent.parent / "data" / "synthetic_failed_payments.json"
    assert json_path.exists(), f"File {json_path} does not exist"
    
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert len(data) == 75, f"Expected 75 records, got {len(data)}"
    for item in data:
        # Validate through Pydantic
        FailedPayment(**item)

    print(f"  [OK] Successfully validated all {len(data)} records against Pydantic schema")


if __name__ == "__main__":
    test_pydantic_schemas()
    test_sqlalchemy_orm()
    test_synthetic_json_records()
    print("\n=======================================================")
    print("  ALL DATA SCHEMA & SYNTHETIC DATA TESTS PASSED! [OK]")
    print("=======================================================\n")
