"use client";

import React, { useState } from "react";
import { PendingApprovalItem, approvePayment } from "@/lib/api";
import {
  ShieldAlert,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  RotateCw,
  UserCheck,
} from "lucide-react";

interface PendingApprovalsCardProps {
  batchId: string;
  items: PendingApprovalItem[];
  onDecisionComplete: (paymentId: string, decision: "approve" | "reject") => void;
}

export function PendingApprovalsCard({
  batchId,
  items,
  onDecisionComplete,
}: PendingApprovalsCardProps) {
  const [actionLoading, setActionLoading] = useState<{ [paymentId: string]: string | null }>({});
  const [toastMsg, setToastMsg] = useState<{ text: string; type: "success" | "error" } | null>(null);

  if (!items || items.length === 0) {
    return null;
  }

  const handleDecision = async (paymentId: string, decision: "approve" | "reject") => {
    setActionLoading((prev) => ({ ...prev, [paymentId]: decision }));
    setToastMsg(null);
    try {
      await approvePayment(batchId, paymentId, decision, "Risk_Operations_Lead");
      setToastMsg({
        text: `Payment ${paymentId} successfully ${decision === "approve" ? "approved" : "rejected"}.`,
        type: "success",
      });
      setTimeout(() => setToastMsg(null), 4000);
      onDecisionComplete(paymentId, decision);
    } catch (err: any) {
      setToastMsg({
        text: err.message || `Failed to ${decision} payment`,
        type: "error",
      });
    } finally {
      setActionLoading((prev) => ({ ...prev, [paymentId]: null }));
    }
  };

  return (
    <div className="w-full bg-[var(--bg-surface)] rounded-xl border border-amber-500/40 shadow-card p-5 sm:p-6 mb-6 ring-2 ring-amber-400/20 animate-in fade-in duration-300">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-amber-500/20">
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-lg bg-amber-500/10 border border-amber-500/30 flex items-center justify-center flex-shrink-0 text-amber-700 dark:text-amber-400">
            <UserCheck className="w-5 h-5 text-amber-700 dark:text-amber-400" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="font-heading text-lg font-bold text-[var(--text-primary)] tracking-tight">
                Pending High-Value Approvals
              </h2>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-500/10 text-amber-700 dark:text-amber-300 border border-amber-500/30 animate-pulse">
                {items.length} Awaiting Review
              </span>
            </div>
            <p className="text-xs text-[var(--text-secondary)] mt-0.5 font-semibold">
              Transactions exceeding the ₹5,000.00 safety threshold require human authorization before automated tool execution.
            </p>
          </div>
        </div>
      </div>

      {/* Toast Alert */}
      {toastMsg && (
        <div
          className={`mt-3 p-3 rounded-lg text-xs font-semibold flex items-center gap-2 ${
            toastMsg.type === "success"
              ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border border-emerald-500/30"
              : "bg-red-500/10 text-red-700 dark:text-red-300 border border-red-500/30"
          }`}
        >
          {toastMsg.type === "success" ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400 flex-shrink-0" />
          ) : (
            <AlertTriangle className="w-4 h-4 text-red-600 dark:text-red-400 flex-shrink-0" />
          )}
          <span>{toastMsg.text}</span>
        </div>
      )}

      {/* List of Pending High-Value Items */}
      <div className="mt-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
        {items.map((item) => {
          const isApproving = actionLoading[item.payment_id] === "approve";
          const isRejecting = actionLoading[item.payment_id] === "reject";
          const isDisabled = isApproving || isRejecting;

          return (
            <div
              key={item.payment_id}
              className="p-4 rounded-lg border border-[var(--border-default)] hover:border-[var(--brand-accent)] bg-[var(--bg-surface-subtle)] flex flex-col justify-between shadow-sm transition-all"
            >
              <div>
                {/* Top Row: Customer & Amount */}
                <div className="flex items-start justify-between gap-2 mb-2">
                  <div>
                    <h3 className="text-xs font-bold text-[var(--text-primary)] leading-tight">
                      {item.customer_name || "Valued Customer"}
                    </h3>
                    <span className="font-mono text-xs text-[var(--text-muted)] font-semibold">
                      {item.payment_id}
                    </span>
                  </div>
                  <span className="px-2.5 py-1 rounded bg-[var(--brand-accent-subtle)] text-[var(--brand-primary)] border border-[var(--border-default)] font-bold text-xs whitespace-nowrap">
                    ₹{item.amount.toFixed(2)}
                  </span>
                </div>

                {/* Category & Proposed Action */}
                <div className="flex flex-wrap items-center gap-1.5 mb-2.5 text-xs">
                  <span className="px-2 py-0.5 rounded bg-[var(--bg-surface)] text-[var(--text-secondary)] border border-[var(--border-default)] font-semibold uppercase">
                    {item.fail_category || "Technical Error"}
                  </span>
                  <span className="text-[var(--text-muted)]">➔</span>
                  <span className="px-2 py-0.5 rounded bg-[var(--brand-accent-subtle)] text-[var(--brand-primary)] border border-[var(--brand-accent)]/20 font-bold uppercase">
                    {item.proposed_action || "Retry Now"}
                  </span>
                </div>

                {/* Gated Reason */}
                <p className="text-xs text-[var(--text-secondary)] bg-amber-500/10 border border-amber-500/30 rounded p-2 mb-3 leading-snug font-medium">
                  ⚠️ {item.approval_reason}
                </p>
              </div>

              {/* Action Buttons */}
              <div className="grid grid-cols-2 gap-2 pt-2 border-t border-[var(--border-default)]">
                <button
                  type="button"
                  onClick={() => handleDecision(item.payment_id, "approve")}
                  disabled={isDisabled}
                  className="flex items-center justify-center gap-1.5 py-2 px-3 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white rounded-lg text-xs font-bold transition-all shadow-sm active:scale-[0.98]"
                >
                  {isApproving ? (
                    <RotateCw className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <CheckCircle2 className="w-3.5 h-3.5" />
                  )}
                  <span>Approve</span>
                </button>

                <button
                  type="button"
                  onClick={() => handleDecision(item.payment_id, "reject")}
                  disabled={isDisabled}
                  className="flex items-center justify-center gap-1.5 py-2 px-3 bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white rounded-lg text-xs font-bold transition-all shadow-sm active:scale-[0.98]"
                >
                  {isRejecting ? (
                    <RotateCw className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <XCircle className="w-3.5 h-3.5" />
                  )}
                  <span>Reject</span>
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
