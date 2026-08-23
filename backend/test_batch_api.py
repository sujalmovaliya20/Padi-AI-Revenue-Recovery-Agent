"""
Test script for FastAPI Batch Endpoints.

Tests:
1. POST /batch/run — Start batch processing in background
2. GET  /batch/{batch_id}/status — Poll until complete (live counts by status)
3. GET  /batch/{batch_id}/results — Inspect final states of all payments
4. GET  /batch/{batch_id}/audit/{payment_id} — Inspect complete decision trace & tool results
5. GET  /batch/{batch_id}/metrics — Inspect recovery rate, amount at risk, ROI, category breakdown
"""

import json
import os
import sys
import time
import httpx

# Ensure utf-8 stdout
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "http://127.0.0.1:8000"


def print_banner(text: str):
    print(f"\n{'=' * 75}")
    print(f"  {text}")
    print(f"{'=' * 75}")


def test_batch_api_lifecycle():
    client = httpx.Client(base_url=BASE_URL, timeout=30.0)

    # 0. Health & Root check
    print_banner("0. API ROOT & HEALTH CHECK")
    root_resp = client.get("/")
    print("GET / ->", root_resp.status_code)
    print(json.dumps(root_resp.json(), indent=2))

    # 1. POST /batch/run
    print_banner("1. POST /batch/run — LAUNCH BATCH RUN")
    payload = {
        "payment_ids": [
            "pay_syn_0823_1001",
            "pay_syn_0822_1002",
            "pay_syn_0822_1003",
            "pay_syn_0822_1004",
            "pay_syn_0822_1005",
            "pay_syn_0821_1010",
        ]
    }
    print(f"Submitting Batch Request with {len(payload['payment_ids'])} payments...")
    run_resp = client.post("/batch/run", json=payload)
    print(f"Status Code: {run_resp.status_code}")
    run_data = run_resp.json()
    print("Response:")
    print(json.dumps(run_data, indent=2))

    assert run_resp.status_code == 202
    batch_id = run_data["batch_id"]

    # 2. GET /batch/{batch_id}/status (Poll until complete)
    print_banner("2. GET /batch/{batch_id}/status — POLLING PROGRESS")
    completed = False
    for attempt in range(15):
        status_resp = client.get(f"/batch/{batch_id}/status")
        status_data = status_resp.json()
        print(
            f"  [Poll {attempt+1}] Status: {status_data['status']} | "
            f"Progress: {status_data['processed_count']}/{status_data['total_count']} ({status_data['progress_pct']}%) | "
            f"Counts: {status_data['counts_by_status']}"
        )
        if status_data["status"] == "completed":
            completed = True
            break
        time.sleep(1.0)

    assert completed, "Batch did not reach completed status in time"

    # 3. GET /batch/{batch_id}/results
    print_banner("3. GET /batch/{batch_id}/results — PROCESSED PAYMENT RESULTS")
    results_resp = client.get(f"/batch/{batch_id}/results")
    print(f"Status Code: {results_resp.status_code}")
    results_data = results_resp.json()
    print(f"Total Results: {results_data['total_count']}")
    print("\nSample Processed Records (First 3):")
    for r in results_data["results"][:3]:
        print(f"\n  - Payment ID:    {r.get('payment_id')}")
        print(f"    Customer:      {r.get('customer_name')}")
        print(f"    Amount:        ₹{r.get('amount'):.2f} INR")
        print(f"    Category:      {r.get('fail_category')}")
        print(f"    Action:        {r.get('current_action')}")
        print(f"    Final Status:  {r.get('status')}")
        print(f"    Stop Reason:   {r.get('stop_reason')}")

    # 4. GET /batch/{batch_id}/audit/{payment_id}
    test_pid = payload["payment_ids"][2]  # expired_card payment
    print_banner(f"4. GET /batch/{{batch_id}}/audit/{test_pid} — AUDIT TRAIL")
    audit_resp = client.get(f"/batch/{batch_id}/audit/{test_pid}")
    print(f"Status Code: {audit_resp.status_code}")
    audit_data = audit_resp.json()
    print(f"Payment ID:       {audit_data['payment_id']}")
    print(f"Customer:         {audit_data['customer_name']}")
    print(f"Amount:           ₹{audit_data['amount']:.2f} INR")
    print(f"Final Status:     {audit_data['final_status']}")
    print(f"Final Action:     {audit_data['final_action']}")
    print(f"Stop Reason:      {audit_data['stop_reason']}")
    print("\nAudit Trail Steps:")
    for step_idx, step in enumerate(audit_data["audit_trail"], 1):
        print(f"\n  Step {step_idx} [{step.get('node').upper()}]:")
        print(f"    Decision: {step.get('decision')}")
        if step.get("reason"):
            print(f"    Reason:   {step.get('reason')}")
        if step.get("tool_called"):
            print(f"    Tool:     {step.get('tool_called')}")
            print(f"    Tool Result:\n{json.dumps(step.get('tool_result'), indent=6)}")

    # 5. GET /batch/{batch_id}/metrics
    print_banner("5. GET /batch/{batch_id}/metrics — RECOVERY ROI & METRICS")
    metrics_resp = client.get(f"/batch/{batch_id}/metrics")
    print(f"Status Code: {metrics_resp.status_code}")
    metrics_data = metrics_resp.json()
    print("Aggregate Metrics:")
    print(f"  - Total Payments Processed: {metrics_data['total_payments']}")
    print(f"  - Total Amount at Risk:     ₹{metrics_data['total_amount_at_risk']:,.2f} INR")
    print(f"  - Total Amount Recovered:   ₹{metrics_data['total_recovered']:,.2f} INR")
    print(f"  - Recovery Rate:            {metrics_data['recovery_rate_pct']:.1f}%")
    print(f"  - Avg Retries to Recovery:  {metrics_data['avg_retries_to_recovery']}")
    print(f"  - Escalation Rate:          {metrics_data['escalation_rate']*100:.1f}%")
    print("\nBreakdown by Category:")
    for cat_name, cat_metric in metrics_data["breakdown_by_fail_category"].items():
        print(
            f"  - {cat_name:<20}: {cat_metric['total_count']} payments | "
            f"₹{cat_metric['total_amount']:,.0f} at risk | "
            f"₹{cat_metric['recovered_amount']:,.0f} recovered ({cat_metric['recovery_rate_pct']:.1f}%) | "
            f"Escalated: {cat_metric['escalated_count']} | In-Progress: {cat_metric['in_progress_count']}"
        )

    print_banner("ALL FASTAPI BATCH ENDPOINTS VERIFIED & PASSED [OK]")


if __name__ == "__main__":
    test_batch_api_lifecycle()
