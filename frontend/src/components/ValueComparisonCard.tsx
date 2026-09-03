"use client";

import React from "react";
import { BatchMetricsResponse } from "@/lib/api";
import { Sparkles, TrendingUp, XCircle, CheckCircle2, ArrowRight } from "lucide-react";

interface ValueComparisonCardProps {
  metrics: BatchMetricsResponse | null;
  loading?: boolean;
}

export function ValueComparisonCard({ metrics, loading }: ValueComparisonCardProps) {
  if (!metrics || metrics.total_payments === 0) {
    return null;
  }

  const atRisk = metrics.total_amount_at_risk || 0;
  const agentRecovered = metrics.agent_recovered ?? metrics.total_recovered ?? 0;
  const recoveryRate = metrics.agent_recovery_rate ?? metrics.recovery_rate_pct ?? 0;
  const baselineRecovered = metrics.baseline_recovered ?? 0;
  const improvement = metrics.improvement ?? agentRecovered;

  // Max scale for the comparative bar chart is the total amount at risk
  const maxAmount = atRisk > 0 ? atRisk : 1;
  const baselinePct = (baselineRecovered / maxAmount) * 100;
  const agentPct = (agentRecovered / maxAmount) * 100;

  return (
    <div className="rounded-xl bg-[var(--bg-surface)] shadow-card border border-[var(--border-default)] p-6 overflow-hidden transition-all duration-200 hover:shadow-elevated">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 pb-4 border-b border-[var(--border-default)]">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-[var(--brand-primary)] text-white shadow-sm">
            <Sparkles className="h-4.5 w-4.5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="font-heading text-lg font-semibold text-[var(--text-primary)] tracking-tight">
                Value Impact: With Agent vs. Without Agent
              </h2>
              <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 px-2.5 py-0.5 text-xs font-heading font-semibold text-emerald-700 dark:text-emerald-300">
                <TrendingUp className="h-3 w-3" />
                +{recoveryRate.toFixed(1)}% Lift
              </span>
            </div>
            <p className="text-xs font-body text-[var(--text-secondary)] font-semibold mt-0.5">
              Honest counterfactual comparison against standard zero-touch failure baseline
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 self-start sm:self-auto font-mono text-xs text-[var(--text-primary)] bg-[var(--bg-surface-subtle)] px-3 py-1.5 rounded-md border border-[var(--border-default)] font-semibold">
          <span>Total at Risk:</span>
          <span className="font-bold text-[var(--text-primary)]">
            ₹{atRisk.toLocaleString("en-IN", { maximumFractionDigits: 0 })}
          </span>
        </div>
      </div>

      {/* Comparative Bar Chart */}
      <div className="mt-5 space-y-4">
        {/* Bar 1: Without Agent (Baseline) */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-xs font-body font-semibold">
            <span className="flex items-center gap-1.5 text-[var(--text-secondary)]">
              <XCircle className="h-3.5 w-3.5 opacity-60" />
              <span>Without Agent (Standard Static Dunning)</span>
            </span>
            <span className="font-mono text-[var(--text-muted)] font-bold">
              ₹0 recovered <span className="text-xs font-normal font-sans">(0.0%)</span>
            </span>
          </div>
          <div className="relative h-7 w-full overflow-hidden rounded-md bg-[var(--bg-surface-subtle)] border border-[var(--border-default)] flex items-center">
            <div
              className="h-full bg-[var(--border-default)] transition-all duration-500 ease-out"
              style={{ width: `${Math.max(baselinePct, 0.5)}%` }}
            />
            <span className="absolute left-3 text-xs font-mono font-semibold text-[var(--text-muted)]">
              ₹0
            </span>
          </div>
        </div>

        {/* Bar 2: With Revenue Recovery Agent */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-xs font-body font-semibold">
            <span className="flex items-center gap-1.5 text-[var(--brand-primary)] font-bold">
              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
              <span>With AI Revenue Recovery Agent</span>
            </span>
            <span className="font-mono text-[var(--brand-primary)] font-bold">
              ₹{agentRecovered.toLocaleString("en-IN", { maximumFractionDigits: 0 })} recovered{" "}
              <span className="text-xs font-semibold text-emerald-600 dark:text-emerald-400">({recoveryRate.toFixed(1)}%)</span>
            </span>
          </div>
          <div className="relative h-7 w-full overflow-hidden rounded-md bg-[var(--brand-accent-subtle)] border border-[var(--brand-accent)]/30 flex items-center">
            <div
              className="h-full bg-gradient-to-r from-[var(--brand-primary)] to-[var(--brand-accent)] transition-all duration-700 ease-out"
              style={{ width: `${Math.max(agentPct, 2)}%` }}
            />
            <span className="absolute left-3 text-xs font-mono font-bold text-white drop-shadow-sm">
              ₹{agentRecovered.toLocaleString("en-IN", { maximumFractionDigits: 0 })}
            </span>
          </div>
        </div>
      </div>

      {/* Summary Highlight & Caption */}
      <div className="mt-4 pt-3 border-t border-[var(--border-default)] flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
        <p className="text-xs font-body font-semibold text-[var(--text-primary)] flex items-center gap-1.5">
          <ArrowRight className="h-3.5 w-3.5 text-[var(--brand-primary)] shrink-0" />
          <span>
            <strong className="text-[var(--brand-primary)] font-bold">{recoveryRate.toFixed(1)}%</strong> of at-risk revenue recovered automatically, with zero without intervention.
          </span>
        </p>
        <div className="text-xs font-body text-[var(--text-secondary)] font-semibold self-start sm:self-auto">
          Net Value Added: <strong className="text-emerald-700 dark:text-emerald-400 font-bold">+₹{improvement.toLocaleString("en-IN", { maximumFractionDigits: 0 })}</strong>
        </div>
      </div>
    </div>
  );
}
