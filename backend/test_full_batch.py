"""
Test full 75-record batch processing and metrics computation via FastAPI.
"""

import json
import os
import sys
import time
import httpx

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

client = httpx.Client(base_url="http://127.0.0.1:8000", timeout=60.0)

print("\n--- 1. Submitting 'all pending' Batch (75 Records) ---")
resp = client.post("/batch/run", json={"payment_ids": "all pending"})
print("POST /batch/run ->", resp.status_code)
data = resp.json()
print(json.dumps(data, indent=2))
batch_id = data["batch_id"]

print("\n--- 2. Live Polling Background Task Progress ---")
for attempt in range(40):
    st = client.get(f"/batch/{batch_id}/status").json()
    print(
        f"  [T+{attempt+1:02d}s] Progress: {st['processed_count']:>2}/{st['total_count']} ({st['progress_pct']:5.1f}%) | "
        f"Status: {st['status']:<9} | Live Counts: {st['counts_by_status']}"
    )
    if st["status"] == "completed":
        break
    time.sleep(1.0)

print("\n--- 3. Fetching Computed Aggregate ROI Metrics ---")
metrics = client.get(f"/batch/{batch_id}/metrics").json()
print(json.dumps(metrics, indent=2))
