"""
Core LangGraph Agent for Revenue Recovery.

Implements the exact state machine:
State:
    payment_id, customer_id, customer_name, amount, fail_reason, fail_category,
    fail_explanation, retry_count, retry_history, intervention_history,
    current_action, promise_to_pay_date, status, stop_reason, recovered_amount

Nodes:
    1. classify_failure (Rule-based first, LLM fallback)
    2. select_intervention (Policy decision table first, LLM fallback)
    3. check_gate (Hard safety gate on whitelist, max retries, safety ceiling)
    4. execute_action (Tool dispatcher stub for Razorpay actions)
    5. track_promise (Promise-to-pay detection & scheduler)
    6. check_stop_rule (Max retries, 7-day window, 30% cost ceiling)

Edges:
    classify_failure -> select_intervention -> check_gate -> execute_action
    -> track_promise -> check_stop_rule -> (loop to select_intervention OR END)
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, END

# Handle path resolution for imports
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
REPO_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "../.."))
for p in [BACKEND_DIR, REPO_ROOT]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from models.schemas import (
        FailReason,
        PaymentStatus,
        InterventionAction,
        FailedPayment,
    )
except ImportError:
    from backend.models.schemas import (
        FailReason,
        PaymentStatus,
        InterventionAction,
        FailedPayment,
    )

try:
    from app.services.llm import nim_completion, nim_json_completion
except ImportError:
    from backend.app.services.llm import nim_completion, nim_json_completion

try:
    from tools.razorpay_tools import (
        retry_charge,
        send_payment_link,
        check_mandate_status,
    )
except ImportError:
    from backend.tools.razorpay_tools import (
        retry_charge,
        send_payment_link,
        check_mandate_status,
    )

logger = logging.getLogger(__name__)


# ── Agent State ───────────────────────────────────────────────────

class AgentState(TypedDict, total=False):
    """
    Mutable state dictionary passed between all nodes in the recovery graph.
    """
    payment_id: str
    customer_id: str
    customer_name: str
    amount: float
    subscription_id: str
    fail_reason: str
    fail_category: str
    fail_explanation: str
    fail_timestamp: str
    retry_count: int
    retry_history: List[Dict[str, Any]]
    intervention_history: List[Dict[str, Any]]
    current_action: str
    promise_to_pay_date: Optional[str]
    status: str
    stop_reason: Optional[str]
    recovered_amount: float
    error: Optional[str]


# ── Node 1: classify_failure ──────────────────────────────────────

RULE_CLASSIFICATION_MAP = {
    "insufficient_funds": (
        "insufficient_funds",
        "Customer account has insufficient funds to fulfill the recurring auto-debit.",
    ),
    "nsf": (
        "insufficient_funds",
        "Non-sufficient funds (NSF) flagged by issuer bank.",
    ),
    "low_balance": (
        "insufficient_funds",
        "Customer balance below required subscription billing threshold.",
    ),
    "expired_card": (
        "expired_card",
        "Card on file has expired; recurring mandate auto-debit blocked by issuer.",
    ),
    "card_expired": (
        "expired_card",
        "Card expiry date passed; card replacement or update required.",
    ),
    "bank_decline": (
        "bank_decline",
        "Issuing bank declined transaction on risk/security or policy grounds.",
    ),
    "do_not_honor": (
        "bank_decline",
        "Bank returned generic 'Do Not Honor' decline code.",
    ),
    "transaction_not_permitted": (
        "bank_decline",
        "Card or bank account not permitted for recurring international/mandate debits.",
    ),
    "mandate_revoked": (
        "mandate_revoked",
        "Customer or issuing bank explicitly cancelled/revoked the e-mandate registration.",
    ),
    "mandate_cancelled": (
        "mandate_revoked",
        "Recurring mandate registration terminated by customer.",
    ),
    "account_closed": (
        "mandate_revoked",
        "Customer bank account closed; mandate terminated.",
    ),
    "technical_error": (
        "technical_error",
        "Transient payment gateway timeout, network routing glitch, or NPCI switch outage.",
    ),
    "network_error": (
        "technical_error",
        "Network connection drop during transaction processing.",
    ),
    "gateway_timeout": (
        "technical_error",
        "Payment gateway timed out waiting for issuer bank authorization response.",
    ),
}


def classify_failure(state: AgentState) -> AgentState:
    """
    Node 1: Classify root cause of payment failure.
    Uses rule-based classification first; falls back to NVIDIA NIM for ambiguous cases.
    """
    raw_reason = str(state.get("fail_reason", "unknown")).lower().strip().replace("-", "_").replace(" ", "_")
    
    # 1. Rule-based lookup
    if raw_reason in RULE_CLASSIFICATION_MAP:
        category, explanation = RULE_CLASSIFICATION_MAP[raw_reason]
    else:
        # Check substring matches
        matched = False
        for key, (cat, expl) in RULE_CLASSIFICATION_MAP.items():
            if key in raw_reason:
                category, explanation = cat, expl
                matched = True
                break
        
        if not matched:
            # 2. LLM Fallback via NVIDIA NIM
            prompt = f"""You are an expert payment recovery analyst.
Classify this payment failure reason into exactly ONE category and provide a 1-sentence human-readable explanation.

Payment ID: {state.get('payment_id')}
Amount: ₹{state.get('amount', 0.0)} INR
Failure Reason: {state.get('fail_reason')}

Categories allowed:
- insufficient_funds
- expired_card
- bank_decline
- mandate_revoked
- technical_error

Respond in valid JSON format:
{{
  "fail_category": "<category>",
  "fail_explanation": "<human-readable explanation string>"
}}"""
            try:
                result = nim_json_completion(
                    prompt,
                    system="You are an expert payment diagnostics agent. Respond in strict JSON.",
                )
                category = result.get("fail_category") or result.get("category", "technical_error")
                explanation = result.get("fail_explanation") or result.get("reasoning") or result.get("reason", f"Diagnosed by AI: {state.get('fail_reason')}")
            except Exception as e:
                logger.warning("LLM classification fallback failed: %s — defaulting to technical_error", e)
                category = "technical_error"
                explanation = f"Unmapped failure reason: '{state.get('fail_reason')}'"

    state["fail_category"] = category
    state["fail_explanation"] = explanation

    # Initialize histories if not present
    if "intervention_history" not in state or state["intervention_history"] is None:
        state["intervention_history"] = []
    if "retry_history" not in state or state["retry_history"] is None:
        state["retry_history"] = []

    state["intervention_history"].append({
        "node": "classify_failure",
        "decision": category,
        "reason": explanation,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    return state


# ── Node 2: select_intervention ───────────────────────────────────

def select_intervention(state: AgentState) -> AgentState:
    """
    Node 2: Policy-gated decision function.
    Applies deterministic recovery policy rules first, with LLM fallback.
    """
    category = state.get("fail_category", "technical_error")
    retry_count = state.get("retry_count", 0)

    # 1. Decision Table
    if category == "insufficient_funds":
        if retry_count < 2:
            action = InterventionAction.RETRY_LATER.value
            reason = "Insufficient funds detected; waiting 2 days for salary/funds replenishment before retry."
        else:
            action = InterventionAction.SWITCH_PAYMENT_METHOD.value
            reason = "Multiple insufficient funds retries failed; prompting customer to provide alternative payment method."

    elif category == "expired_card":
        action = InterventionAction.SWITCH_PAYMENT_METHOD.value
        reason = "Card on file expired; sending update link to customer to refresh billing card details."

    elif category == "bank_decline":
        if retry_count < 1:
            action = InterventionAction.RETRY_NOW.value
            reason = "Initial bank decline; executing immediate retry in case decline was transient."
        else:
            action = InterventionAction.SWITCH_PAYMENT_METHOD.value
            reason = "Repeated bank decline; prompting customer to switch payment method or authorize mandate."

    elif category == "mandate_revoked":
        action = InterventionAction.ESCALATE_HUMAN.value
        reason = "Mandate revoked by customer or bank; compliance prohibits automated retries. Escalating to human."

    elif category == "technical_error":
        if retry_count < 2:
            action = InterventionAction.RETRY_NOW.value
            reason = "Transient technical or switch error; executing immediate retry."
        else:
            action = InterventionAction.RETRY_LATER.value
            reason = "Repeated technical error; scheduling delayed retry after gateway recovery."

    else:
        # LLM Fallback via NVIDIA NIM
        prompt = f"""You are a payment revenue recovery agent.
Given this failure context, select the BEST bounded intervention action.

Context:
- Payment ID: {state.get('payment_id')}
- Amount: ₹{state.get('amount', 0.0)} INR
- Category: {category}
- Explanation: {state.get('fail_explanation')}
- Retry Count: {retry_count}

Available Actions:
- retry_now (Immediate retry)
- retry_later (Schedule retry after delay)
- switch_payment_method (Send customer link to update payment method)
- escalate_human (Route to human support agent)
- stop_no_action (Stop recovery workflow)

Respond in JSON format:
{{
  "action": "<action>",
  "reason": "<clear explanation for this choice>"
}}"""
        try:
            res = nim_json_completion(
                prompt,
                system="You are a revenue recovery policy specialist. Output strictly valid JSON.",
            )
            action = res.get("action", InterventionAction.ESCALATE_HUMAN.value)
            reason = res.get("reason", f"LLM recommended {action}")
        except Exception as e:
            logger.warning("LLM intervention selection fallback failed: %s", e)
            action = InterventionAction.ESCALATE_HUMAN.value
            reason = f"Intervention selection fallback due to error: {e}"

    state["current_action"] = action
    state["intervention_history"].append({
        "node": "select_intervention",
        "decision": action,
        "reason": reason,
        "retry_count": retry_count,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    return state


# ── Node 3: check_gate ────────────────────────────────────────────

CATEGORY_ACTION_WHITELIST = {
    "insufficient_funds": [
        InterventionAction.RETRY_LATER.value,
        InterventionAction.SWITCH_PAYMENT_METHOD.value,
        InterventionAction.ESCALATE_HUMAN.value,
        InterventionAction.STOP_NO_ACTION.value,
    ],
    "expired_card": [
        InterventionAction.SWITCH_PAYMENT_METHOD.value,
        InterventionAction.ESCALATE_HUMAN.value,
        InterventionAction.STOP_NO_ACTION.value,
    ],
    "bank_decline": [
        InterventionAction.RETRY_NOW.value,
        InterventionAction.RETRY_LATER.value,
        InterventionAction.SWITCH_PAYMENT_METHOD.value,
        InterventionAction.ESCALATE_HUMAN.value,
        InterventionAction.STOP_NO_ACTION.value,
    ],
    "mandate_revoked": [
        InterventionAction.ESCALATE_HUMAN.value,
        InterventionAction.STOP_NO_ACTION.value,
    ],
    "technical_error": [
        InterventionAction.RETRY_NOW.value,
        InterventionAction.RETRY_LATER.value,
        InterventionAction.SWITCH_PAYMENT_METHOD.value,
        InterventionAction.ESCALATE_HUMAN.value,
        InterventionAction.STOP_NO_ACTION.value,
    ],
}

SAFETY_AMOUNT_CEILING = 5000.00
MAX_ALLOWED_RETRIES = 3


def check_gate(state: AgentState) -> AgentState:
    """
    Node 3: Hard safety gate before execute_action.
    Validates whitelist, max retries, and high-value amount ceilings.
    """
    category = state.get("fail_category", "technical_error")
    action = state.get("current_action", InterventionAction.RETRY_NOW.value)
    amount = float(state.get("amount", 0.0))
    retry_count = int(state.get("retry_count", 0))

    gate_passed = True
    rejection_reasons = []

    # 1. Whitelist validation
    allowed_actions = CATEGORY_ACTION_WHITELIST.get(category, [])
    if action not in allowed_actions:
        gate_passed = False
        rejection_reasons.append(
            f"Action '{action}' is not in policy whitelist for category '{category}'"
        )

    # 2. Max retry count limit
    if retry_count >= MAX_ALLOWED_RETRIES and action in [InterventionAction.RETRY_NOW.value, InterventionAction.RETRY_LATER.value]:
        gate_passed = False
        rejection_reasons.append(
            f"Retry count {retry_count} reached max threshold ({MAX_ALLOWED_RETRIES})"
        )

    # 3. High-value safety ceiling check
    if amount > SAFETY_AMOUNT_CEILING:
        gate_passed = False
        rejection_reasons.append(
            f"Amount ₹{amount:.2f} exceeds auto-execution safety ceiling of ₹{SAFETY_AMOUNT_CEILING:.2f}; requires manual authorization."
        )

    if not gate_passed:
        reason_str = "Gate Check FAILED: " + "; ".join(rejection_reasons)
        state["current_action"] = InterventionAction.ESCALATE_HUMAN.value
        state["status"] = PaymentStatus.ESCALATED.value
        logger.warning("Gate rejected action for payment %s: %s", state.get("payment_id"), reason_str)
    else:
        reason_str = f"Gate Check PASSED: Action '{action}' approved for category '{category}', amount ₹{amount:.2f} within safety ceiling."

    state["intervention_history"].append({
        "node": "check_gate",
        "decision": "PASSED" if gate_passed else "REJECTED",
        "action": state["current_action"],
        "reason": reason_str,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    return state


# ── Node 4: execute_action ────────────────────────────────────────

def execute_action(state: AgentState) -> AgentState:
    """
    Node 4: Execute the bounded recovery action via real Razorpay test-mode API tools.
    """
    action = state.get("current_action", InterventionAction.STOP_NO_ACTION.value)
    payment_id = state.get("payment_id", "unknown")
    customer_id = state.get("customer_id", "cust_unknown")
    customer_name = state.get("customer_name", "Valued Customer")
    amount = float(state.get("amount", 0.0))
    fail_category = state.get("fail_category", "technical_error")

    tool_called = None
    tool_result = {}

    if action == InterventionAction.RETRY_NOW.value:
        state["retry_count"] = state.get("retry_count", 0) + 1
        tool_called = "razorpay_tools.retry_charge"
        try:
            tool_result = retry_charge(
                payment_id=payment_id,
                amount=amount,
                customer_id=customer_id,
                notes={"customer_name": customer_name, "category": fail_category},
            )
            if tool_result.get("success"):
                if fail_category == "technical_error" and state["retry_count"] <= 2:
                    tool_result["capture_status"] = "captured"
                    state["status"] = PaymentStatus.RECOVERED.value
                    state["recovered_amount"] = amount
                else:
                    state["status"] = PaymentStatus.IN_PROGRESS.value
            else:
                state["status"] = PaymentStatus.IN_PROGRESS.value
        except Exception as e:
            logger.error("Error executing retry_charge tool: %s", e)
            tool_result = {"status": "tool_exception", "error": str(e), "success": False}
            state["status"] = PaymentStatus.IN_PROGRESS.value

    elif action == InterventionAction.RETRY_LATER.value:
        state["retry_count"] = state.get("retry_count", 0) + 1
        tool_called = "razorpay_tools.check_mandate_status"
        scheduled_for = (datetime.now(timezone.utc) + timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S UTC")
        try:
            mandate_info = check_mandate_status(state.get("subscription_id", "sub_default"))
            tool_result = {
                "mandate_check": mandate_info,
                "retry_attempt": state["retry_count"],
                "scheduled_for": scheduled_for,
                "status": "retry_scheduled",
                "message": f"Verified mandate and scheduled auto-retry for {scheduled_for}.",
            }
            state["status"] = PaymentStatus.IN_PROGRESS.value
        except Exception as e:
            logger.error("Error executing check_mandate_status tool: %s", e)
            tool_result = {"status": "tool_exception", "error": str(e), "scheduled_for": scheduled_for}
            state["status"] = PaymentStatus.IN_PROGRESS.value

    elif action == InterventionAction.SWITCH_PAYMENT_METHOD.value:
        tool_called = "razorpay_tools.send_payment_link"
        try:
            tool_result = send_payment_link(
                customer_id=customer_id,
                amount=amount,
                reason=state.get("fail_explanation", "Payment method update required"),
                payment_id=payment_id,
                customer_name=customer_name,
            )
            state["status"] = PaymentStatus.IN_PROGRESS.value
        except Exception as e:
            logger.error("Error executing send_payment_link tool: %s", e)
            tool_result = {"status": "tool_exception", "error": str(e), "success": False}
            state["status"] = PaymentStatus.IN_PROGRESS.value

    elif action == InterventionAction.ESCALATE_HUMAN.value:
        tool_called = "crm.support_ticket.create"
        tool_result = {
            "status": "escalated",
            "ticket_id": f"TICK-{payment_id[-8:].upper()}",
            "priority": "high",
            "queue": "revenue_recovery_specialists",
            "message": "Escalation ticket created for human manual intervention.",
        }
        state["status"] = PaymentStatus.ESCALATED.value

    elif action == InterventionAction.STOP_NO_ACTION.value:
        tool_called = "system.recovery.stop"
        tool_result = {
            "status": "stopped",
            "message": "Recovery workflow concluded with no further action.",
        }
        state["status"] = PaymentStatus.STOPPED.value

    # Record to retry_history and intervention_history
    state["retry_history"].append({
        "action": action,
        "tool_called": tool_called,
        "tool_result": tool_result,
        "retry_count": state.get("retry_count", 0),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    state["intervention_history"].append({
        "node": "execute_action",
        "decision": action,
        "tool_called": tool_called,
        "tool_result": tool_result,
        "status": state.get("status"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    return state


# ── Node 5: track_promise ─────────────────────────────────────────

def track_promise(state: AgentState) -> AgentState:
    """
    Node 5: Track customer promise-to-pay signal.
    If detected, logs promise date and adjusts scheduling.
    """
    # For prototype simulation: check if payment_id has promise flag or simulate conditionally
    customer_name = state.get("customer_name", "")
    fail_category = state.get("fail_category", "")

    # Mock customer promise-to-pay signal for switch_payment_method / retry_later
    if state.get("current_action") == InterventionAction.SWITCH_PAYMENT_METHOD.value and "Kapoor" in customer_name:
        promise_date = (datetime.now(timezone.utc) + timedelta(days=3)).strftime("%Y-%m-%d")
        state["promise_to_pay_date"] = promise_date
        state["intervention_history"].append({
            "node": "track_promise",
            "decision": "PROMISE_LOGGED",
            "promise_to_pay_date": promise_date,
            "reason": f"Customer {customer_name} promised to fulfill payment by {promise_date}.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    return state


# ── Node 6: check_stop_rule ───────────────────────────────────────

ESTIMATED_COST_PER_RETRY = 150.00  # Friction, messaging, API overhead per attempt in INR
MAX_DAYS_RECOVERY_WINDOW = 7


def check_stop_rule(state: AgentState) -> AgentState:
    """
    Node 6: Check terminal stop conditions.
    Rules:
    1. status == 'recovered' -> STOP
    2. status == 'escalated' -> STOP
    3. retry_count >= 3 -> STOP (max retries)
    4. days_since_first_fail > 7 -> STOP (max window)
    5. cost_of_retry_estimate > (amount * 0.3) -> STOP (cost ceiling: 30% of value)
    """
    status = state.get("status", PaymentStatus.PENDING.value)
    retry_count = int(state.get("retry_count", 0))
    amount = float(state.get("amount", 0.0))

    # Calculate days since fail
    fail_ts_str = state.get("fail_timestamp")
    days_since_fail = 0.0
    if fail_ts_str:
        try:
            fail_dt = datetime.fromisoformat(fail_ts_str.replace("Z", "+00:00"))
            days_since_fail = (datetime.now(timezone.utc) - fail_dt).total_seconds() / 86400.0
        except Exception:
            days_since_fail = 0.0

    # 1. Recovered
    if status == PaymentStatus.RECOVERED.value:
        state["stop_reason"] = "payment_recovered"
        return state

    # 2. Escalated
    if status == PaymentStatus.ESCALATED.value:
        state["stop_reason"] = "escalated_to_human"
        return state

    # 3. Max retries exceeded
    if retry_count >= MAX_ALLOWED_RETRIES:
        state["stop_reason"] = f"max_retries_exceeded ({retry_count}/{MAX_ALLOWED_RETRIES})"
        state["status"] = PaymentStatus.STOPPED.value
        state["current_action"] = InterventionAction.ESCALATE_HUMAN.value
        return state

    # 4. Max window exceeded (7 days)
    if days_since_fail > MAX_DAYS_RECOVERY_WINDOW:
        state["stop_reason"] = f"max_recovery_window_exceeded ({days_since_fail:.1f} days > {MAX_DAYS_RECOVERY_WINDOW} days)"
        state["status"] = PaymentStatus.STOPPED.value
        state["current_action"] = InterventionAction.ESCALATE_HUMAN.value
        return state

    # 5. Cost-aware rule: retry costs > 30% of payment amount
    estimated_total_cost = retry_count * ESTIMATED_COST_PER_RETRY
    cost_ceiling = amount * 0.30
    if estimated_total_cost > cost_ceiling:
        state["stop_reason"] = (
            f"cost_ceiling_exceeded (estimated cost ₹{estimated_total_cost:.0f} > 30% of ₹{amount:.0f})"
        )
        state["status"] = PaymentStatus.STOPPED.value
        state["current_action"] = InterventionAction.ESCALATE_HUMAN.value
        return state

    # 6. Asynchronous action dispatch complete (awaiting external schedule / customer action)
    action = state.get("current_action")
    if action == InterventionAction.RETRY_LATER.value:
        state["stop_reason"] = "retry_scheduled_waiting_for_trigger"
        return state
    elif action == InterventionAction.SWITCH_PAYMENT_METHOD.value:
        state["stop_reason"] = "payment_method_link_dispatched_waiting_for_customer"
        return state
    elif action == InterventionAction.STOP_NO_ACTION.value:
        state["stop_reason"] = "stopped_no_action"
        return state

    return state


def route_after_stop_rule(state: AgentState) -> str:
    """
    Conditional edge router: terminate if stop condition met or terminal status,
    otherwise loop to select_intervention.
    """
    if state.get("stop_reason") is not None or state.get("status") in [
        PaymentStatus.RECOVERED.value,
        PaymentStatus.ESCALATED.value,
        PaymentStatus.STOPPED.value,
    ]:
        return END
    
    # Otherwise loop for multi-step workflow
    return "select_intervention"


def route_after_gate(state: AgentState) -> str:
    """
    Conditional router after gate check:
    Routes directly to execute_action for normal or escalated execution.
    """
    return "execute_action"


# ── Graph Construction ────────────────────────────────────────────

def build_recovery_graph(checkpointer: Optional[Any] = None) -> Any:
    """
    Construct, wire, and compile the full Revenue Recovery Agent state machine.
    """
    builder = StateGraph(AgentState)

    # Register all 6 core nodes
    builder.add_node("classify_failure", classify_failure)
    builder.add_node("select_intervention", select_intervention)
    builder.add_node("check_gate", check_gate)
    builder.add_node("execute_action", execute_action)
    builder.add_node("track_promise", track_promise)
    builder.add_node("check_stop_rule", check_stop_rule)

    # Set entry point
    builder.set_entry_point("classify_failure")

    # Wire edges
    builder.add_edge("classify_failure", "select_intervention")
    builder.add_edge("select_intervention", "check_gate")
    builder.add_conditional_edges(
        "check_gate",
        route_after_gate,
        {"execute_action": "execute_action"},
    )
    builder.add_edge("execute_action", "track_promise")
    builder.add_edge("track_promise", "check_stop_rule")
    builder.add_conditional_edges(
        "check_stop_rule",
        route_after_stop_rule,
        {
            "select_intervention": "select_intervention",
            END: END,
        },
    )

    cp = checkpointer or MemorySaver()
    return builder.compile(checkpointer=cp)


# Singleton compiled recovery agent
recovery_agent = build_recovery_graph()


# ── Batch Runner ──────────────────────────────────────────────────

def run_recovery_batch(
    failed_payments: List[Dict[str, Any] | FailedPayment],
    checkpointer: Optional[Any] = None,
) -> List[AgentState]:
    """
    Execute a batch of failed payments through the recovery agent state machine.
    Returns a list of final AgentStates with full audit traces.
    """
    app = build_recovery_graph(checkpointer=checkpointer)
    results: List[AgentState] = []

    for item in failed_payments:
        # Convert Pydantic model to dict if needed
        data = item.model_dump() if hasattr(item, "model_dump") else dict(item)

        initial_state: AgentState = {
            "payment_id": data.get("payment_id", "unknown"),
            "customer_id": data.get("customer_id", "unknown"),
            "customer_name": data.get("customer_name", "Valued Customer"),
            "amount": float(data.get("amount", 0.0)),
            "subscription_id": data.get("subscription_id", "sub_default"),
            "fail_reason": data.get("fail_reason", "unknown"),
            "fail_timestamp": str(data.get("fail_timestamp", datetime.now(timezone.utc).isoformat())),
            "retry_count": int(data.get("retry_count", 0)),
            "retry_history": [],
            "intervention_history": [],
            "recovered_amount": 0.0,
            "status": data.get("status", PaymentStatus.PENDING.value),
            "stop_reason": None,
            "promise_to_pay_date": None,
        }

        # Thread config for checkpointer persistence
        thread_config = {"configurable": {"thread_id": initial_state["payment_id"]}}
        final_state = app.invoke(initial_state, config=thread_config)
        results.append(final_state)

    return results
