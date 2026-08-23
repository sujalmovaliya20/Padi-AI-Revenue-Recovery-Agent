"""
Setup script to provision test-mode Razorpay Orders for synthetic payment records.

Maps each synthetic payment_id to a real Razorpay test-mode Order so retry actions
and recovery tools have concrete orders to act upon.

Usage:
    python data/create_test_orders.py [--limit 75]
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Add backend directory and repo root to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
for p in [str(REPO_ROOT), str(BACKEND_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

try:
    from tools.razorpay_tools import (
        get_razorpay_client,
        is_live_test_mode_configured,
        retry_charge,
    )
except ImportError:
    from backend.tools.razorpay_tools import (
        get_razorpay_client,
        is_live_test_mode_configured,
        retry_charge,
    )


def create_test_orders(
    input_file: str,
    output_file: str,
    limit: int = 75,
) -> dict:
    """
    Load synthetic failed payments, create corresponding Razorpay test Orders,
    and save the order_id <-> payment_id mapping.
    """
    inp_path = Path(input_file)
    if not inp_path.exists():
        raise FileNotFoundError(f"Input file {input_file} not found. Run generate_synthetic_batch.py first.")

    with open(inp_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    records = records[:limit]
    is_live = is_live_test_mode_configured()
    print(f"\n[RAZORPAY ADAPTER] Mode: {'LIVE TEST API' if is_live else 'TEST SIMULATION (Configure RAZORPAY_KEY_ID in .env for live API)'}")
    print(f"Processing {len(records)} payments from {inp_path.name}...\n")

    mappings = {}
    created_list = []

    for i, item in enumerate(records, 1):
        payment_id = item["payment_id"]
        amount = float(item["amount"])
        customer_id = item["customer_id"]
        customer_name = item.get("customer_name", "Valued Customer")

        # Execute retry_charge tool to create or simulate real order
        result = retry_charge(
            payment_id=payment_id,
            amount=amount,
            customer_id=customer_id,
            notes={"customer_name": customer_name, "subscription_id": item.get("subscription_id")},
        )

        order_id = result.get("razorpay_order_id", f"order_test_{payment_id[-10:]}")
        order_entry = {
            "payment_id": payment_id,
            "razorpay_order_id": order_id,
            "amount": amount,
            "amount_in_paise": int(round(amount * 100)),
            "currency": "INR",
            "customer_id": customer_id,
            "customer_name": customer_name,
            "fail_reason": item.get("fail_reason"),
            "status": result.get("order_status", "created"),
            "message": result.get("message"),
        }

        mappings[payment_id] = order_entry
        created_list.append(order_entry)

        if i <= 5 or i % 25 == 0 or i == len(records):
            print(f"  [{i:>2}/{len(records)}] {payment_id} -> {order_id} (₹{amount:.2f} INR) [{order_entry['status']}]")

    out_path = Path(output_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(mappings, f, indent=2, ensure_ascii=False)

    print(f"\n[OK] Successfully saved {len(mappings)} Razorpay order mappings to {out_path.resolve()}\n")
    return mappings


def main():
    parser = argparse.ArgumentParser(description="Create Razorpay test-mode orders for synthetic failed payments.")
    parser.add_argument(
        "--input",
        type=str,
        default=str(Path(__file__).resolve().parent / "synthetic_failed_payments.json"),
        help="Input synthetic payments JSON",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=str(Path(__file__).resolve().parent / "razorpay_order_mappings.json"),
        help="Output mappings JSON file",
    )
    parser.add_argument("--limit", type=int, default=75, help="Number of records to provision (default: 75)")
    args = parser.parse_args()

    create_test_orders(input_file=args.input, output_file=args.output, limit=args.limit)


if __name__ == "__main__":
    main()
