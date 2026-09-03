"use client";

import React from "react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
  CartesianGrid,
} from "recharts";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { BatchStatusResponse, BatchMetricsResponse } from "@/lib/api";
import { useTheme } from "./ThemeProvider";

interface FunnelChartProps {
  status: BatchStatusResponse | null;
  metrics: BatchMetricsResponse | null;
}

export function FunnelChart({ status, metrics }: FunnelChartProps) {
  const { theme } = useTheme();
  const isDark = theme === "dark";

  const counts = status?.counts_by_status || {
    pending: 0,
    in_progress: 0,
    recovered: 0,
    escalated: 0,
    stopped: 0,
  };

  const total = status?.total_count || 0;

  // Funnel / Pipeline stages with theme-aware colors
  const funnelData = [
    {
      stage: "1. Total Failed",
      count: total,
      pct: 100,
      fill: isDark ? "rgba(255, 255, 255, 0.35)" : "rgba(0, 0, 0, 0.45)",
      description: "Initial failed payment inputs",
    },
    {
      stage: "2. In Progress",
      count: counts.in_progress,
      pct: total > 0 ? Math.round((counts.in_progress / total) * 100) : 0,
      fill: isDark ? "#6f9bff" : "#305eff",
      description: "Payment links active & scheduled retries",
    },
    {
      stage: "3. Recovered",
      count: counts.recovered,
      pct: total > 0 ? Math.round((counts.recovered / total) * 100) : 0,
      fill: isDark ? "#34d399" : "#0000c4",
      description: "Automated instant captured recoveries",
    },
    {
      stage: "4. Escalated",
      count: counts.escalated,
      pct: total > 0 ? Math.round((counts.escalated / total) * 100) : 0,
      fill: isDark ? "#f87171" : "rgba(0, 0, 196, 0.65)",
      description: "Compliance & high-value escalations",
    },
    {
      stage: "5. Stopped",
      count: counts.stopped,
      pct: total > 0 ? Math.round((counts.stopped / total) * 100) : 0,
      fill: isDark ? "rgba(203, 213, 225, 0.55)" : "rgba(0, 0, 0, 0.75)",
      description: "Cost safeguard & retry ceiling halts",
    },
  ];

  // Category breakdown chart data
  const categoryData = Object.entries(metrics?.breakdown_by_fail_category || {}).map(
    ([key, val]) => ({
      name: key.replace("_", " "),
      total: val.total_count,
      recovered: val.recovered_count,
      in_progress: val.in_progress_count,
      escalated: val.escalated_count,
      stopped: val.stopped_count,
      amount: val.total_amount,
    })
  );

  const gridStroke = isDark ? "rgba(255, 255, 255, 0.08)" : "rgba(0, 0, 0, 0.06)";
  const tickFill = isDark ? "#f4f4f8" : "#0b0f19";

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
      {/* Funnel Pipeline Chart */}
      <Card className="rounded-xl bg-[var(--bg-surface)] shadow-card border border-[var(--border-default)] lg:col-span-7">
        <CardHeader className="pb-2 p-6">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="font-heading text-h4 font-semibold text-[var(--text-primary)]">
                Recovery Pipeline Funnel
              </CardTitle>
              <CardDescription className="font-body text-xs font-semibold text-[var(--text-secondary)] mt-1">
                Conversion from initial failed payment detection to resolution state
              </CardDescription>
            </div>
            <span className="rounded-sm bg-[var(--brand-accent-subtle)] px-3 py-1 font-mono text-xs font-semibold text-[var(--brand-primary)] border border-[var(--border-default)]">
              {status?.processed_count || 0} / {total} Processed
            </span>
          </div>
        </CardHeader>
        <CardContent className="p-6 pt-0">
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={funnelData}
                layout="vertical"
                margin={{ top: 8, right: 24, left: 32, bottom: 8 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 12, fill: tickFill, fontWeight: 600 }} />
                <YAxis
                  dataKey="stage"
                  type="category"
                  tick={{ fontSize: 13, fill: tickFill, fontFamily: "Inter", fontWeight: 600 }}
                  width={115}
                />
                <Tooltip
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      const data = payload[0].payload;
                      return (
                        <div className="rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface-elevated)] p-3 shadow-elevated text-xs font-body text-[var(--text-primary)]">
                          <p className="font-heading font-semibold text-[var(--text-primary)]">{data.stage}</p>
                          <p className="text-[var(--text-secondary)] mt-0.5 font-semibold text-xs">{data.description}</p>
                          <div className="mt-2 flex items-center justify-between gap-4 font-mono font-semibold text-[var(--brand-primary)]">
                            <span>Count: {data.count}</span>
                            <span>{data.pct}% of batch</span>
                          </div>
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                  {funnelData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      {/* Category Breakdown Chart */}
      <Card className="rounded-xl bg-[var(--bg-surface)] shadow-card border border-[var(--border-default)] lg:col-span-5">
        <CardHeader className="pb-2 p-6">
          <CardTitle className="font-heading text-h4 font-semibold text-[var(--text-primary)]">
            Fail Cause Breakdown
          </CardTitle>
          <CardDescription className="font-body text-xs font-semibold text-[var(--text-secondary)] mt-1">
            Payment count and resolution volume by diagnosed root cause
          </CardDescription>
        </CardHeader>
        <CardContent className="p-6 pt-0">
          <div className="h-64 w-full">
            {categoryData.length === 0 ? (
              <div className="flex h-full items-center justify-center font-body text-xs text-[var(--text-muted)] font-semibold">
                Run a batch to view category distribution
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={categoryData}
                  margin={{ top: 8, right: 8, left: -24, bottom: 24 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} />
                  <XAxis
                    dataKey="name"
                    tick={{ fontSize: 12, fill: tickFill, fontWeight: 600 }}
                    angle={-20}
                    textAnchor="end"
                    interval={0}
                  />
                  <YAxis tick={{ fontSize: 12, fill: tickFill, fontWeight: 600 }} />
                  <Tooltip
                    content={({ active, payload }) => {
                      if (active && payload && payload.length) {
                        const d = payload[0].payload;
                        return (
                          <div className="rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface-elevated)] p-3 shadow-elevated text-xs font-body text-[var(--text-primary)]">
                            <p className="font-heading font-semibold text-[var(--text-primary)] capitalize">{d.name}</p>
                            <p className="text-[var(--text-secondary)] mt-0.5 text-xs font-semibold">
                              Total Volume: ₹{d.amount.toLocaleString()}
                            </p>
                            <div className="mt-2 space-y-1 font-mono text-xs font-semibold">
                              <p className="text-emerald-600 dark:text-emerald-400">Recovered: {d.recovered}</p>
                              <p className="text-[var(--brand-accent)]">In Progress: {d.in_progress}</p>
                              <p className="text-red-600 dark:text-red-400">Escalated: {d.escalated}</p>
                              <p className="text-[var(--text-muted)]">Stopped: {d.stopped}</p>
                            </div>
                          </div>
                        );
                      }
                      return null;
                    }}
                  />
                  <Bar dataKey="recovered" stackId="a" fill={isDark ? "#34d399" : "#0000c4"} name="Recovered" />
                  <Bar dataKey="in_progress" stackId="a" fill={isDark ? "#6f9bff" : "#305eff"} name="In Progress" />
                  <Bar dataKey="escalated" stackId="a" fill={isDark ? "#f87171" : "rgba(0, 0, 196, 0.6)"} name="Escalated" />
                  <Bar dataKey="stopped" stackId="a" fill={isDark ? "rgba(203, 213, 225, 0.45)" : "rgba(0, 0, 0, 0.65)"} name="Stopped" />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
