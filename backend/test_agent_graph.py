"""
Test script for the Core LangGraph Revenue Recovery Agent.

Runs 5 distinct sample payments through the graph and prints the full decision trace for each.

Test scenarios:
1. Insufficient Funds (Standard auto-retry later)
2. Expired Card (Payment method update link)
3. Bank Decline (Immediate retry)
4. Mandate Revoked (Compliance hard gate -> Escalate Human)
5. Technical Error (Immediate retry -> Auto-recovered)
6. High-Value Ceiling Check (> ₹5000 -> Gate rejected -> Escalate Human)
"""

import json
import os
import sys
from pathlib import Path

# Set up paths and utf-8 stdout
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from agent.graph import run_recovery_batch
from models.schemas import FailedPayment, FailReason, PaymentStatus


def print_banner(text: str):
    print(f"\n{'=' * 75}")
    print(f"  {text}")
    print(f"{'=' * 75}")


def print_trace(index: int, state: dict):
    payment_id = state.get("payment_id")
    customer = state.get("customer_name")
    amount = state.get("amount")
    category = state.get("fail_category")
    status = state.get("status")
    action = state.get("current_action")
    stop_reason = state.get("stop_reason")
    recovered = state.get("recovered_amount", 0.0)

    print(f"\n[{index}] PAYMENT TRACE: {payment_id} | {customer} | ₹{amount:.2f} INR")
    print(f"    - Category:       {category}")
    print(f"    - Explanation:    {state.get('fail_explanation')}")
    print(f"    - Final Status:   {status.upper()}")
    print(f"    - Final Action:   {action}")
    print(f"    - Stop Reason:    {stop_reason}")
    if recovered > 0:
        print(f"    - Recovered Amt:  ₹{recovered:.2f} INR [RECOVERED]")

    if state.get("promise_to_pay_date"):
        print(f"    - Promise-to-Pay: {state.get('promise_to_pay_date')}")

    print("\n    >>> AUDIT TRAIL / NODE DECISIONS:")
    for step_num, step in enumerate(state.get("intervention_history", []), 1):
        node = step.get("node")
        decision = step.get("decision")
        reason = step.get("reason", "")
        tool = step.get("tool_called")
        tool_res = step.get("tool_result")

        print(f"      Step {step_num} [{node.upper()}]:")
        print(f"        Decision: {decision}")
        if reason:
            print(f"        Reason:   {reason}")
        if tool:
            print(f"        Tool:     {tool}")
            print(f"        Result:   {json.dumps(tool_res)}")

    print(f"    {'-' * 65}")


def main():
    print_banner("RUNNING REVENUE RECOVERY AGENT — 5 SAMPLE TRACES")

    # Construct 5 realistic test payments with varied root causes & amounts
    test_payments = [
        # 1. Insufficient funds
        {
            "payment_id": "pay_test_insufficient_001",
            "customer_id": "cust_in_50101",
            "customer_name": "Aarav Sharma",
            "amount": 999.00,
            "subscription_id": "sub_pro_monthly_101",
            "fail_reason": "insufficient_funds",
            "fail_timestamp": "2026-08-22T10:00:00Z",
            "retry_count": 0,
            "status": "pending",
        },
        # 2. Expired card (with Kapoor promise-to-pay trigger simulation)
        {
            "payment_id": "pay_test_expired_002",
            "customer_id": "cust_in_50102",
            "customer_name": "Rohan Kapoor",
            "amount": 1499.00,
            "subscription_id": "sub_growth_monthly_102",
            "fail_reason": "expired_card",
            "fail_timestamp": "2026-08-21T14:30:00Z",
            "retry_count": 0,
            "status": "pending",
        },
        # 3. Bank decline
        {
            "payment_id": "pay_test_decline_003",
            "customer_id": "cust_in_50103",
            "customer_name": "Priya Menon",
            "amount": 499.00,
            "subscription_id": "sub_basic_monthly_103",
            "fail_reason": "bank_decline",
            "fail_timestamp": "2026-08-23T04:15:00Z",
            "retry_count": 0,
            "status": "pending",
        },
        # 4. Mandate revoked (Compliance hard gate)
        {
            "payment_id": "pay_test_revoked_004",
            "customer_id": "cust_in_50104",
            "customer_name": "Siddharth Verma",
            "amount": 2999.00,
            "subscription_id": "sub_premium_quarterly_104",
            "fail_reason": "mandate_revoked",
            "fail_timestamp": "2026-08-20T08:00:00Z",
            "retry_count": 0,
            "status": "pending",
        },
        # 5. Technical error (Transitory -> immediate retry -> recovered)
        {
            "payment_id": "pay_test_tech_005",
            "customer_id": "cust_in_50105",
            "customer_name": "Ananya Iyer",
            "amount": 799.00,
            "subscription_id": "sub_standard_monthly_105",
            "fail_reason": "technical_error",
            "fail_timestamp": "2026-08-23T06:45:00Z",
            "retry_count": 0,
            "status": "pending",
        },
        # 6. High-value safety ceiling check (> ₹5000)
        {
            "payment_id": "pay_test_highval_006",
            "customer_id": "cust_in_50106",
            "customer_name": "Vikram Malhotra",
            "amount": 8999.00,
            "subscription_id": "sub_enterprise_annual_106",
            "fail_reason": "bank_decline",
            "fail_timestamp": "2026-08-22T12:00:00Z",
            "retry_count": 0,
            "status": "pending",
        },
    ]

    print(f" Executing {len(test_payments)} payments through LangGraph state machine...")
    final_states = run_recovery_batch(test_payments)

    for idx, state in enumerate(final_states, 1):
        print_trace(idx, state)

    print_banner("ALL RECOVERY GRAPH TRACES EXECUTED SUCCESSFULLY [OK]")


if __name__ == "__main__":
    main()
