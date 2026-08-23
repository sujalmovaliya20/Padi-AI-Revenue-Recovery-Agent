"""
Batch Processing Router for Revenue Recovery Agent.

Endpoints:
- POST /batch/run — Launch batch recovery process in background
- GET  /batch/{batch_id}/status — Real-time progress and live status counts
- GET  /batch/{batch_id}/results — Final state of all processed payments in batch
- GET  /batch/{batch_id}/audit/{payment_id} — Detailed decision trace and tool responses for a specific payment
- GET  /batch/{batch_id}/metrics — Aggregate recovery ROI & operational metrics
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from pydantic import BaseModel, Field

# Ensure path resolution
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
REPO_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", ".."))
for p in [BACKEND_DIR, REPO_ROOT]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from agent.graph import build_recovery_graph, AgentState
    from models.schemas import FailedPayment, PaymentStatus
except ImportError:
    from backend.agent.graph import build_recovery_graph, AgentState
    from backend.models.schemas import FailedPayment, PaymentStatus

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/batch", tags=["Batch Recovery"])


# ── In-Memory & State Store for Batches ─────────────────────────────

class BatchRecord:
    """Stores progress, states, and metrics for a batch run."""

    def __init__(self, batch_id: str, payments: List[Dict[str, Any]]):
        self.batch_id = batch_id
        self.status = "queued"  # queued, running, completed, failed
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.completed_at: Optional[str] = None
        self.total_count = len(payments)
        self.processed_count = 0
        self.progress_pct = 0.0
        self.raw_payments = payments
        self.results: List[Dict[str, Any]] = []
        self.payments_by_id: Dict[str, Dict[str, Any]] = {}
        self.counts_by_status: Dict[str, int] = {
            "pending": len(payments),
            "in_progress": 0,
            "recovered": 0,
            "escalated": 0,
            "stopped": 0,
        }
        self.error: Optional[str] = None


# Global in-memory batch registry
BATCH_STORE: Dict[str, BatchRecord] = {}


# ── Request / Response DTO Schemas ─────────────────────────────────

class BatchRunRequest(BaseModel):
    """Payload to start a batch recovery run."""
    payment_ids: Optional[Union[List[str], str]] = Field(
        default="all pending",
        description="List of specific payment IDs, or 'all pending' to process entire pending queue.",
        example=["pay_syn_0823_1001", "pay_syn_0822_1002"],
    )


class BatchRunResponse(BaseModel):
    batch_id: str
    status: str
    total_payments: int
    message: str
    created_at: str


class BatchStatusResponse(BaseModel):
    batch_id: str
    status: str
    total_count: int
    processed_count: int
    progress_pct: float
    counts_by_status: Dict[str, int]
    created_at: str
    completed_at: Optional[str] = None


class BatchResultsResponse(BaseModel):
    batch_id: str
    status: str
    total_count: int
    results: List[Dict[str, Any]]


class AuditTrailResponse(BaseModel):
    batch_id: str
    payment_id: str
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    amount: float
    fail_category: Optional[str] = None
    fail_explanation: Optional[str] = None
    final_status: str
    final_action: Optional[str] = None
    stop_reason: Optional[str] = None
    recovered_amount: float = 0.0
    promise_to_pay_date: Optional[str] = None
    retry_count: int = 0
    audit_trail: List[Dict[str, Any]]
    retry_history: List[Dict[str, Any]]


class CategoryMetric(BaseModel):
    category: str
    total_count: int
    total_amount: float
    recovered_count: int
    recovered_amount: float
    recovery_rate_pct: float
    escalated_count: int
    in_progress_count: int
    stopped_count: int


class BatchMetricsResponse(BaseModel):
    batch_id: str
    total_payments: int
    total_amount_at_risk: float
    total_recovered: float
    recovery_rate_pct: float
    avg_retries_to_recovery: float
    escalation_rate: float
    breakdown_by_fail_category: Dict[str, CategoryMetric]


# ── Data Loading Helpers ───────────────────────────────────────────

def load_synthetic_dataset() -> List[Dict[str, Any]]:
    """Load the synthetic payment dataset from disk or fallback generator."""
    candidates = [
        Path(REPO_ROOT) / "data" / "synthetic_failed_payments.json",
        Path(BACKEND_DIR) / "data" / "synthetic_failed_payments.json",
        Path(__file__).resolve().parent.parent.parent.parent / "data" / "synthetic_failed_payments.json",
    ]
    for p in candidates:
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning("Error reading dataset from %s: %s", p, e)

    # If dataset file missing on disk, dynamically generate a batch of 75
    try:
        from data.generate_synthetic_batch import generate_synthetic_payments
        return generate_synthetic_payments(count=75)
    except Exception:
        return []


def resolve_payments_to_process(payment_ids: Optional[Union[List[str], str]]) -> List[Dict[str, Any]]:
    """Resolve requested payment IDs against the available dataset."""
    all_records = load_synthetic_dataset()
    lookup = {r["payment_id"]: r for r in all_records}

    # Case 1: "all pending", "all", None, or empty list
    if (
        payment_ids is None
        or payment_ids == "all pending"
        or payment_ids == "all"
        or (isinstance(payment_ids, list) and len(payment_ids) == 0)
    ):
        return all_records

    # Case 2: Specific list of string IDs
    target_ids = [payment_ids] if isinstance(payment_ids, str) else payment_ids
    selected: List[Dict[str, Any]] = []

    for pid in target_ids:
        if pid in lookup:
            selected.append(lookup[pid])
        else:
            # Generate a realistic mock record for testing unknown arbitrary ID
            selected.append({
                "payment_id": pid,
                "customer_id": f"cust_mock_{pid[-6:]}",
                "customer_name": "Valued Subscriber",
                "amount": 999.00,
                "subscription_id": "sub_pro_monthly",
                "fail_reason": "bank_decline",
                "fail_timestamp": datetime.now(timezone.utc).isoformat(),
                "retry_count": 0,
                "status": "pending",
            })
    return selected


# ── Background Execution Task ─────────────────────────────────────

def execute_batch_in_background(batch_id: str):
    """
    Worker task running each payment through the LangGraph recovery agent graph.
    Updates the batch record in real-time.
    """
    record = BATCH_STORE.get(batch_id)
    if not record:
        logger.error("Batch %s not found in store for background execution", batch_id)
        return

    record.status = "running"
    logger.info("Starting background batch execution %s (%d payments)", batch_id, record.total_count)

    graph = build_recovery_graph()

    for item in record.raw_payments:
        pid = item["payment_id"]
        initial_state: AgentState = {
            "payment_id": pid,
            "customer_id": item.get("customer_id", "unknown"),
            "customer_name": item.get("customer_name", "Valued Customer"),
            "amount": float(item.get("amount", 0.0)),
            "subscription_id": item.get("subscription_id", "sub_default"),
            "fail_reason": item.get("fail_reason", "unknown"),
            "fail_timestamp": str(item.get("fail_timestamp", datetime.now(timezone.utc).isoformat())),
            "retry_count": int(item.get("retry_count", 0)),
            "retry_history": [],
            "intervention_history": [],
            "recovered_amount": 0.0,
            "status": PaymentStatus.PENDING.value,
            "stop_reason": None,
            "promise_to_pay_date": None,
        }

        try:
            thread_cfg = {"configurable": {"thread_id": pid}}
            final_state = graph.invoke(initial_state, config=thread_cfg)
        except Exception as e:
            logger.error("Error executing payment %s: %s", pid, e)
            final_state = dict(initial_state)
            final_state["status"] = PaymentStatus.STOPPED.value
            final_state["stop_reason"] = f"Execution Error: {e}"
            final_state["error"] = str(e)

        # Update batch record incrementally
        final_dict = dict(final_state)
        record.results.append(final_dict)
        record.payments_by_id[pid] = final_dict
        record.processed_count += 1
        record.progress_pct = round((record.processed_count / record.total_count) * 100.0, 1)

        # Update status counts
        cur_status = final_dict.get("status", "pending")
        if cur_status in record.counts_by_status:
            record.counts_by_status[cur_status] += 1
        else:
            record.counts_by_status[cur_status] = 1

        # Decrement pending count
        if record.counts_by_status.get("pending", 0) > 0:
            record.counts_by_status["pending"] -= 1

    record.status = "completed"
    record.completed_at = datetime.now(timezone.utc).isoformat()
    logger.info("Batch execution %s completed successfully (%d/%d)", batch_id, record.processed_count, record.total_count)


# ── Route Handlers ────────────────────────────────────────────────

@router.post("/run", response_model=BatchRunResponse, status_code=status.HTTP_202_ACCEPTED)
async def run_batch(
    payload: Optional[BatchRunRequest] = None,
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """
    Launch a batch of payments through the LangGraph recovery agent in the background.
    Returns batch_id immediately.
    """
    p_ids = payload.payment_ids if payload else "all pending"
    records = resolve_payments_to_process(p_ids)

    if not records:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No payments found matching the specified criteria to process.",
        )

    batch_id = f"batch_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    batch_rec = BatchRecord(batch_id=batch_id, payments=records)
    BATCH_STORE[batch_id] = batch_rec

    # Schedule background worker
    background_tasks.add_task(execute_batch_in_background, batch_id)

    return BatchRunResponse(
        batch_id=batch_id,
        status="queued",
        total_payments=len(records),
        message=f"Batch {batch_id} with {len(records)} payments queued for background recovery processing.",
        created_at=batch_rec.created_at,
    )


@router.get("/{batch_id}/status", response_model=BatchStatusResponse)
async def get_batch_status(batch_id: str):
    """
    Poll the live progress and status distribution counts for a batch.
    """
    record = BATCH_STORE.get(batch_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch ID '{batch_id}' not found.",
        )

    return BatchStatusResponse(
        batch_id=record.batch_id,
        status=record.status,
        total_count=record.total_count,
        processed_count=record.processed_count,
        progress_pct=record.progress_pct,
        counts_by_status=record.counts_by_status,
        created_at=record.created_at,
        completed_at=record.completed_at,
    )


@router.get("/{batch_id}/results", response_model=BatchResultsResponse)
async def get_batch_results(batch_id: str):
    """
    Get the final state of every payment in the specified batch.
    """
    record = BATCH_STORE.get(batch_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch ID '{batch_id}' not found.",
        )

    return BatchResultsResponse(
        batch_id=record.batch_id,
        status=record.status,
        total_count=record.processed_count,
        results=record.results,
    )


@router.get("/{batch_id}/audit/{payment_id}", response_model=AuditTrailResponse)
async def get_payment_audit_trail(batch_id: str, payment_id: str):
    """
    Get the full audit trail (node transitions, decisions, reasons, tool calls)
    for a specific payment in the batch.
    """
    record = BATCH_STORE.get(batch_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch ID '{batch_id}' not found.",
        )

    payment_state = record.payments_by_id.get(payment_id)
    if not payment_state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment ID '{payment_id}' not found in batch '{batch_id}'.",
        )

    return AuditTrailResponse(
        batch_id=batch_id,
        payment_id=payment_id,
        customer_id=payment_state.get("customer_id"),
        customer_name=payment_state.get("customer_name"),
        amount=float(payment_state.get("amount", 0.0)),
        fail_category=payment_state.get("fail_category"),
        fail_explanation=payment_state.get("fail_explanation"),
        final_status=payment_state.get("status", "unknown"),
        final_action=payment_state.get("current_action"),
        stop_reason=payment_state.get("stop_reason"),
        recovered_amount=float(payment_state.get("recovered_amount", 0.0)),
        promise_to_pay_date=payment_state.get("promise_to_pay_date"),
        retry_count=int(payment_state.get("retry_count", 0)),
        audit_trail=payment_state.get("intervention_history", []),
        retry_history=payment_state.get("retry_history", []),
    )


@router.get("/{batch_id}/metrics", response_model=BatchMetricsResponse)
async def get_batch_metrics(batch_id: str):
    """
    Compute and return aggregate revenue recovery metrics:
    - total_amount_at_risk
    - total_recovered
    - recovery_rate_pct
    - avg_retries_to_recovery
    - escalation_rate
    - breakdown_by_fail_category
    """
    record = BATCH_STORE.get(batch_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch ID '{batch_id}' not found.",
        )

    results = record.results
    total_payments = len(results)
    if total_payments == 0:
        return BatchMetricsResponse(
            batch_id=batch_id,
            total_payments=0,
            total_amount_at_risk=0.0,
            total_recovered=0.0,
            recovery_rate_pct=0.0,
            avg_retries_to_recovery=0.0,
            escalation_rate=0.0,
            breakdown_by_fail_category={},
        )

    total_amount_at_risk = sum(float(r.get("amount", 0.0)) for r in results)
    total_recovered = sum(float(r.get("recovered_amount", 0.0)) for r in results)
    recovery_rate_pct = round((total_recovered / total_amount_at_risk * 100.0), 2) if total_amount_at_risk > 0 else 0.0

    # Escalations
    escalated_count = sum(1 for r in results if r.get("status") == PaymentStatus.ESCALATED.value)
    escalation_rate = round(escalated_count / total_payments, 3)

    # Average retries for recovered payments
    recovered_retries = [r.get("retry_count", 1) for r in results if r.get("status") == PaymentStatus.RECOVERED.value]
    avg_retries = round(sum(recovered_retries) / len(recovered_retries), 2) if recovered_retries else 0.0

    # Breakdown by category
    categories: Dict[str, CategoryMetric] = {}
    for r in results:
        cat = r.get("fail_category", "unknown")
        amt = float(r.get("amount", 0.0))
        rec_amt = float(r.get("recovered_amount", 0.0))
        st = r.get("status", "pending")

        if cat not in categories:
            categories[cat] = CategoryMetric(
                category=cat,
                total_count=0,
                total_amount=0.0,
                recovered_count=0,
                recovered_amount=0.0,
                recovery_rate_pct=0.0,
                escalated_count=0,
                in_progress_count=0,
                stopped_count=0,
            )

        m = categories[cat]
        m.total_count += 1
        m.total_amount += amt
        if st == PaymentStatus.RECOVERED.value:
            m.recovered_count += 1
            m.recovered_amount += rec_amt
        elif st == PaymentStatus.ESCALATED.value:
            m.escalated_count += 1
        elif st == PaymentStatus.IN_PROGRESS.value:
            m.in_progress_count += 1
        elif st == PaymentStatus.STOPPED.value:
            m.stopped_count += 1

    # Compute percentage per category
    for cat, m in categories.items():
        m.total_amount = round(m.total_amount, 2)
        m.recovered_amount = round(m.recovered_amount, 2)
        m.recovery_rate_pct = round((m.recovered_amount / m.total_amount * 100.0), 2) if m.total_amount > 0 else 0.0

    return BatchMetricsResponse(
        batch_id=batch_id,
        total_payments=total_payments,
        total_amount_at_risk=round(total_amount_at_risk, 2),
        total_recovered=round(total_recovered, 2),
        recovery_rate_pct=recovery_rate_pct,
        avg_retries_to_recovery=avg_retries,
        escalation_rate=escalation_rate,
        breakdown_by_fail_category=categories,
    )


@router.post("/reset")
async def reset_demo_dataset():
    """
    Reset Demo Endpoint:
    Clears all active batches from memory, generates 75 fresh synthetic failed payments,
    re-provisions live Razorpay test-mode orders, and prepares a clean slate for live judge demos.
    """
    global BATCH_STORE
    BATCH_STORE.clear()

    try:
        from data.generate_synthetic_batch import generate_synthetic_payments, save_dataset
        fresh_data = generate_synthetic_payments(count=75)
        save_dataset(fresh_data)
        logger.info("Fresh synthetic payment dataset (75 records) generated for demo reset.")

        # Provision fresh test orders
        from data.create_test_orders import provision_test_orders
        provision_test_orders(fresh_data, limit=15)

        return {
            "status": "reset",
            "message": "Demo reset successfully with 75 fresh failed payments & Razorpay test orders.",
            "total_payments": len(fresh_data),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error("Error during demo reset: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset demo dataset: {e}",
        )


@router.get("/{batch_id}/export")
async def export_batch_summary(batch_id: str):
    """
    Export Full Measured Results:
    Returns the comprehensive batch metadata, aggregate metrics, and every payment's
    complete chronological node-by-node audit trail for transparent verification.
    """
    record = BATCH_STORE.get(batch_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch ID '{batch_id}' not found.",
        )

    metrics = await get_batch_metrics(batch_id)

    return {
        "export_generated_at": datetime.now(timezone.utc).isoformat(),
        "batch_id": record.batch_id,
        "batch_status": record.status,
        "created_at": record.created_at,
        "completed_at": record.completed_at,
        "total_payments": record.total_count,
        "processed_payments": record.processed_count,
        "counts_by_status": record.counts_by_status,
        "aggregate_metrics": metrics.model_dump(),
        "payments_audit_trail": record.results,
    }

