"use client";

import React, { useState } from "react";
import {
  PromiseTrackerItem,
  FastForwardTransition,
  fastForwardBatch,
} from "@/lib/api";
import {
  Clock,
  FastForward,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  RotateCw,
  CalendarClock,
  ArrowRight,
  Hourglass,
} from "lucide-react";

interface PromiseTrackerCardProps {
  batchId: string;
  items: PromiseTrackerItem[];
  onFastForwardComplete: () => void;
}

export function PromiseTrackerCard({
  batchId,
  items,
  onFastForwardComplete,
}: PromiseTrackerCardProps) {
  const [isForwarding, setIsForwarding] = useState(false);
  const [transitions, setTransitions] = useState<FastForwardTransition[]>([]);
  const [forwardResult, setForwardResult] = useState<{
    kept: number;
    broken: number;
    simulatedDate: string;
  } | null>(null);
  const [toastMsg, setToastMsg] = useState<{
    text: string;
    type: "success" | "error";
  } | null>(null);

  // Don't render if there are no awaiting_promise items AND no transition results to show
  if ((!items || items.length === 0) && transitions.length === 0) {
    return null;
  }

  const handleFastForward = async () => {
    setIsForwarding(true);
    setToastMsg(null);
    setTransitions([]);
    setForwardResult(null);

    try {
      const result = await fastForwardBatch(batchId, 5);
      setTransitions(result.transitions);
      setForwardResult({
        kept: result.promises_kept,
        broken: result.promises_broken,
        simulatedDate: result.simulated_date,
      });
      setToastMsg({
        text: `Fast-forwarded +${result.days_forwarded} days → ${result.promises_kept} kept, ${result.promises_broken} broken`,
        type: "success",
      });
      setTimeout(() => {
        setToastMsg(null), 6000;
      });
      onFastForwardComplete();
    } catch (err: any) {
      setToastMsg({
        text: err.message || "Failed to fast-forward batch",
        type: "error",
      });
      setTimeout(() => setToastMsg(null), 5000);
    } finally {
      setIsForwarding(false);
    }
  };

  return (
    <div className="rounded-xl bg-[var(--bg-surface)] shadow-card border border-[var(--border-default)] overflow-hidden">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between px-6 py-4 border-b border-[var(--border-default)] bg-gradient-to-r from-amber-500/10 to-orange-500/5">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-amber-500/15 text-amber-600 dark:text-amber-400 border border-amber-500/30">
            <Hourglass className="h-4.5 w-4.5" />
          </div>
          <div>
            <h3 className="font-heading text-base font-semibold text-[var(--text-primary)] leading-tight">
              Promise-to-Pay Tracker
            </h3>
            <p className="text-xs font-body text-[var(--text-secondary)] mt-0.5 font-semibold">
              {items.length > 0
                ? `${items.length} payment${items.length !== 1 ? "s" : ""} awaiting promised payment date`
                : "All promises resolved"}
            </p>
          </div>
        </div>

        {/* Fast-Forward Button */}
        {items.length > 0 && (
          <button
            onClick={handleFastForward}
            disabled={isForwarding}
            className="flex items-center gap-2 h-9 px-4 rounded-lg bg-amber-500 hover:bg-amber-600 text-white font-heading text-xs font-semibold shadow-card transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
          >
            {isForwarding ? (
              <>
                <RotateCw className="h-4 w-4 animate-spin" />
                <span>Simulating...</span>
              </>
            ) : (
              <>
                <FastForward className="h-4 w-4" />
                <span>Fast-Forward Time (+5 days)</span>
              </>
            )}
          </button>
        )}
      </div>

      {/* Toast Message */}
      {toastMsg && (
        <div
          className={`mx-6 mt-4 flex items-center gap-2 rounded-md px-4 py-2.5 text-xs font-body font-semibold animate-in fade-in duration-200 ${
            toastMsg.type === "success"
              ? "bg-emerald-500/10 border border-emerald-500/30 text-emerald-700 dark:text-emerald-300"
              : "bg-red-500/10 border border-red-500/30 text-red-700 dark:text-red-300"
          }`}
        >
          {toastMsg.type === "success" ? (
            <CheckCircle2 className="h-4 w-4 shrink-0" />
          ) : (
            <AlertTriangle className="h-4 w-4 shrink-0" />
          )}
          <span>{toastMsg.text}</span>
        </div>
      )}

      {/* Fast-Forward Results Summary */}
      {forwardResult && transitions.length > 0 && (
        <div className="mx-6 mt-4 flex items-center gap-4 rounded-lg bg-gradient-to-r from-[var(--brand-accent-subtle)] to-amber-500/10 border border-[var(--border-default)] px-4 py-3">
          <div className="flex items-center gap-2 text-xs font-body font-bold text-[var(--text-secondary)]">
            <CalendarClock className="h-4 w-4 text-[var(--brand-primary)]" />
            <span>Simulated: {forwardResult.simulatedDate}</span>
          </div>
          <div className="h-4 w-px bg-[var(--border-default)]" />
          <div className="flex items-center gap-1.5 text-xs font-body font-bold text-emerald-600 dark:text-emerald-400">
            <CheckCircle2 className="h-3.5 w-3.5" />
            <span>{forwardResult.kept} Kept</span>
          </div>
          <div className="flex items-center gap-1.5 text-xs font-body font-bold text-red-500 dark:text-red-400">
            <XCircle className="h-3.5 w-3.5" />
            <span>{forwardResult.broken} Broken</span>
          </div>
        </div>
      )}

      {/* Transitions Table (shown after fast-forward) */}
      {transitions.length > 0 && (
        <div className="px-6 py-4">
          <h4 className="text-xs font-heading font-semibold text-[var(--text-secondary)] mb-3">
            Promise Resolution Results
          </h4>
          <div className="overflow-x-auto rounded-lg border border-[var(--border-default)]">
            <table className="w-full text-left">
              <thead>
                <tr className="bg-[var(--bg-surface-subtle)] text-xs font-heading font-semibold text-[var(--text-secondary)] uppercase tracking-wider">
                  <th className="px-4 py-2.5">Payment ID</th>
                  <th className="px-4 py-2.5">Customer</th>
                  <th className="px-4 py-2.5 text-right">Amount</th>
                  <th className="px-4 py-2.5">Promise Date</th>
                  <th className="px-4 py-2.5">Outcome</th>
                  <th className="px-4 py-2.5">Reason</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border-subtle)]">
                {transitions.map((t) => (
                  <tr
                    key={t.payment_id}
                    className={`text-xs font-body transition-colors duration-300 ${
                      t.outcome === "promise_kept"
                        ? "bg-emerald-500/10"
                        : "bg-red-500/10"
                    }`}
                  >
                    <td className="px-4 py-3 font-mono text-xs font-semibold text-[var(--text-primary)]">
                      {t.payment_id}
                    </td>
                    <td className="px-4 py-3 font-semibold text-[var(--text-primary)]">
                      {t.customer_name || "—"}
                    </td>
                    <td className="px-4 py-3 text-right font-mono font-semibold text-[var(--text-primary)]">
                      ₹{t.amount.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-[var(--text-secondary)] font-semibold">
                      {t.promise_date || "—"}
                    </td>
                    <td className="px-4 py-3">
                      {t.outcome === "promise_kept" ? (
                        <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/20 border border-emerald-500/40 px-2.5 py-1 text-xs font-heading font-semibold text-emerald-700 dark:text-emerald-300">
                          <CheckCircle2 className="h-3 w-3" />
                          Recovered
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 rounded-full bg-red-500/20 border border-red-500/40 px-2.5 py-1 text-xs font-heading font-semibold text-red-700 dark:text-red-300">
                          <XCircle className="h-3 w-3" />
                          Escalated
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-xs text-[var(--text-secondary)] font-semibold max-w-[250px] truncate">
                      {t.reason}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Active Awaiting Promise Table (before fast-forward) */}
      {items.length > 0 && transitions.length === 0 && (
        <div className="px-6 py-4">
          <div className="overflow-x-auto rounded-lg border border-[var(--border-default)]">
            <table className="w-full text-left">
              <thead>
                <tr className="bg-[var(--bg-surface-subtle)] text-xs font-heading font-semibold text-[var(--text-secondary)] uppercase tracking-wider">
                  <th className="px-4 py-2.5">Payment ID</th>
                  <th className="px-4 py-2.5">Customer</th>
                  <th className="px-4 py-2.5 text-right">Amount</th>
                  <th className="px-4 py-2.5">Category</th>
                  <th className="px-4 py-2.5">Promise Date</th>
                  <th className="px-4 py-2.5">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border-subtle)]">
                {items.map((item) => (
                  <tr key={item.payment_id} className="text-xs font-body hover:bg-amber-500/5 transition-colors">
                    <td className="px-4 py-3 font-mono text-xs font-semibold text-[var(--text-primary)]">
                      {item.payment_id}
                    </td>
                    <td className="px-4 py-3 font-semibold text-[var(--text-primary)]">
                      {item.customer_name || "—"}
                    </td>
                    <td className="px-4 py-3 text-right font-mono font-semibold text-[var(--text-primary)]">
                      ₹{item.amount.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                    </td>
                    <td className="px-4 py-3 text-xs font-semibold text-[var(--text-secondary)]">
                      {item.fail_category?.replace(/_/g, " ") || "—"}
                    </td>
                    <td className="px-4 py-3">
                      <span className="inline-flex items-center gap-1.5 font-mono text-xs font-semibold text-amber-700 dark:text-amber-300 bg-amber-500/10 border border-amber-500/30 rounded-md px-2 py-0.5">
                        <Clock className="h-3 w-3" />
                        {item.promise_to_pay_date || "—"}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-500/10 border border-amber-500/30 px-2.5 py-1 text-xs font-heading font-semibold text-amber-700 dark:text-amber-300">
                        <Hourglass className="h-3 w-3" />
                        Awaiting
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Instructional hint */}
          <div className="mt-3 flex items-center gap-2 text-xs font-body text-[var(--text-muted)] font-semibold">
            <ArrowRight className="h-3.5 w-3.5 text-amber-500" />
            <span>
              Click <strong>Fast-Forward Time</strong> to simulate {items.length} promise{items.length !== 1 ? "s" : ""} being evaluated after the deadline.
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
