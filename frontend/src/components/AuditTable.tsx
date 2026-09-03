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
import { Input } from "@/components/ui/input";
import { PaymentResult, AuditStep, getPaymentAudit } from "@/lib/api";
import {
  ChevronDown,
  ChevronRight,
  Search,
  ShieldCheck,
  Zap,
  ExternalLink,
  CheckCircle2,
  RotateCw,
  LifeBuoy,
  StopCircle,
  Clock,
} from "lucide-react";

interface AuditTableProps {
  batchId: string;
  payments: PaymentResult[];
}

export function AuditTable({ batchId, payments }: AuditTableProps) {
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [loadingAudit, setLoadingAudit] = useState<boolean>(false);
  const [auditDataCache, setAuditDataCache] = useState<Record<string, AuditStep[]>>({});

  // Filter payments
  const filtered = payments.filter((p) => {
    const matchesSearch =
      p.payment_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (p.customer_name && p.customer_name.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (p.fail_reason && p.fail_reason.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (p.fail_category && p.fail_category.toLowerCase().includes(searchTerm.toLowerCase()));

    const matchesStatus = statusFilter === "all" || p.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const toggleExpand = async (paymentId: string) => {
    if (expandedId === paymentId) {
      setExpandedId(null);
      return;
    }

    setExpandedId(paymentId);

    // If audit steps already present on record, cache them
    const record = payments.find((p) => p.payment_id === paymentId);
    if (record?.intervention_history && record.intervention_history.length > 0) {
      setAuditDataCache((prev) => ({
        ...prev,
        [paymentId]: record.intervention_history || [],
      }));
      return;
    }

    // Otherwise fetch from endpoint
    if (!auditDataCache[paymentId] && batchId) {
      setLoadingAudit(true);
      try {
        const data = await getPaymentAudit(batchId, paymentId);
        setAuditDataCache((prev) => ({
          ...prev,
          [paymentId]: data.audit_trail || [],
        }));
      } catch (err) {
        console.error("Failed to load audit trail:", err);
      } finally {
        setLoadingAudit(false);
      }
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "recovered":
        return (
          <Badge className="bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/30 rounded-sm font-semibold gap-1 text-xs">
            <CheckCircle2 className="h-3 w-3 text-emerald-600 dark:text-emerald-400" />
            Recovered
          </Badge>
        );
      case "in_progress":
        return (
          <Badge className="bg-[var(--brand-accent-subtle)] text-[var(--brand-accent)] border-[var(--brand-accent)]/30 rounded-sm font-semibold gap-1 text-xs">
            <RotateCw className="h-3 w-3 text-[var(--brand-accent)] animate-spin" />
            In Progress
          </Badge>
        );
      case "escalated":
        return (
          <Badge className="bg-red-500/10 text-red-700 dark:text-red-300 border-red-500/30 rounded-sm font-semibold gap-1 text-xs">
            <LifeBuoy className="h-3 w-3 text-red-600 dark:text-red-400" />
            Escalated
          </Badge>
        );
      case "stopped":
        return (
          <Badge className="bg-[var(--bg-surface-subtle)] text-[var(--text-secondary)] border-[var(--border-default)] rounded-sm font-semibold gap-1 text-xs">
            <StopCircle className="h-3 w-3 text-[var(--text-muted)]" />
            Stopped
          </Badge>
        );
      case "awaiting_promise":
        return (
          <Badge className="bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-500/30 rounded-sm font-semibold gap-1 text-xs">
            <Clock className="h-3 w-3 text-amber-600 dark:text-amber-400" />
            Promise Logged
          </Badge>
        );
      default:
        return <Badge variant="secondary" className="rounded-sm font-semibold text-xs">Pending</Badge>;
    }
  };

  const getActionBadge = (action?: string) => {
    if (!action) return null;
    switch (action) {
      case "retry_now":
        return <Badge variant="outline" className="border-[var(--brand-primary)]/40 text-[var(--brand-primary)] rounded-sm font-semibold text-xs">Auto Retry Now</Badge>;
      case "retry_later":
        return <Badge variant="outline" className="border-[var(--brand-accent)]/40 text-[var(--brand-accent)] rounded-sm font-semibold text-xs">Schedule Retry (2d)</Badge>;
      case "switch_payment_method":
        return <Badge variant="outline" className="border-[var(--brand-accent)]/40 text-[var(--brand-accent)] rounded-sm font-semibold text-xs">Send Payment Link</Badge>;
      case "escalate_human":
        return <Badge variant="outline" className="border-red-500/40 text-red-700 dark:text-red-300 rounded-sm font-semibold text-xs">Human Escalation</Badge>;
      case "stop_no_action":
        return <Badge variant="outline" className="border-[var(--border-default)] text-[var(--text-muted)] rounded-sm font-semibold text-xs">Stop Recovery</Badge>;
      default:
        return <Badge variant="outline" className="rounded-sm font-semibold text-xs">{action}</Badge>;
    }
  };

  return (
    <div className="space-y-4">
      {/* Controls Bar */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--text-muted)]" />
          <Input
            placeholder="Search payment ID, customer, fail reason..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-9 h-10 font-body text-xs font-semibold rounded-md bg-[var(--bg-surface)] text-[var(--text-primary)] border-[var(--border-default)] focus:border-[var(--brand-accent)]"
          />
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-2 overflow-x-auto pb-1">
          {["all", "in_progress", "recovered", "escalated", "stopped"].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`rounded-md px-3.5 py-1.5 font-heading text-xs font-semibold tracking-wider transition-all duration-150 ease ${
                statusFilter === st
                  ? "bg-[var(--brand-primary)] text-white shadow-card border border-[var(--brand-primary)]"
                  : "bg-[var(--bg-surface)] text-[var(--text-primary)] border border-[var(--border-default)] hover:border-[var(--brand-accent)] hover:text-[var(--brand-accent)]"
              }`}
            >
              {st === "all" ? "All Payments" : st.replace("_", " ").toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {/* Table Card */}
      <div className="rounded-xl bg-[var(--bg-surface)] shadow-card border border-[var(--border-default)] overflow-hidden">
        <Table>
          <TableHeader className="bg-[var(--bg-surface-subtle)]">
            <TableRow className="border-b border-[var(--border-default)]">
              <TableHead className="w-10"></TableHead>
              <TableHead className="text-[var(--text-secondary)] font-semibold text-xs">Payment ID</TableHead>
              <TableHead className="text-[var(--text-secondary)] font-semibold text-xs">Customer</TableHead>
              <TableHead className="text-[var(--text-secondary)] font-semibold text-xs">Amount</TableHead>
              <TableHead className="text-[var(--text-secondary)] font-semibold text-xs">Fail Reason</TableHead>
              <TableHead className="text-[var(--text-secondary)] font-semibold text-xs">Action Selected</TableHead>
              <TableHead className="text-[var(--text-secondary)] font-semibold text-xs">Status</TableHead>
              <TableHead className="text-center text-[var(--text-secondary)] font-semibold text-xs">Retries</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} className="h-32 text-center font-body text-xs text-[var(--text-muted)] font-semibold">
                  No payment records found matching criteria.
                </TableCell>
              </TableRow>
            ) : (
              filtered.map((item) => {
                const isExpanded = expandedId === item.payment_id;
                const steps = auditDataCache[item.payment_id] || item.intervention_history || [];

                return (
                  <React.Fragment key={item.payment_id}>
                    <TableRow
                      onClick={() => toggleExpand(item.payment_id)}
                      className={`cursor-pointer transition-colors duration-150 ease border-b border-[var(--border-subtle)] hover:bg-[var(--brand-accent-subtle)] ${
                        isExpanded ? "bg-[var(--brand-accent-subtle)]" : ""
                      }`}
                    >
                      <TableCell className="p-2 text-center text-[var(--text-muted)]">
                        {isExpanded ? (
                          <ChevronDown className="h-4 w-4 text-[var(--brand-primary)]" />
                        ) : (
                          <ChevronRight className="h-4 w-4" />
                        )}
                      </TableCell>
                      <TableCell className="font-mono text-xs font-semibold text-[var(--text-primary)]">
                        {item.payment_id}
                      </TableCell>
                      <TableCell className="font-body text-xs font-semibold text-[var(--text-primary)]">
                        {item.customer_name || "Unknown Customer"}
                      </TableCell>
                      <TableCell className="font-mono text-xs font-semibold text-[var(--text-primary)]">
                        ₹{item.amount.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                      </TableCell>
                      <TableCell>
                        <span className="rounded-md bg-[var(--brand-accent-subtle)] px-2.5 py-1 font-mono text-xs text-[var(--brand-primary)] border border-[var(--border-default)] font-semibold">
                          {item.fail_category || item.fail_reason}
                        </span>
                      </TableCell>
                      <TableCell>{getActionBadge(item.current_action)}</TableCell>
                      <TableCell>{getStatusBadge(item.status)}</TableCell>
                      <TableCell className="text-center font-mono text-xs font-semibold text-[var(--text-primary)]">{item.retry_count}</TableCell>
                    </TableRow>

                    {/* Summary Explanation subtitle row */}
                    {item.summary_explanation && (
                      <TableRow
                        onClick={() => toggleExpand(item.payment_id)}
                        className={`cursor-pointer border-b border-[var(--border-subtle)] ${isExpanded ? "bg-[var(--brand-accent-subtle)]" : ""}`}
                      >
                        <TableCell />
                        <TableCell colSpan={7} className="py-1.5 pb-2.5">
                          <p className="font-body text-xs text-[var(--text-secondary)] leading-snug font-semibold italic">
                            {item.summary_explanation}
                          </p>
                        </TableCell>
                      </TableRow>
                    )}

                    {/* Expandable Audit Trail Storyline */}
                    {isExpanded && (
                      <TableRow className="bg-[var(--brand-accent-subtle)] border-b border-[var(--border-default)]">
                        <TableCell colSpan={8} className="p-6">
                          <div className="rounded-xl bg-[var(--bg-surface-elevated)] border border-[var(--border-default)] p-6 shadow-elevated space-y-4">
                            {/* Summary explanation heading */}
                            {item.summary_explanation && (
                              <div className="bg-[var(--brand-accent-subtle)] border border-[var(--brand-accent)]/20 rounded-lg px-4 py-3">
                                <p className="font-body text-sm text-[var(--text-primary)] font-bold leading-snug">
                                  {item.summary_explanation}
                                </p>
                              </div>
                            )}
                            <div className="flex flex-wrap items-center justify-between border-b border-[var(--border-default)] pb-4 gap-2">
                              <div>
                                <h4 className="font-heading text-h4 font-semibold text-[var(--text-primary)] flex items-center gap-2">
                                  <ShieldCheck className="h-5 w-5 text-[var(--brand-primary)]" />
                                  Recovery Decision Audit Trail — {item.payment_id}
                                </h4>
                                <p className="font-body text-xs text-[var(--brand-primary)] mt-1 font-semibold">
                                  End-to-end bounded autonomous agent execution transcript & tool response
                                </p>
                              </div>
                              <div className="flex items-center gap-2 font-mono text-xs">
                                {item.stop_reason && (
                                  <span className="rounded-sm bg-[var(--bg-surface-subtle)] px-3 py-1 text-[var(--text-primary)] font-semibold border border-[var(--border-default)]">
                                    Stop Reason: {item.stop_reason}
                                  </span>
                                )}
                              </div>
                            </div>

                            {/* Chronological Narrative Steps */}
                            {loadingAudit && steps.length === 0 ? (
                              <div className="py-6 text-center font-body text-xs text-[var(--text-muted)] animate-pulse font-semibold">
                                Loading full audit trace from backend...
                              </div>
                            ) : steps.length === 0 ? (
                              <div className="py-4 text-center font-body text-xs text-[var(--text-muted)] font-semibold">
                                No audit step transcript recorded for this payment yet.
                              </div>
                            ) : (
                              <div className="relative pl-6 space-y-4 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-[var(--border-default)]">
                                {steps.map((step, idx) => (
                                  <div key={idx} className="relative group">
                                    {/* Step marker dot */}
                                    <div className="absolute -left-6 top-1 h-3 w-3 rounded-full border-2 border-[var(--bg-surface-elevated)] bg-[var(--brand-primary)] ring-2 ring-[var(--brand-accent)]/30" />

                                    <div className="rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] p-4 space-y-2 shadow-card">
                                      <div className="flex items-center justify-between font-mono text-xs">
                                        <span className="font-heading font-semibold text-[var(--brand-primary)] uppercase tracking-wide">
                                          Step {idx + 1}: {step.node.replace("_", " ")}
                                        </span>
                                        {step.timestamp && (
                                          <span className="text-[var(--text-muted)] font-mono font-semibold">
                                            {new Date(step.timestamp).toLocaleTimeString()}
                                          </span>
                                        )}
                                      </div>

                                      <div className="flex items-baseline gap-2">
                                        <span className="font-heading text-xs font-semibold text-[var(--text-secondary)]">Decision:</span>
                                        <span className="font-mono text-xs rounded-sm bg-[var(--bg-surface-subtle)] px-2 py-0.5 text-[var(--text-primary)] border border-[var(--border-default)] font-semibold">
                                          {step.decision}
                                        </span>
                                      </div>

                                      {step.reason && (
                                        <p className="font-body text-xs text-[var(--text-primary)] leading-relaxed font-semibold">
                                          {step.reason}
                                        </p>
                                      )}

                                      {/* Tool Invocation Details */}
                                      {step.tool_called && (
                                        <div className="mt-2 rounded-md bg-[var(--brand-accent-subtle)] border border-[var(--brand-accent)]/20 p-3 space-y-1 font-mono text-xs">
                                          <div className="flex items-center justify-between text-[var(--text-primary)]">
                                            <span className="flex items-center gap-1.5 font-heading font-semibold text-[var(--brand-primary)]">
                                              <Zap className="h-3.5 w-3.5" />
                                              Tool Invoked: {step.tool_called}
                                            </span>
                                            {step.tool_result?.short_url && (
                                              <a
                                                href={step.tool_result.short_url}
                                                target="_blank"
                                                rel="noreferrer"
                                                className="flex items-center gap-1 text-[var(--brand-primary)] hover:underline font-body font-semibold"
                                              >
                                                Open Payment Link <ExternalLink className="h-3 w-3" />
                                              </a>
                                            )}
                                          </div>

                                          {step.tool_result && (
                                            <pre className="mt-2 max-h-40 overflow-auto rounded-sm bg-[var(--bg-surface)] p-3 text-xs text-[var(--text-primary)] border border-[var(--border-default)] leading-tight font-mono font-semibold">
                                              {JSON.stringify(step.tool_result, null, 2)}
                                            </pre>
                                          )}
                                        </div>
                                      )}
                                    </div>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    )}
                  </React.Fragment>
                );
              })
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
