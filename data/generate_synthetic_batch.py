"""
Synthetic dataset generator for Revenue Recovery Agent.

Generates realistic failed subscription & mandate payment records for India-focused SaaS/OTT.
Features:
- Exact categorical distribution:
    - 40% insufficient_funds
    - 20% expired_card
    - 15% bank_decline
    - 15% mandate_revoked
    - 10% technical_error
- Realistic Indian customer names and tier amounts (₹299 – ₹4999)
- Staggered timestamps over the past 14 days
- Exports to JSON and provides `insert_into_postgres()` for database persistence

Usage:
    python generate_synthetic_batch.py --count 75 --output synthetic_failed_payments.json
    python generate_synthetic_batch.py --count 75 --insert-db
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

# Add repository root and backend directory to sys.path to import schemas & models
REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
for p in [str(REPO_ROOT), str(BACKEND_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

try:
    from models.schemas import FailedPayment, FailReason, PaymentStatus
except ImportError:
    try:
        from backend.models.schemas import FailedPayment, FailReason, PaymentStatus
    except ImportError:
        from app.schemas import FailedPayment, FailReason, PaymentStatus


# ── Seed Data Pools ───────────────────────────────────────────────

FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Reyansh", "Arnav", "Ayaan",
    "Krishna", "Ishaan", "Shaurya", "Atharva", "Advik", "Pranav", "Advaith",
    "Dhruv", "Kabir", "Ananya", "Diya", "Saanvi", "Aadhya", "Pari", "Anika",
    "Navya", "Myra", "Sara", "Isha", "Riya", "Pooja", "Priya", "Sneha", "Kavya",
    "Deepika", "Shreya", "Meera", "Neha", "Rohan", "Vikram", "Rahul", "Karan",
    "Sujal", "Nikhil", "Amit", "Manish", "Rajesh", "Suresh", "Tanvi", "Siddharth",
    "Gaurav", "Harsh", "Varun", "Abhishek", "Deepak", "Ankush", "Swati", "Nandini"
]

LAST_NAMES = [
    "Sharma", "Verma", "Patel", "Mehta", "Iyer", "Nair", "Reddy", "Rao",
    "Gupta", "Singh", "Kumar", "Chopra", "Deshmukh", "Joshi", "Bose",
    "Banerjee", "Chatterjee", "Mishra", "Pandey", "Saxena", "Kapoor",
    "Malhotra", "Kulkarni", "Bhat", "Menon", "Pillai", "Agarwal", "Bansal",
    "Singhania", "Movaliya", "Chauhan", "Yadav", "Trivedi"
]

SUBSCRIPTION_PLANS = [
    ("sub_starter_monthly", 299.00),
    ("sub_basic_monthly", 499.00),
    ("sub_standard_monthly", 799.00),
    ("sub_pro_monthly", 999.00),
    ("sub_growth_monthly", 1499.00),
    ("sub_business_monthly", 1999.00),
    ("sub_scale_monthly", 2499.00),
    ("sub_premium_quarterly", 2999.00),
    ("sub_enterprise_team", 3999.00),
    ("sub_executive_annual", 4999.00),
]

# Exact distribution percentages specified by user:
# 40% insufficient_funds, 20% expired_card, 15% bank_decline, 15% mandate_revoked, 10% technical_error
CATEGORY_DISTRIBUTION = [
    (FailReason.INSUFFICIENT_FUNDS, 0.40),
    (FailReason.EXPIRED_CARD, 0.20),
    (FailReason.BANK_DECLINE, 0.15),
    (FailReason.MANDATE_REVOKED, 0.15),
    (FailReason.TECHNICAL_ERROR, 0.10),
]


def generate_customer_name(used_names: set[str]) -> str:
    """Generate a unique realistic Indian customer name."""
    for _ in range(100):
        name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        if name not in used_names:
            used_names.add(name)
            return name
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)} {random.randint(10, 99)}"


def generate_synthetic_payments(count: int = 75, seed: int = 42) -> List[Dict[str, Any]]:
    """
    Generate a list of synthetic failed payment dictionaries matching the requested distribution.
    """
    random.seed(seed)
    used_names: set[str] = set()

    # Calculate exact counts per category
    # For count = 75:
    # insufficient_funds: round(75 * 0.40) = 30
    # expired_card:       round(75 * 0.20) = 15
    # bank_decline:       round(75 * 0.15) = 11
    # mandate_revoked:    round(75 * 0.15) = 11
    # technical_error:    75 - (30+15+11+11) = 8
    target_counts = {}
    allocated = 0
    for reason, weight in CATEGORY_DISTRIBUTION[:-1]:
        c = int(round(count * weight))
        target_counts[reason] = c
        allocated += c
    target_counts[CATEGORY_DISTRIBUTION[-1][0]] = count - allocated

    category_pool: List[FailReason] = []
    for reason, c in target_counts.items():
        category_pool.extend([reason] * c)

    random.shuffle(category_pool)

    now = datetime.now(timezone.utc)
    records: List[Dict[str, Any]] = []

    for i, reason in enumerate(category_pool, start=1):
        plan_id, base_price = random.choice(SUBSCRIPTION_PLANS)
        
        # Stagger timestamp over the past 14 days (1 to 336 hours ago)
        # Uniformly distributed with slight random jitter
        hours_ago = (i / count) * 14 * 24 + random.uniform(-6, 6)
        hours_ago = max(0.5, min(336.0, hours_ago))
        fail_time = now - timedelta(hours=hours_ago)

        # Retry count: higher for older failures, 0-1 for recent
        max_retries = min(3, int(hours_ago // 72))
        retry_count = random.randint(0, max_retries)

        # Status: most recent are pending, some in_progress
        if hours_ago < 24:
            status = PaymentStatus.PENDING
        elif hours_ago < 72 and retry_count > 0:
            status = random.choice([PaymentStatus.PENDING, PaymentStatus.IN_PROGRESS])
        else:
            status = random.choice([PaymentStatus.PENDING, PaymentStatus.IN_PROGRESS, PaymentStatus.ESCALATED])

        payment_data = {
            "payment_id": f"pay_syn_{fail_time.strftime('%m%d')}_{1000 + i}",
            "customer_id": f"cust_in_{50000 + i}",
            "customer_name": generate_customer_name(used_names),
            "amount": float(base_price),
            "subscription_id": f"{plan_id}_{100 + i}",
            "fail_reason": reason.value,
            "fail_timestamp": fail_time.isoformat(),
            "retry_count": retry_count,
            "status": status.value,
        }

        # Validate with Pydantic model to guarantee compliance
        validated = FailedPayment(**payment_data)
        records.append(validated.model_dump(mode="json"))

    # Sort chronologically by fail_timestamp descending (newest first)
    records.sort(key=lambda r: r["fail_timestamp"], reverse=True)
    return records


def insert_into_postgres(records: List[Dict[str, Any]]) -> int:
    """
    Insert or upsert generated synthetic payment records directly into PostgreSQL.
    Returns the number of records inserted/updated.
    """
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from app.database import SessionLocal, init_db
    from app.models import FailedPaymentModel

    # Ensure tables exist
    init_db()

    db = SessionLocal()
    inserted_count = 0
    try:
        for r in records:
            # Parse datetime string into datetime object if needed
            ts = datetime.fromisoformat(r["fail_timestamp"]) if isinstance(r["fail_timestamp"], str) else r["fail_timestamp"]

            stmt = pg_insert(FailedPaymentModel).values(
                payment_id=r["payment_id"],
                customer_id=r["customer_id"],
                customer_name=r["customer_name"],
                amount=r["amount"],
                subscription_id=r["subscription_id"],
                fail_reason=FailReason(r["fail_reason"]),
                fail_timestamp=ts,
                retry_count=r["retry_count"],
                status=PaymentStatus(r["status"]),
            )
            # Upsert on conflict
            stmt = stmt.on_conflict_do_update(
                index_elements=["payment_id"],
                set_={
                    "status": stmt.excluded.status,
                    "retry_count": stmt.excluded.retry_count,
                    "amount": stmt.excluded.amount,
                },
            )
            db.execute(stmt)
            inserted_count += 1
        db.commit()
    except Exception as e:
        db.rollback()
        raise RuntimeError(f"Database insertion failed: {e}") from e
    finally:
        db.close()

    return inserted_count


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic failed payment dataset.")
    parser.add_argument("--count", type=int, default=75, help="Number of records to generate (default: 75)")
    parser.add_argument(
        "--output",
        type=str,
        default=str(Path(__file__).resolve().parent / "synthetic_failed_payments.json"),
        help="Path for output JSON file",
    )
    parser.add_argument("--insert-db", action="store_true", help="Insert records directly into PostgreSQL")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    args = parser.parse_args()

    print(f"\n Generating {args.count} synthetic failed payments (seed={args.seed})...")
    records = generate_synthetic_payments(count=args.count, seed=args.seed)

    # Calculate distribution breakdown
    counts: Dict[str, int] = {}
    for r in records:
        counts[r["fail_reason"]] = counts.get(r["fail_reason"], 0) + 1

    print("\n--- Distribution Breakdown ---")
    for reason, c in sorted(counts.items(), key=lambda x: x[1], reverse=True):
        pct = (c / len(records)) * 100
        print(f"  - {reason:<22}: {c:>2} records ({pct:5.1f}%)")

    # Write JSON output
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

    print(f"\n Successfully saved {len(records)} records to {out_path}")

    # Optional DB insert
    if args.insert_db:
        print("\n Connecting to PostgreSQL and inserting records...")
        try:
            inserted = insert_into_postgres(records)
            print(f" Inserted/Upserted {inserted} records into table 'failed_payments' [OK]")
        except Exception as e:
            print(f" Note: Database insert failed (PostgreSQL may be offline): {e}")

    # Show preview of first 5 records
    print("\n--- Sample Records Preview (First 5 of 75) ---")
    for i, r in enumerate(records[:5], 1):
        print(f"\n[{i}] Payment ID: {r['payment_id']}")
        print(f"    Customer:     {r['customer_name']} ({r['customer_id']})")
        print(f"    Amount:       ₹{r['amount']:.2f} INR")
        print(f"    Subscription: {r['subscription_id']}")
        print(f"    Reason:       {r['fail_reason']}")
        print(f"    Timestamp:    {r['fail_timestamp']}")
        print(f"    Status:       {r['status']} (retries: {r['retry_count']})")


if __name__ == "__main__":
    main()
