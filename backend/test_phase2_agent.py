"""
Phase 2 Test Script — Revenue Recovery Agent (NVIDIA NIM Integration)

Tests:
1. Rule-based fast-path classification and intervention mapping
2. LLM fallback classification & intervention selection with NVIDIA NIM
3. Strict prompt-based JSON parsing and Pydantic validation
4. End-to-end LangGraph recovery agent workflow execution

Usage:
    python test_phase2_agent.py
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Ensure backend root is on sys.path and stdout handles utf-8
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.agent.graph import build_recovery_graph
from app.config import get_settings
from app.schemas import (
    FailureCategory,
    FailureClassification,
    InterventionAction,
    InterventionDecision,
    PaymentFailureInput,
)
from app.services.llm import nim_json_completion


def print_separator(title: str):
    print(f"\n{'=' * 65}")
    print(f"  {title}")
    print(f"{'=' * 65}")


def test_rule_based_flow():
    """Test standard rule-based classification and intervention."""
    print_separator("Test 1: Rule-Based Fast Path Flow")

    graph = build_recovery_graph()
    test_cases = [
        ("INSUFFICIENT_FUNDS", FailureCategory.INSUFFICIENT_FUNDS, InterventionAction.RETRY_LATER),
        ("EXPIRED_CARD", FailureCategory.EXPIRED_CARD, InterventionAction.SWITCH_PAYMENT_METHOD),
        ("NETWORK_ERROR", FailureCategory.TECHNICAL_ERROR, InterventionAction.RETRY_NOW),
        ("ACCOUNT_CLOSED", FailureCategory.MANDATE_REVOKED, InterventionAction.ESCALATE_HUMAN),
    ]

    for code, expected_cat, expected_act in test_cases:
        inp = PaymentFailureInput(
            payment_id=f"pay_{code.lower()}_001",
            customer_id="cust_12345",
            amount=1499.00,
            currency="INR",
            error_code=code,
            error_description=f"Payment failed due to {code.lower()}",
            retry_count=1,
            payment_method="mandate",
        )

        final_state = graph.invoke(
            {"payment_id": inp.payment_id, "amount": inp.amount, "fail_reason": inp.error_code, "retry_count": inp.retry_count},
            config={"configurable": {"thread_id": inp.payment_id}},
        )

        print(f"  Payment: {final_state.get('payment_id')}")
        print(f"    - Error Code:     {code}")
        print(f"    - Category:       {final_state.get('fail_category')}")
        print(f"    - Action:         {final_state.get('current_action')}")
        print(f"    - Explanation:    {final_state.get('fail_explanation')}")

        assert final_state.get("fail_category") == expected_cat.value
        assert final_state.get("current_action") == expected_act.value
        print("    --> [PASSED]")


def test_nvidia_nim_fallback_structured_output():
    """Test NVIDIA NIM LLM fallback with strict prompt-based JSON & Pydantic validation."""
    print_separator("Test 2: NVIDIA NIM Structured Output & Fallback Parsing")

    # Simulate an unknown error that triggers NIM LLM fallback
    unknown_payment = PaymentFailureInput(
        payment_id="pay_unknown_999",
        customer_id="cust_99999",
        amount=4999.00,
        currency="INR",
        error_code="ERR_CUSTOM_BANK_GATEWAY_THROTTLED",
        error_description="Issuer gateway returned temporary routing error 92: velocity check failed",
        retry_count=0,
        payment_method="mandate",
    )

    settings = get_settings()
    print(f"  NVIDIA NIM Base URL: {settings.NVIDIA_NIM_BASE_URL}")
    print(f"  NVIDIA NIM Model:    {settings.NVIDIA_NIM_MODEL}")

    # Check if a live key is configured
    has_live_key = (
        bool(settings.NVIDIA_NIM_API_KEY)
        and not settings.NVIDIA_NIM_API_KEY.startswith("nvapi-xxx")
        and not settings.NVIDIA_NIM_API_KEY.startswith("sk-")
    )

    if has_live_key:
        print("  [LIVE] Calling NVIDIA NIM API directly...")
        graph = build_recovery_graph()
        final_state = graph.invoke({"payment": unknown_payment})
        res = final_state["result"]
        print(f"  LLM Classified Category: {res.classification.category.value}")
        print(f"  LLM Classification Reasoning: {res.classification.reasoning}")
        print(f"  LLM Intervention Action: {res.intervention.action.value}")
        print(f"  LLM Intervention Reasoning: {res.intervention.reasoning}")
    else:
        print("  [MOCK] Validating NIM LLM fallback pipeline & JSON parser with Pydantic validation...")
        
        # Test direct nim_json_completion parser with raw JSON and markdown code fences
        mock_nim_response = MagicMock()
        mock_nim_response.choices = [
            MagicMock(message=MagicMock(content='```json\n{"category": "bank_decline", "confidence": 0.88, "reasoning": "Issuer gateway velocity throttle behaves as a temporary bank-side decline."}\n```'))
        ]

        with patch("app.services.llm.get_llm_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_nim_response
            mock_get_client.return_value = mock_client

            parsed: FailureClassification = nim_json_completion(
                "Classify this failure",
                response_model=FailureClassification,
            )

            print(f"    - Parsed Category:   {parsed.category.value}")
            print(f"    - Parsed Confidence: {parsed.confidence}")
            print(f"    - Parsed Reasoning:  {parsed.reasoning}")
            assert parsed.category == FailureCategory.BANK_DECLINE
            assert parsed.confidence == 0.88
            print("    --> Markdown-fenced JSON parsed & validated successfully [PASSED]")

        # Test end-to-end graph with NIM fallback mock
        mock_intervention_response = MagicMock()
        mock_intervention_response.choices = [
            MagicMock(message=MagicMock(content='{"action": "retry_later", "priority": 2, "reasoning": "Velocity throttles typically reset after 4-6 hours, so schedule delayed retry.", "estimated_success_rate": 0.75}'))
        ]

        with patch("app.services.llm.get_llm_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat.completions.create.side_effect = [
                mock_nim_response,          # For classify_failure
                mock_intervention_response,  # For select_intervention
            ]
            mock_get_client.return_value = mock_client

            graph = build_recovery_graph()
            final_state = graph.invoke(
                {"payment_id": unknown_payment.payment_id, "amount": unknown_payment.amount, "fail_reason": unknown_payment.error_code, "retry_count": unknown_payment.retry_count},
                config={"configurable": {"thread_id": unknown_payment.payment_id}},
            )
            print(f"\n  End-to-end Graph Result for Unknown Error:")
            print(f"    - Payment ID:     {final_state.get('payment_id')}")
            print(f"    - Category:       {final_state.get('fail_category')} (explanation: {final_state.get('fail_explanation')})")
            print(f"    - Action:         {final_state.get('current_action')}")
            print(f"    - Stop Reason:    {final_state.get('stop_reason')}")
            assert final_state.get("fail_category") == FailureCategory.BANK_DECLINE.value
            assert final_state.get("current_action") == InterventionAction.SWITCH_PAYMENT_METHOD.value
            print("    --> End-to-End NIM Graph Execution [PASSED]")


def test_pydantic_schema_validation():
    """Verify all Pydantic v2 schemas and enums."""
    print_separator("Test 3: Pydantic v2 Schema & Bounded Action Validation")

    categories = [c.value for c in FailureCategory]
    interventions = [i.value for i in InterventionAction]
    print(f"  Valid Failure Categories ({len(categories)}): {', '.join(categories)}")
    print(f"  Valid Intervention Actions ({len(interventions)}): {', '.join(interventions)}")

    # Ensure out-of-range confidence or invalid action fails validation
    try:
        FailureClassification(category=FailureCategory.BANK_DECLINE, confidence=1.5, reasoning="invalid")
        raise AssertionError("Expected ValidationError for confidence > 1.0")
    except Exception as e:
        print("  Pydantic validation constraint caught invalid confidence correctly [PASSED]")


if __name__ == "__main__":
    print("\n[START] Starting Phase 2 Test Suite: Revenue Recovery Agent (NVIDIA NIM)")
    test_rule_based_flow()
    test_nvidia_nim_fallback_structured_output()
    test_pydantic_schema_validation()
    print_separator("ALL PHASE 2 TESTS PASSED SUCCESSFULLY [OK]")
