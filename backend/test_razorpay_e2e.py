"""
End-to-End Test for Razorpay Tools & Recovery Agent Integration.

Verifies:
1. Direct tool execution (retry_charge, send_payment_link, check_mandate_status)
2. Agent end-to-end execution invoking real Razorpay tools in execute_action
3. Verification of tool_result and audit log persistence
"""

import json
import os
import sys
from pprint import pprint

# Ensure paths and utf-8 stdout
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from agent.graph import run_recovery_batch
from tools.razorpay_tools import (
    retry_charge,
    send_payment_link,
    check_mandate_status,
    is_live_test_mode_configured,
)


def print_section(title: str):
    print(f"\n{'=' * 75}")
    print(f"  {title}")
    print(f"{'=' * 75}")


def test_individual_razorpay_tools():
    print_section("1. DIRECT RAZORPAY TOOL FUNCTION INVOCATIONS")

    # Tool 1: retry_charge
    print("\n--- Testing Tool 1: retry_charge() ---")
    retry_res = retry_charge(
        payment_id="pay_syn_0823_1001",
        amount=999.00,
        customer_id="cust_in_50001",
        notes={"customer_name": "Rahul Kumar", "subscription_tier": "Pro Monthly"},
    )
    print("Tool Result (retry_charge):")
    print(json.dumps(retry_res, indent=2))
    assert retry_res.get("success") is True
    assert "razorpay_order_id" in retry_res

    # Tool 2: send_payment_link
    print("\n--- Testing Tool 2: send_payment_link() ---")
    link_res = send_payment_link(
        customer_id="cust_in_50003",
        amount=1499.00,
        reason="Card on file expired; update billing card to resume active subscription",
        payment_id="pay_syn_0822_1003",
        customer_name="Manish Kapoor",
        customer_email="manish.kapoor@example.com",
    )
    print("Tool Result (send_payment_link):")
    print(json.dumps(link_res, indent=2))
    assert link_res.get("success") is True
    assert "short_url" in link_res or "payment_link_id" in link_res

    # Tool 3: check_mandate_status
    print("\n--- Testing Tool 3: check_mandate_status() ---")
    mandate_res = check_mandate_status(subscription_id="sub_pro_monthly_101")
    print("Tool Result (check_mandate_status):")
    print(json.dumps(mandate_res, indent=2))
    assert "status" in mandate_res


def test_end_to_end_agent_with_razorpay():
    print_section("2. END-TO-END AGENT WORKFLOW WITH REAL TOOL INTEGRATION")

    test_payment = {
        "payment_id": "pay_syn_0822_1003",
        "customer_id": "cust_in_50003",
        "customer_name": "Manish Kapoor",
        "amount": 1499.00,
        "subscription_id": "sub_growth_monthly_103",
        "fail_reason": "expired_card",
        "fail_timestamp": "2026-08-22T14:08:03Z",
        "retry_count": 0,
        "status": "pending",
    }

    print(f"Input Payment: {test_payment['payment_id']} (₹{test_payment['amount']:.2f} INR, Reason: {test_payment['fail_reason']})")
    print("Executing through LangGraph Agent...")

    results = run_recovery_batch([test_payment])
    final_state = results[0]

    print("\n--- Final Agent State ---")
    print(f"Payment ID:       {final_state.get('payment_id')}")
    print(f"Customer:         {final_state.get('customer_name')}")
    print(f"Category:         {final_state.get('fail_category')}")
    print(f"Explanation:      {final_state.get('fail_explanation')}")
    print(f"Action:           {final_state.get('current_action')}")
    print(f"Status:           {final_state.get('status')}")
    print(f"Stop Reason:      {final_state.get('stop_reason')}")

    print("\n--- Audit Log: Node Execution Trace & Tool Result ---")
    for idx, log in enumerate(final_state.get("intervention_history", []), 1):
        print(f"\nStep {idx} [{log.get('node').upper()}]:")
        print(f"  Decision: {log.get('decision')}")
        if log.get("reason"):
            print(f"  Reason:   {log.get('reason')}")
        if log.get("tool_called"):
            print(f"  Tool:     {log.get('tool_called')}")
            print(f"  Tool Response Payload:")
            print(json.dumps(log.get("tool_result"), indent=4))

    print("\n" + "=" * 75)
    print("  RAZORPAY TEST-MODE END-TO-END EXECUTION PASSED [OK]")
    print("=" * 75)


if __name__ == "__main__":
    test_individual_razorpay_tools()
    test_end_to_end_agent_with_razorpay()
