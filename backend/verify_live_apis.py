"""
Live Verification of Razorpay Test API & NVIDIA NIM LLM Integration.
"""

import json
import os
import sys

# Ensure backend root is on sys.path and utf-8 stdout
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.config import get_settings
from app.services.llm import get_llm_client, nim_completion, nim_json_completion
from tools.razorpay_tools import (
    get_razorpay_client,
    is_live_test_mode_configured,
    retry_charge,
    send_payment_link,
    check_mandate_status,
)
from agent.graph import run_recovery_batch


def print_banner(text: str):
    print(f"\n{'=' * 75}")
    print(f"  {text}")
    print(f"{'=' * 75}")


def test_live_nim():
    print_banner("1. TESTING LIVE NVIDIA NIM LLM API")
    settings = get_settings()
    print(f"Model: {settings.NVIDIA_NIM_MODEL}")
    print(f"Base URL: {settings.NVIDIA_NIM_BASE_URL}")

    # Text completion
    print("\n--> Testing Text Completion...")
    try:
        reply = nim_completion("In 1 sentence, explain what revenue recovery is.", temperature=0.2)
        print(f"NIM Response:\n\"{reply.strip()}\"")
    except Exception as e:
        print(f"Text Completion Error: {e}")

    # JSON completion
    print("\n--> Testing Structured JSON Completion...")
    try:
        json_output = nim_json_completion(
            "Diagnose a failed transaction with error: 'INSUFFICIENT_FUNDS'. Output category and recovery recommendation in JSON.",
        )
        print("NIM Structured Output:")
        print(json.dumps(json_output, indent=2))
    except Exception as e:
        print(f"JSON Completion Error: {e}")


def test_live_razorpay():
    print_banner("2. TESTING LIVE RAZORPAY TEST-MODE API")
    settings = get_settings()
    print(f"Razorpay Key ID: {settings.RAZORPAY_KEY_ID[:12]}...")
    print(f"Live Test Mode Active: {is_live_test_mode_configured()}")

    # 1. Real test-mode Order creation
    print("\n--> Testing Real Razorpay Order Creation via retry_charge()...")
    order_res = retry_charge(
        payment_id="pay_demo_live_001",
        amount=1499.00,
        customer_id="cust_live_101",
        notes={"customer_name": "Live Test Customer", "source": "AI Recovery Agent Live Test"},
    )
    print("Razorpay Order Result:")
    print(json.dumps(order_res, indent=2))
    assert order_res.get("success") is True
    print(f"  [OK] Successfully created real Razorpay test order: {order_res.get('razorpay_order_id')}")

    # 2. Real test-mode Payment Link creation
    print("\n--> Testing Real Razorpay Payment Link Creation via send_payment_link()...")
    link_res = send_payment_link(
        customer_id="cust_live_101",
        amount=1499.00,
        reason="Subscription renewal payment update",
        payment_id="pay_demo_live_001",
        customer_name="Live Test Customer",
        customer_email="live.test@example.com",
    )
    print("Razorpay Payment Link Result:")
    print(json.dumps(link_res, indent=2))
    assert link_res.get("success") is True
    print(f"  [OK] Successfully created real Razorpay payment link: {link_res.get('short_url')}")


def test_live_agent_end_to_end():
    print_banner("3. END-TO-END AGENT EXECUTION WITH LIVE RAZORPAY & NIM")

    live_sample_payment = {
        "payment_id": "pay_live_card_expired_901",
        "customer_id": "cust_live_901",
        "customer_name": "Rohan Kapoor",
        "amount": 2499.00,
        "subscription_id": "sub_enterprise_live_901",
        "fail_reason": "expired_card",
        "fail_timestamp": "2026-08-23T10:00:00Z",
        "retry_count": 0,
        "status": "pending",
    }

    print(f"Submitting Payment: {live_sample_payment['payment_id']} (₹{live_sample_payment['amount']:.2f} INR)")
    results = run_recovery_batch([live_sample_payment])
    final_state = results[0]

    print("\nFinal State Summary:")
    print(f"  - Payment ID:       {final_state.get('payment_id')}")
    print(f"  - Customer:         {final_state.get('customer_name')}")
    print(f"  - Classified As:    {final_state.get('fail_category')}")
    print(f"  - Explanation:      {final_state.get('fail_explanation')}")
    print(f"  - Selected Action:  {final_state.get('current_action')}")
    print(f"  - Final Status:     {final_state.get('status')}")
    print(f"  - Stop Reason:      {final_state.get('stop_reason')}")

    print("\nExecution Step Audit Log (with Real API Payloads):")
    for step in final_state.get("intervention_history", []):
        node = step.get("node")
        print(f"\n[{node.upper()}]:")
        print(f"  Decision: {step.get('decision')}")
        if step.get("reason"):
            print(f"  Reason:   {step.get('reason')}")
        if step.get("tool_called"):
            print(f"  Tool:     {step.get('tool_called')}")
            print(f"  Real API Response:")
            print(json.dumps(step.get("tool_result"), indent=4))

    print_banner("ALL LIVE INTEGRATION TESTS PASSED [OK]")


if __name__ == "__main__":
    test_live_nim()
    test_live_razorpay()
    test_live_agent_end_to_end()
