/**
 * Frontend API client for Revenue Recovery Agent FastAPI backend.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export interface BatchRunResponse {
  batch_id: string;
  status: string;
  total_payments: number;
  message: string;
  created_at: string;
}

export interface BatchStatusResponse {
  batch_id: string;
  status: "queued" | "running" | "completed" | "failed";
  total_count: number;
  processed_count: number;
  progress_pct: number;
  counts_by_status: {
    pending: number;
    in_progress: number;
    recovered: number;
    escalated: number;
    stopped: number;
    awaiting_promise?: number;
  };
  created_at: string;
  completed_at?: string | null;
}

export interface PaymentResult {
  payment_id: string;
  customer_id?: string;
  customer_name?: string;
  amount: number;
  subscription_id?: string;
  fail_reason?: string;
  fail_category?: string;
  fail_explanation?: string;
  current_action?: string;
  status: "pending" | "in_progress" | "recovered" | "escalated" | "stopped" | "awaiting_promise";
  retry_count: number;
  stop_reason?: string | null;
  stop_reason_category?: "max_retries" | "max_days" | "cost_exceeds_value" | "compliance_block" | string | null;
  recovered_amount?: number;
  promise_to_pay_date?: string | null;
  fail_timestamp?: string;
  intervention_history?: AuditStep[];
  summary_explanation?: string | null;
}

export interface AuditStep {
  node: string;
  decision: string;
  reason?: string;
  tool_called?: string | null;
  tool_result?: any;
  status?: string;
  timestamp?: string;
}

export interface AuditTrailResponse {
  batch_id: string;
  payment_id: string;
  customer_id?: string;
  customer_name?: string;
  amount: number;
  fail_category?: string;
  fail_explanation?: string;
  final_status: string;
  final_action?: string;
  stop_reason?: string;
  stop_reason_category?: string | null;
  recovered_amount: number;
  promise_to_pay_date?: string;
  retry_count: number;
  audit_trail: AuditStep[];
  retry_history: any[];
}

export interface CategoryMetric {
  category: string;
  total_count: number;
  total_amount: number;
  recovered_count: number;
  recovered_amount: number;
  recovery_rate_pct: number;
  escalated_count: number;
  in_progress_count: number;
  stopped_count: number;
  awaiting_promise_count?: number;
}

export interface BatchMetricsResponse {
  batch_id: string;
  total_payments: number;
  total_amount_at_risk: number;
  total_recovered: number;
  recovery_rate_pct: number;
  avg_retries_to_recovery: number;
  escalation_rate: number;
  baseline_recovered?: number;
  baseline_recovery_rate?: number;
  agent_recovered?: number;
  agent_recovery_rate?: number;
  improvement?: number;
  cost_aware_stops?: number;
  estimated_savings?: number;
  breakdown_by_fail_category: Record<string, CategoryMetric>;
}

// ── Promise Tracker Types ──────────────────────────────────────────

export interface PromiseTrackerItem {
  payment_id: string;
  customer_id?: string;
  customer_name?: string;
  amount: number;
  fail_category?: string;
  current_action?: string;
  promise_to_pay_date?: string;
  status: string;
  summary_explanation?: string;
}

export interface PromiseTrackerResponse {
  batch_id: string;
  total_awaiting: number;
  promise_payments: PromiseTrackerItem[];
}

export interface FastForwardTransition {
  payment_id: string;
  customer_name?: string;
  amount: number;
  promise_date?: string;
  outcome: "promise_kept" | "promise_broken";
  new_status: string;
  reason: string;
}

export interface FastForwardResponse {
  batch_id: string;
  days_forwarded: number;
  simulated_date: string;
  total_evaluated: number;
  promises_kept: number;
  promises_broken: number;
  transitions: FastForwardTransition[];
}

export async function runBatch(payment_ids: string[] | string = "all pending"): Promise<BatchRunResponse> {
  const res = await fetch(`${API_BASE}/batch/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ payment_ids }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to trigger batch run");
  }
  return res.json();
}

export async function getBatchStatus(batch_id: string): Promise<BatchStatusResponse> {
  const res = await fetch(`${API_BASE}/batch/${batch_id}/status`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch batch status");
  return res.json();
}

export async function getBatchResults(batch_id: string): Promise<{ batch_id: string; status: string; total_count: number; results: PaymentResult[] }> {
  const res = await fetch(`${API_BASE}/batch/${batch_id}/results`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch batch results");
  return res.json();
}

export async function getPaymentAudit(batch_id: string, payment_id: string): Promise<AuditTrailResponse> {
  const res = await fetch(`${API_BASE}/batch/${batch_id}/audit/${payment_id}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch payment audit trail");
  return res.json();
}

export async function getBatchMetrics(batch_id: string): Promise<BatchMetricsResponse> {
  const res = await fetch(`${API_BASE}/batch/${batch_id}/metrics`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch batch metrics");
  return res.json();
}

export async function resetDemo(): Promise<{ status: string; message: string; total_payments: number }> {
  const res = await fetch(`${API_BASE}/batch/reset`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to reset demo");
  }
  return res.json();
}

export interface TimelineStep {
  step_number: number;
  title: string;
  status: "error" | "fallback" | "success" | "escalated" | "info";
  icon: string;
  description: string;
  details?: any;
}

export interface ResilienceTestResponse {
  test_id: string;
  failure_type: string;
  scenario_description: string;
  payment_id: string;
  customer_name: string;
  amount: number;
  initial_status: string;
  final_status: string;
  final_action: string;
  recovered_amount: number;
  stop_reason?: string | null;
  timeline_summary: string[];
  timeline_steps: TimelineStep[];
  audit_trail: AuditStep[];
  resilience_verified: boolean;
  message: string;
}

export async function triggerResilienceTest(
  failure_type: string = "API_TIMEOUT",
  amount: number = 1499.0,
  customer_name: string = "Rohan Deshmukh"
): Promise<ResilienceTestResponse> {
  const res = await fetch(`${API_BASE}/demo/trigger-resilience-test`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ failure_type, amount, customer_name }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to trigger resilience test");
  }
  return res.json();
}

export async function exportBatchSummary(batch_id: string): Promise<any> {
  const res = await fetch(`${API_BASE}/batch/${batch_id}/export`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to export batch summary");
  return res.json();
}

export interface PendingApprovalItem {
  payment_id: string;
  customer_id?: string;
  customer_name?: string;
  amount: number;
  subscription_id?: string;
  fail_category?: string;
  fail_reason?: string;
  proposed_action: string;
  approval_reason: string;
  status: string;
  timestamp: string;
}

export interface PendingApprovalsResponse {
  batch_id: string;
  total_pending: number;
  pending_approvals: PendingApprovalItem[];
}

export async function getPendingApprovals(batch_id: string): Promise<PendingApprovalsResponse> {
  const res = await fetch(`${API_BASE}/batch/${batch_id}/pending-approvals`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch pending approvals");
  return res.json();
}

export async function approvePayment(
  batch_id: string,
  payment_id: string,
  decision: "approve" | "reject",
  reviewer: string = "Risk_Operations_Lead"
): Promise<any> {
  const res = await fetch(`${API_BASE}/batch/${batch_id}/approve/${payment_id}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ decision, reviewer }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Failed to ${decision} payment`);
  }
  return res.json();
}

// ── Promise Tracker & Fast-Forward API ─────────────────────────────

export async function getPromiseTracker(batch_id: string): Promise<PromiseTrackerResponse> {
  const res = await fetch(`${API_BASE}/batch/${batch_id}/promise-tracker`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch promise tracker data");
  return res.json();
}

export async function fastForwardBatch(
  batch_id: string,
  days_offset: number = 5
): Promise<FastForwardResponse> {
  const res = await fetch(`${API_BASE}/batch/${batch_id}/fast-forward`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ days_offset }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to fast-forward batch");
  }
  return res.json();
}
