"use client";

import React, { useState } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PaymentResult } from "@/lib/api";
import {
  AlertOctagon,
  LifeBuoy,
  StopCircle,
  FileSpreadsheet,
  Coins,
} from "lucide-react";

interface ExceptionsViewProps {
  payments: PaymentResult[];
}

export function ExceptionsView({ payments }: ExceptionsViewProps) {
  const [filterType, setFilterType] = useState<"all" | "escalated" | "stopped">("all");

  const exceptions = payments.filter(
    (p) => p.status === "escalated" || p.status === "stopped"
  );

  const filtered = exceptions.filter((p) => {
    if (filterType === "escalated") return p.status === "escalated";
    if (filterType === "stopped") return p.status === "stopped";
    return true;
  });

  const escalatedCount = exceptions.filter((p) => p.status === "escalated").length;
  const stoppedCount = exceptions.filter((p) => p.status === "stopped").length;
  const totalAmount = exceptions.reduce((acc, p) => acc + (p.amount || 0), 0);

  const exportCSV = () => {
    const headers = "Payment ID,Customer Name,Amount,Category,Status,Stop Reason,Action\n";
    const rows = exceptions
      .map(
        (p) =>
          `"${p.payment_id}","${p.customer_name || ""}","${p.amount}","${p.fail_category || p.fail_reason}","${p.status}","${p.stop_reason || ""}","${p.current_action || ""}"`
      )
      .join("\n");
    const blob = new Blob([headers + rows], { type: "text/csv" });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `exceptions_list_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    document.body.removeChild(a);
  };

  return (
    <div className="space-y-6">
      {/* Overview Callout Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card className="rounded-xl bg-[var(--bg-surface)] shadow-card border border-[var(--border-default)] transition-all duration-200 ease hover:shadow-elevated">
          <CardHeader className="pb-2 p-6">
            <div className="flex items-center justify-between">
              <CardTitle className="font-heading text-xs font-semibold uppercase tracking-wider text-[var(--brand-primary)]">
                Human Escalations
              </CardTitle>
              <div className="rounded-md bg-red-500/10 p-2 text-red-600 dark:text-red-400 border border-red-500/20">
                <LifeBuoy className="h-4 w-4 text-red-600 dark:text-red-400" />
              </div>
            </div>
          </CardHeader>
          <CardContent className="p-6 pt-0">
            <div className="font-heading text-h2 font-semibold text-[var(--text-primary)] tracking-normal">
              {escalatedCount}
            </div>
            <p className="font-body text-xs text-[var(--text-secondary)] mt-1 font-semibold">
              Revoked mandates & high-value &gt;₹5,000 safety caps
            </p>
          </CardContent>
        </Card>

        <Card className="rounded-xl bg-[var(--bg-surface)] shadow-card border border-[var(--border-default)] transition-all duration-200 ease hover:shadow-elevated">
          <CardHeader className="pb-2 p-6">
            <div className="flex items-center justify-between">
              <CardTitle className="font-heading text-xs font-semibold uppercase tracking-wider text-[var(--brand-primary)]">
                Autonomous Stops
              </CardTitle>
              <div className="rounded-md bg-[var(--brand-accent-subtle)] p-2 text-[var(--brand-primary)] border border-[var(--border-default)]">
                <StopCircle className="h-4 w-4 text-[var(--brand-primary)]" />
              </div>
            </div>
          </CardHeader>
          <CardContent className="p-6 pt-0">
            <div className="font-heading text-h2 font-semibold text-[var(--text-primary)] tracking-normal">
              {stoppedCount}
            </div>
            <p className="font-body text-xs text-[var(--text-secondary)] mt-1 font-semibold">
              Bounded safety halts (cost ceiling &gt;30% or max retries &gt;=3)
            </p>
          </CardContent>
        </Card>

        <Card className="rounded-xl bg-[var(--bg-surface)] shadow-card border border-[var(--border-default)] transition-all duration-200 ease hover:shadow-elevated">
          <CardHeader className="pb-2 p-6">
            <div className="flex items-center justify-between">
              <CardTitle className="font-heading text-xs font-semibold uppercase tracking-wider text-[var(--brand-primary)]">
                Exception Volume at Stake
              </CardTitle>
              <div className="rounded-md bg-[var(--brand-accent-subtle)] p-2 text-[var(--brand-accent)] border border-[var(--border-default)]">
                <AlertOctagon className="h-4 w-4 text-[var(--brand-accent)]" />
              </div>
            </div>
          </CardHeader>
          <CardContent className="p-6 pt-0">
            <div className="font-heading text-h2 font-semibold text-[var(--brand-accent)] tracking-normal">
              ₹{totalAmount.toLocaleString("en-IN", { maximumFractionDigits: 0 })}
            </div>
            <p className="font-body text-xs text-[var(--text-secondary)] mt-1 font-semibold">
              Requires manual CSR intervention or customer outreach
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Action Header & Filters */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2">
          <div className="flex items-center rounded-lg bg-[var(--bg-surface)] p-1 border border-[var(--border-default)] shadow-card text-xs">
            <button
              onClick={() => setFilterType("all")}
              className={`rounded-md px-3.5 py-1.5 font-heading text-xs font-semibold tracking-wider transition-all duration-150 ease ${
                filterType === "all"
                  ? "bg-[var(--brand-primary)] text-white shadow-card"
                  : "text-[var(--text-primary)] hover:text-[var(--brand-accent)]"
              }`}
            >
              All Exceptions ({exceptions.length})
            </button>
            <button
              onClick={() => setFilterType("escalated")}
              className={`rounded-md px-3.5 py-1.5 font-heading text-xs font-semibold tracking-wider transition-all duration-150 ease ${
                filterType === "escalated"
                  ? "bg-[var(--brand-primary)] text-white shadow-card"
                  : "text-[var(--text-primary)] hover:text-[var(--brand-accent)]"
              }`}
            >
              Escalated ({escalatedCount})
            </button>
            <button
              onClick={() => setFilterType("stopped")}
              className={`rounded-md px-3.5 py-1.5 font-heading text-xs font-semibold tracking-wider transition-all duration-150 ease ${
                filterType === "stopped"
                  ? "bg-[var(--brand-primary)] text-white shadow-card"
                  : "text-[var(--text-primary)] hover:text-[var(--brand-accent)]"
              }`}
            >
              Stopped ({stoppedCount})
            </button>
          </div>
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={exportCSV}
          className="h-9 gap-2 rounded-md font-body text-xs font-semibold border border-[var(--border-default)] bg-[var(--bg-surface)] hover:border-[var(--brand-accent)] hover:text-[var(--brand-accent)] text-[var(--text-primary)] shadow-card"
        >
          <FileSpreadsheet className="h-4 w-4 text-[var(--brand-primary)]" />
          Export Exception CSV
        </Button>
      </div>

      {/* Exception Table */}
      <div className="rounded-xl bg-[var(--bg-surface)] shadow-card border border-[var(--border-default)] overflow-hidden">
        <Table>
          <TableHeader className="bg-[var(--bg-surface-subtle)]">
            <TableRow className="border-b border-[var(--border-default)]">
              <TableHead className="text-[var(--text-secondary)] font-semibold text-xs">Payment ID</TableHead>
              <TableHead className="text-[var(--text-secondary)] font-semibold text-xs">Customer</TableHead>
              <TableHead className="text-[var(--text-secondary)] font-semibold text-xs">Amount</TableHead>
              <TableHead className="text-[var(--text-secondary)] font-semibold text-xs">Category</TableHead>
              <TableHead className="text-[var(--text-secondary)] font-semibold text-xs">Classification</TableHead>
              <TableHead className="text-[var(--text-secondary)] font-semibold text-xs">Stop / Escalation Reason</TableHead>
              <TableHead className="text-center text-[var(--text-secondary)] font-semibold text-xs">Retries</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="h-28 text-center font-body text-xs text-[var(--text-muted)] font-semibold">
                  No exceptions matching current filter.
                </TableCell>
              </TableRow>
            ) : (
              filtered.map((item) => (
                <TableRow key={item.payment_id} className="transition-colors duration-150 ease hover:bg-[var(--brand-accent-subtle)] border-b border-[var(--border-subtle)]">
                  <TableCell className="font-mono text-xs font-semibold text-[var(--text-primary)]">
                    {item.payment_id}
                  </TableCell>
                  <TableCell className="font-body text-xs font-semibold text-[var(--text-primary)]">
                    {item.customer_name || "Valued Subscriber"}
                  </TableCell>
                  <TableCell className="font-mono text-xs font-semibold text-[var(--text-primary)]">
                    ₹{item.amount.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                  </TableCell>
                  <TableCell>
                    <span className="rounded-md bg-[var(--brand-accent-subtle)] px-2.5 py-1 font-mono text-xs text-[var(--brand-primary)] border border-[var(--border-default)] font-semibold">
                      {item.fail_category || item.fail_reason}
                    </span>
                  </TableCell>
                  <TableCell>
                    {item.status === "escalated" ? (
                      <Badge className="bg-red-500/10 text-red-700 dark:text-red-300 border-red-500/30 rounded-sm font-semibold text-xs gap-1">
                        <LifeBuoy className="h-3 w-3" />
                        Escalated to Human
                      </Badge>
                    ) : item.stop_reason_category === "cost_exceeds_value" || item.stop_reason?.includes("cost_ceiling") ? (
                      <Badge className="bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-500/30 font-semibold rounded-sm text-xs gap-1">
                        <Coins className="h-3 w-3" />
                        Cost-Aware Stop
                      </Badge>
                    ) : (
                      <Badge className="bg-[var(--bg-surface-subtle)] text-[var(--text-secondary)] border-[var(--border-default)] rounded-sm font-semibold text-xs gap-1">
                        <StopCircle className="h-3 w-3" />
                        Halted / Stopped
                      </Badge>
                    )}
                  </TableCell>
                  <TableCell className="max-w-md">
                    <div className="flex items-center gap-1.5">
                      <span className="font-mono text-xs text-[var(--text-primary)] font-semibold">
                        {item.stop_reason || "Autonomous threshold reached"}
                      </span>
                    </div>
                    {(item.stop_reason_category === "cost_exceeds_value" || item.stop_reason?.includes("cost_ceiling")) && (
                      <span className="font-body text-xs text-amber-700 dark:text-amber-300 block mt-0.5 font-semibold">
                        Margin Protection: Further retries halted because estimated cost exceeded 30% of ₹{item.amount.toFixed(0)} invoice.
                      </span>
                    )}
                    {item.fail_explanation && !(item.stop_reason_category === "cost_exceeds_value" || item.stop_reason?.includes("cost_ceiling")) && (
                      <span className="font-body text-xs text-[var(--text-secondary)] block truncate mt-0.5 font-semibold">
                        {item.fail_explanation}
                      </span>
                    )}
                  </TableCell>
                  <TableCell className="text-center font-mono text-xs font-semibold text-[var(--text-primary)]">{item.retry_count}</TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
