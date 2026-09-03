"use client";

import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { BatchMetricsResponse, BatchStatusResponse } from "@/lib/api";
import { ShieldAlert, IndianRupee, TrendingUp, RefreshCw, Coins } from "lucide-react";

interface MetricsCardsProps {
  metrics: BatchMetricsResponse | null;
  status: BatchStatusResponse | null;
  loading?: boolean;
}

export function MetricsCards({ metrics, status, loading }: MetricsCardsProps) {
  const atRisk = metrics?.total_amount_at_risk ?? 0;
  const recovered = metrics?.total_recovered ?? 0;
  const rate = metrics?.recovery_rate_pct ?? 0;
  const avgRetries = metrics?.avg_retries_to_recovery ?? 0;
  const escalationRate = (metrics?.escalation_rate ?? 0) * 100;
  const inProgressCount = status?.counts_by_status.in_progress ?? 0;
  const costAwareStops = metrics?.cost_aware_stops ?? 0;
  const estimatedSavings = metrics?.estimated_savings ?? 0;

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
      {/* 1. Total Amount at Risk */}
      <Card className="rounded-xl bg-[var(--bg-surface)] shadow-card border border-[var(--border-default)] transition-all duration-200 ease hover:shadow-elevated">
        <CardHeader className="flex flex-row items-center justify-between pb-2 p-5">
          <CardTitle className="font-heading text-xs font-semibold uppercase tracking-wider text-[var(--brand-primary)]">
            Revenue at Risk
          </CardTitle>
          <div className="rounded-md bg-[var(--brand-accent-subtle)] p-2 text-[var(--brand-primary)] border border-[var(--border-default)]">
            <ShieldAlert className="h-4 w-4 text-[var(--brand-primary)]" />
          </div>
        </CardHeader>
        <CardContent className="p-5 pt-0">
          <div className="font-heading text-h2 font-semibold text-[var(--text-primary)] tracking-normal">
            ₹{atRisk.toLocaleString("en-IN", { maximumFractionDigits: 0 })}
          </div>
          <p className="mt-2 font-body text-xs font-semibold text-[var(--text-secondary)]">
            Across {metrics?.total_payments || status?.total_count || 0} failed mandates
          </p>
        </CardContent>
      </Card>

      {/* 2. Total Recovered */}
      <Card className="rounded-xl bg-[var(--bg-surface)] shadow-card border border-[var(--border-default)] transition-all duration-200 ease hover:shadow-elevated">
        <CardHeader className="flex flex-row items-center justify-between pb-2 p-5">
          <CardTitle className="font-heading text-xs font-semibold uppercase tracking-wider text-[var(--brand-primary)]">
            Revenue Recovered
          </CardTitle>
          <div className="rounded-md bg-[var(--brand-accent-subtle)] p-2 text-[var(--brand-primary)] border border-[var(--border-default)]">
            <IndianRupee className="h-4 w-4 text-[var(--brand-primary)]" />
          </div>
        </CardHeader>
        <CardContent className="p-5 pt-0">
          <div className="font-heading text-h2 font-semibold text-[var(--brand-primary)] tracking-normal">
            ₹{recovered.toLocaleString("en-IN", { maximumFractionDigits: 0 })}
          </div>
          <p className="mt-2 font-body text-xs font-semibold text-[var(--text-secondary)]">
            {status?.counts_by_status.recovered || 0} auto-captured recoveries
          </p>
        </CardContent>
      </Card>

      {/* 3. Recovery Rate % */}
      <Card className="rounded-xl bg-[var(--bg-surface)] shadow-card border border-[var(--border-default)] transition-all duration-200 ease hover:shadow-elevated">
        <CardHeader className="flex flex-row items-center justify-between pb-2 p-5">
          <CardTitle className="font-heading text-xs font-semibold uppercase tracking-wider text-[var(--brand-primary)]">
            Recovery Rate
          </CardTitle>
          <div className="rounded-md bg-[var(--brand-accent-subtle)] p-2 text-[var(--brand-accent)] border border-[var(--border-default)]">
            <TrendingUp className="h-4 w-4 text-[var(--brand-accent)]" />
          </div>
        </CardHeader>
        <CardContent className="p-5 pt-0">
          <div className="font-heading text-h2 font-semibold text-[var(--brand-accent)] tracking-normal">
            {rate.toFixed(1)}%
          </div>
          <div className="mt-2 flex items-center gap-2 font-body text-xs font-semibold text-[var(--text-secondary)]">
            <span className="inline-block h-2 w-2 rounded-full bg-[var(--brand-accent)] animate-pulse" />
            <span>{inProgressCount} in retry/link workflow</span>
          </div>
        </CardContent>
      </Card>

      {/* 4. Cost-Aware Savings (KEY INNOVATION STAT CARD) */}
      <Card className="rounded-xl bg-[var(--bg-surface)] shadow-card border border-amber-500/30 transition-all duration-200 ease hover:shadow-elevated bg-gradient-to-br from-[var(--bg-surface)] to-amber-500/5">
        <CardHeader className="flex flex-row items-center justify-between pb-2 p-5">
          <CardTitle className="font-heading text-xs font-semibold uppercase tracking-wider text-amber-700 dark:text-amber-400">
            Cost-Aware Savings
          </CardTitle>
          <div className="rounded-md bg-amber-500/10 p-2 text-amber-600 dark:text-amber-400 border border-amber-500/20">
            <Coins className="h-4 w-4 text-amber-600 dark:text-amber-400" />
          </div>
        </CardHeader>
        <CardContent className="p-5 pt-0">
          <div className="font-heading text-h2 font-semibold text-amber-700 dark:text-amber-400 tracking-normal">
            ₹{estimatedSavings.toLocaleString("en-IN", { maximumFractionDigits: 0 })}
          </div>
          <p className="mt-2 font-body text-xs font-semibold text-[var(--text-primary)] leading-snug">
            <strong>{costAwareStops}</strong> payments stopped early when retry cost exceeded recovery value
          </p>
          <p className="mt-1 text-xs text-[var(--text-muted)] font-normal font-sans italic">
            Autonomous stop rule halts retries when cost exceeds 30% invoice ceiling
          </p>
        </CardContent>
      </Card>

      {/* 5. Avg Retries & Escalation Rate */}
      <Card className="rounded-xl bg-[var(--bg-surface)] shadow-card border border-[var(--border-default)] transition-all duration-200 ease hover:shadow-elevated">
        <CardHeader className="flex flex-row items-center justify-between pb-2 p-5">
          <CardTitle className="font-heading text-xs font-semibold uppercase tracking-wider text-[var(--brand-primary)]">
            Avg Retries & Escalations
          </CardTitle>
          <div className="rounded-md bg-[var(--brand-accent-subtle)] p-2 text-[var(--brand-primary)] border border-[var(--border-default)]">
            <RefreshCw className="h-4 w-4 text-[var(--brand-primary)]" />
          </div>
        </CardHeader>
        <CardContent className="p-5 pt-0">
          <div className="flex items-baseline gap-2">
            <div className="font-heading text-h2 font-semibold text-[var(--text-primary)] tracking-normal">
              {avgRetries.toFixed(1)}
            </div>
            <span className="font-body text-xs font-semibold text-[var(--text-secondary)]">retries / item</span>
          </div>
          <p className="mt-2 font-body text-xs font-semibold text-[var(--text-secondary)]">
            {escalationRate.toFixed(1)}% escalated to human review
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
