"use client";

import React, { useState } from "react";
import { triggerResilienceTest, ResilienceTestResponse, TimelineStep } from "@/lib/api";
import {
  ShieldAlert,
  Play,
  RotateCcw,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Terminal,
} from "lucide-react";

interface ResilienceTestCardProps {
  onTestComplete?: (data: ResilienceTestResponse) => void;
}

const SCENARIOS = [
  {
    id: "API_TIMEOUT",
    label: "⏱️ Gateway Timeout",
    shortDesc: "Simulates upstream gateway timeout (30s delay) on attempt 1",
    fallbackDesc: "🔄 Auto-retries with backoff ➔ Recovers on attempt 2",
  },
  {
    id: "RATE_LIMIT",
    label: "🚦 HTTP 429 Rate Limit",
    shortDesc: "Simulates API quota exceeded under high burst traffic",
    fallbackDesc: "⏳ Auto-queues for delayed retry with backoff",
  },
  {
    id: "INVALID_ORDER",
    label: "🚫 Invalid Order ID",
    shortDesc: "Simulates retry against bad or non-existent order ID",
    fallbackDesc: "🛡️ Auto-escalates to human queue without crashing",
  },
];

export function ResilienceTestCard({ onTestComplete }: ResilienceTestCardProps) {
  const [selectedFailure, setSelectedFailure] = useState<string>("API_TIMEOUT");
  const [loading, setLoading] = useState<boolean>(false);
  const [result, setResult] = useState<ResilienceTestResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showJsonAudit, setShowJsonAudit] = useState<boolean>(false);

  const handleRunTest = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await triggerResilienceTest(selectedFailure);
      setResult(data);
      if (onTestComplete) {
        onTestComplete(data);
      }
    } catch (err: any) {
      setError(err.message || "Failed to execute resilience test");
    } finally {
      setLoading(false);
    }
  };

  const getStepBg = (status: TimelineStep["status"]) => {
    switch (status) {
      case "error":
        return "border-red-500/30 bg-red-500/10 text-red-700 dark:text-red-300";
      case "fallback":
        return "border-[var(--brand-accent)]/30 bg-[var(--brand-accent-subtle)] text-[var(--brand-primary)]";
      case "success":
        return "border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300";
      case "escalated":
        return "border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300";
      default:
        return "border-[var(--border-default)] bg-[var(--bg-surface-subtle)] text-[var(--text-primary)]";
    }
  };

  const getBadgeColor = (status: TimelineStep["status"]) => {
    switch (status) {
      case "error":
        return "bg-red-500/20 text-red-700 dark:text-red-300 border border-red-500/30";
      case "fallback":
        return "bg-[var(--brand-accent-subtle)] text-[var(--brand-primary)] border border-[var(--brand-accent)]/30";
      case "success":
        return "bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 border border-emerald-500/30";
      case "escalated":
        return "bg-amber-500/20 text-amber-700 dark:text-amber-300 border border-amber-500/30";
      default:
        return "bg-[var(--bg-surface)] text-[var(--text-secondary)] border border-[var(--border-default)]";
    }
  };

  return (
    <div className="w-full bg-[var(--bg-surface)] rounded-xl border border-[var(--border-default)] shadow-card p-5 sm:p-6 mb-6">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[var(--border-default)]">
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-lg bg-[var(--brand-accent-subtle)] border border-[var(--border-default)] flex items-center justify-center flex-shrink-0 text-[var(--brand-primary)]">
            <ShieldAlert className="w-5 h-5 text-[var(--brand-primary)]" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="font-heading text-lg font-bold text-[var(--text-primary)] tracking-tight">
                Resilience & Fault-Tolerance Test
              </h2>
              <span className="px-2 py-0.5 rounded text-xs font-bold uppercase tracking-wider bg-[var(--brand-accent-subtle)] text-[var(--brand-primary)] border border-[var(--border-default)]">
                Live Verification
              </span>
            </div>
            <p className="text-xs text-[var(--text-secondary)] mt-0.5 font-semibold">
              Demonstrates autonomous exception interception and graceful fallback without batch crashes.
            </p>
          </div>
        </div>

        {/* CTA Trigger */}
        <div className="flex items-center gap-3">
          <button
            onClick={handleRunTest}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2.5 bg-[var(--brand-primary)] hover:bg-[var(--brand-accent)] disabled:opacity-50 text-white rounded-lg text-xs font-semibold transition-all shadow-card whitespace-nowrap active:scale-[0.98]"
          >
            {loading ? (
              <>
                <RotateCcw className="w-4 h-4 animate-spin" />
                <span>Injecting & Testing...</span>
              </>
            ) : (
              <>
                <Play className="w-4 h-4 fill-current" />
                <span>Run Resilience Test</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Scenario Selection Pills */}
      <div className="mt-4">
        <label className="text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wider mb-2 block">
          Select Fault Scenario to Inject:
        </label>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5">
          {SCENARIOS.map((sc) => {
            const isSelected = selectedFailure === sc.id;
            return (
              <button
                key={sc.id}
                type="button"
                onClick={() => setSelectedFailure(sc.id)}
                className={`p-3 rounded-lg border text-left transition-all ${
                  isSelected
                    ? "border-[var(--brand-primary)] bg-[var(--brand-accent-subtle)] ring-1 ring-[var(--brand-primary)]"
                    : "border-[var(--border-default)] hover:border-[var(--brand-accent)] bg-[var(--bg-surface)]"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-[var(--text-primary)]">{sc.label}</span>
                  {isSelected && (
                    <span className="w-2 h-2 rounded-full bg-[var(--brand-primary)]" />
                  )}
                </div>
                <p className="text-xs text-[var(--text-secondary)] mt-1 leading-snug">{sc.shortDesc}</p>
                <div className="text-xs font-semibold text-[var(--brand-primary)] mt-2 pt-1 border-t border-[var(--border-subtle)]">
                  {sc.fallbackDesc}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Error Message if any */}
      {error && (
        <div className="mt-4 p-3 bg-red-500/10 border border-red-500/30 text-red-700 dark:text-red-300 rounded-lg text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 flex-shrink-0 text-red-600 dark:text-red-400" />
          <span>{error}</span>
        </div>
      )}

      {/* Results & Mini Timeline */}
      {result && (
        <div className="mt-5 pt-4 border-t border-[var(--border-default)] animate-in fade-in duration-300">
          {/* Summary Status Strip */}
          <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-[var(--bg-surface-subtle)] border border-[var(--border-default)] rounded-lg mb-4">
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-[var(--text-secondary)]">Executed Trace:</span>
              <span className="text-xs font-mono font-semibold text-[var(--text-primary)] bg-[var(--bg-surface)] px-2 py-0.5 rounded border border-[var(--border-default)]">
                {result.payment_id}
              </span>
              <span className="text-xs text-[var(--text-secondary)] font-semibold">({result.customer_name} — ₹{result.amount.toFixed(2)})</span>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-[var(--text-secondary)]">Final Outcome:</span>
              <span
                className={`px-2.5 py-0.5 rounded text-xs font-bold uppercase ${
                  result.final_status === "recovered"
                    ? "bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 border border-emerald-500/40"
                    : result.final_status === "escalated"
                    ? "bg-amber-500/20 text-amber-700 dark:text-amber-300 border border-amber-500/40"
                    : "bg-[var(--brand-accent-subtle)] text-[var(--brand-primary)] border border-[var(--border-default)]"
                }`}
              >
                {result.final_status}
              </span>
            </div>
          </div>

          {/* Mini Timeline Visualization */}
          <div className="mb-4">
            <h3 className="text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wider mb-2.5">
              Autonomous Resilience Execution Timeline:
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 relative">
              {result.timeline_steps.map((step, idx) => (
                <div
                  key={idx}
                  className={`p-3.5 rounded-lg border flex flex-col justify-between ${getStepBg(
                    step.status
                  )} shadow-card relative`}
                >
                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-xs font-bold uppercase tracking-wider opacity-80">
                        Step {step.step_number}
                      </span>
                      <span className={`px-2 py-0.5 rounded text-xs font-bold ${getBadgeColor(step.status)}`}>
                        {step.status.toUpperCase()}
                      </span>
                    </div>
                    <div className="text-xs font-bold mb-1 flex items-center gap-1.5">
                      <span>{step.title}</span>
                    </div>
                    <p className="text-xs opacity-90 leading-relaxed font-semibold">{step.description}</p>
                  </div>

                  {step.details && (
                    <div className="mt-2.5 pt-2 border-t border-current/10 text-xs font-mono opacity-80">
                      {Object.entries(step.details).map(([k, v]) => (
                        <div key={k} className="truncate">
                          <span className="font-semibold">{k}:</span> {String(v)}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Raw JSON Audit Trace Toggle */}
          <div className="mt-3">
            <button
              onClick={() => setShowJsonAudit(!showJsonAudit)}
              className="flex items-center gap-1.5 text-xs font-semibold text-[var(--brand-primary)] hover:text-[var(--brand-accent)] transition-colors"
            >
              <Terminal className="w-3.5 h-3.5" />
              <span>{showJsonAudit ? "Hide Technical Audit Payload" : "View Technical Audit Payload (JSON)"}</span>
              {showJsonAudit ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            </button>

            {showJsonAudit && (
              <pre className="mt-2 p-3 bg-[var(--bg-surface-elevated)] text-[var(--text-primary)] border border-[var(--border-default)] rounded-lg text-xs font-mono overflow-x-auto max-h-64">
                {JSON.stringify(result, null, 2)}
              </pre>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
