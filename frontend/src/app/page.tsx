"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  runBatch,
  getBatchStatus,
  getBatchResults,
  getBatchMetrics,
  resetDemo,
  exportBatchSummary,
  getPendingApprovals,
  getPromiseTracker,
  BatchStatusResponse,
  BatchMetricsResponse,
  PaymentResult,
  PendingApprovalItem,
  PromiseTrackerItem,
} from "@/lib/api";
import { MetricsCards } from "@/components/MetricsCards";
import { FunnelChart } from "@/components/FunnelChart";
import { AuditTable } from "@/components/AuditTable";
import { ExceptionsView } from "@/components/ExceptionsView";
import { ResilienceTestCard } from "@/components/ResilienceTestCard";
import { PendingApprovalsCard } from "@/components/PendingApprovalsCard";
import { PromiseTrackerCard } from "@/components/PromiseTrackerCard";
import { ValueComparisonCard } from "@/components/ValueComparisonCard";
import { ThemeToggle } from "@/components/ThemeToggle";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  Play,
  RotateCw,
  RotateCcw,
  ShieldAlert,
  Sparkles,
  FileJson,
  FileSpreadsheet,
  CheckCircle2,
  LayoutDashboard,
  UserCheck,
  CalendarClock,
  TrendingUp,
  PieChart,
  Table as TableIcon,
  Menu,
  X,
  Activity
} from "lucide-react";

export default function DashboardPage() {
  const [batchId, setBatchId] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [isResetting, setIsResetting] = useState<boolean>(false);
  const [statusData, setStatusData] = useState<BatchStatusResponse | null>(null);
  const [metricsData, setMetricsData] = useState<BatchMetricsResponse | null>(null);
  const [payments, setPayments] = useState<PaymentResult[]>([]);
  const [pendingApprovals, setPendingApprovals] = useState<PendingApprovalItem[]>([]);
  const [promisePayments, setPromisePayments] = useState<PromiseTrackerItem[]>([]);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successBanner, setSuccessBanner] = useState<string | null>(null);

  const [activeTab, setActiveTab] = useState<string>("overview");
  const [isSidebarOpen, setIsSidebarOpen] = useState<boolean>(false);

  const pollingRef = useRef<NodeJS.Timeout | null>(null);

  // Trigger batch run
  const handleRunBatch = async (mode: "all pending" | string[] = "all pending") => {
    setIsRunning(true);
    setErrorMsg(null);
    setSuccessBanner(null);
    try {
      const resp = await runBatch(mode);
      setBatchId(resp.batch_id);
      const initStatus = await getBatchStatus(resp.batch_id);
      setStatusData(initStatus);
    } catch (err: any) {
      console.error("Failed to trigger batch:", err);
      setErrorMsg(err.message || "Failed to trigger batch processing. Ensure backend is running.");
      setIsRunning(false);
    }
  };

  // Reset demo dataset
  const handleResetDemo = async () => {
    setIsResetting(true);
    setErrorMsg(null);
    setSuccessBanner(null);
    try {
      await resetDemo();
      setBatchId(null);
      setStatusData(null);
      setMetricsData(null);
      setPayments([]);
      setPendingApprovals([]);
      setPromisePayments([]);
      setIsRunning(false);
      setActiveTab("overview");
      setSuccessBanner("Demo reset successfully! 75 fresh failed payments generated.");
      setTimeout(() => setSuccessBanner(null), 5000);
    } catch (err: any) {
      console.error("Failed to reset demo dataset:", err);
      setErrorMsg(err.message || "Failed to reset demo dataset. Ensure backend is running.");
    } finally {
      setIsResetting(false);
    }
  };

  // Human decision completion callback
  const handleApprovalDecisionComplete = async (paymentId: string, decision: "approve" | "reject") => {
    setPendingApprovals((prev) => prev.filter((p) => p.payment_id !== paymentId));
    if (batchId) {
      try {
        const [st, mt, res, apprv, promises] = await Promise.all([
          getBatchStatus(batchId),
          getBatchMetrics(batchId),
          getBatchResults(batchId),
          getPendingApprovals(batchId).catch(() => ({ pending_approvals: [] })),
          getPromiseTracker(batchId).catch(() => ({ promise_payments: [] })),
        ]);
        setStatusData(st);
        setMetricsData(mt);
        setPayments(res.results || []);
        setPendingApprovals(apprv.pending_approvals || []);
        setPromisePayments(promises.promise_payments || []);
      } catch (err) {
        console.error("Error refreshing after decision:", err);
      }
    }
  };

  // Export handlers
  const handleExportCSV = () => {
    if (!payments || payments.length === 0) return;
    const headers = [
      "payment_id",
      "customer_name",
      "amount",
      "status",
      "fail_category",
      "current_action",
      "recovered_amount",
      "retry_count"
    ];
    const rows = payments.map(p => [
      p.payment_id,
      p.customer_name || "",
      p.amount,
      p.status,
      p.fail_category || "",
      p.current_action || "",
      p.recovered_amount || 0,
      p.retry_count || 0
    ].join(","));
    const csvContent = [headers.join(","), ...rows].join("\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", `revenue_recovery_${batchId || "summary"}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleExportJSON = () => {
    if (!payments || payments.length === 0) return;
    const jsonContent = JSON.stringify(
      {
        batch_id: batchId,
        exported_at: new Date().toISOString(),
        total_payments: payments.length,
        status: statusData,
        metrics: metricsData,
        results: payments,
      },
      null,
      2
    );
    const blob = new Blob([jsonContent], { type: "application/json;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", `revenue_recovery_${batchId || "summary"}.json`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Polling logic when batch is active
  useEffect(() => {
    if (!batchId) return;

    const poll = async () => {
      try {
        const [st, mt, res, apprv, promises] = await Promise.all([
          getBatchStatus(batchId),
          getBatchMetrics(batchId),
          getBatchResults(batchId),
          getPendingApprovals(batchId).catch(() => ({ pending_approvals: [] })),
          getPromiseTracker(batchId).catch(() => ({ promise_payments: [] })),
        ]);

        setStatusData(st);
        setMetricsData(mt);
        setPayments(res.results || []);
        setPendingApprovals(apprv.pending_approvals || []);
        setPromisePayments(promises.promise_payments || []);

        if (st.status === "completed" || st.status === "failed") {
          setIsRunning(false);
          if (pollingRef.current) {
            clearInterval(pollingRef.current);
            pollingRef.current = null;
          }
        }
      } catch (err: any) {
        console.error("Polling error:", err);
      }
    };

    poll();
    pollingRef.current = setInterval(poll, 2000);

    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
      }
    };
  }, [batchId]);

  const navItems = [
    { id: "overview", label: "Overview", icon: LayoutDashboard },
    { id: "resilience", label: "Resilience & Fault-Tolerance Test", icon: ShieldAlert },
    { id: "approvals", label: "Pending High-Value Approvals", icon: UserCheck, count: pendingApprovals.length },
    { id: "promises", label: "Promise-to-Pay Tracker", icon: CalendarClock },
    { id: "impact", label: "Value Impact: With vs. Without Agent", icon: TrendingUp },
    { id: "analysis", label: "Analysis", icon: PieChart },
    { id: "payments", label: "Payments", icon: TableIcon },
  ];

  return (
    <div className="flex flex-col h-screen bg-[var(--bg-page)] text-[var(--text-primary)] font-body transition-colors duration-200 overflow-hidden">
      {/* Header Bar */}
      <header className="shrink-0 z-40 border-b border-[var(--border-default)] bg-[var(--bg-surface)]/95 backdrop-blur-md transition-colors duration-200">
        <div className="mx-auto flex w-full items-center justify-between px-4 sm:px-6 py-4">
          <div className="flex items-center gap-4 sm:gap-5">
            <button 
              onClick={() => setIsSidebarOpen(!isSidebarOpen)}
              className="md:hidden p-2 -ml-2 text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-surface-subtle)] rounded-md"
            >
              <Menu className="h-5 w-5" />
            </button>
            <div className="flex shrink-0 items-center justify-center">
              <img 
                src="https://upload.wikimedia.org/wikipedia/commons/8/89/Razorpay_logo.svg" 
                alt="Razorpay" 
                className="h-7 w-auto drop-shadow-sm dark:brightness-200 dark:contrast-100" 
              />
            </div>
            
            {/* Sleek Vertical Divider */}
            <div className="hidden sm:block h-5 w-px bg-[var(--border-default)]"></div>
            
            <div className="flex items-center gap-3">
              <h1 className="font-heading text-lg font-semibold tracking-tight text-[var(--text-primary)] hidden sm:block">
                Revenue Recovery
              </h1>
              <Badge variant="secondary" className="hidden md:inline-flex rounded bg-[var(--brand-accent-subtle)] text-[var(--brand-primary)] border-none font-mono text-xs font-bold uppercase tracking-wider px-2.5 py-0.5">
                AI Agent
              </Badge>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Theme Toggle (Sun/Moon) */}
            <ThemeToggle />

            {/* Reset Demo Button */}
            <Button
              variant="secondary"
              size="sm"
              onClick={handleResetDemo}
              disabled={isResetting || isRunning}
              className="hidden sm:flex h-10 shrink-0 whitespace-nowrap rounded-md border border-[var(--border-default)] bg-[var(--bg-surface)] hover:border-[var(--brand-accent)] hover:text-[var(--brand-accent)] text-[var(--text-primary)] font-body text-sm font-semibold px-4 shadow-card"
            >
              <RotateCcw className={`mr-1.5 h-4 w-4 ${isResetting ? "animate-spin" : ""}`} />
              Reset Demo
            </Button>
            <Button
              variant="secondary"
              size="icon"
              onClick={handleResetDemo}
              disabled={isResetting || isRunning}
              className="sm:hidden h-10 w-10 shrink-0 rounded-md border border-[var(--border-default)] bg-[var(--bg-surface)] hover:border-[var(--brand-accent)] hover:text-[var(--brand-accent)] text-[var(--text-primary)] shadow-card"
            >
              <RotateCcw className={`h-4 w-4 ${isResetting ? "animate-spin" : ""}`} />
            </Button>

            {/* Run Batch Trigger Button */}
            <Button
              onClick={() => handleRunBatch("all pending")}
              disabled={isRunning}
              className="h-10 shrink-0 whitespace-nowrap rounded-lg bg-[var(--brand-primary)] hover:bg-[var(--brand-accent)] text-white font-heading font-semibold text-sm shadow-card px-3 sm:px-5 gap-2"
            >
              {isRunning ? (
                <>
                  <RotateCw className="h-4 w-4 animate-spin text-white shrink-0" />
                  <span className="hidden sm:inline">Processing Batch...</span>
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 fill-white text-white shrink-0" />
                  <span className="hidden sm:inline">Run Batch (75 Records)</span>
                  <span className="sm:hidden">Run</span>
                </>
              )}
            </Button>
          </div>
        </div>

        {/* Live Progress Bar on top edge when running */}
        {isRunning && statusData && (
          <div className="w-full bg-[var(--bg-surface-subtle)]">
            <Progress value={statusData.progress_pct} className="h-1.5 rounded-none bg-[var(--bg-surface-subtle)]" />
          </div>
        )}
      </header>

      {/* Main Dashboard Container */}
      <div className="flex flex-1 overflow-hidden relative">
        {/* Mobile Overlay */}
        {isSidebarOpen && (
          <div 
            className="fixed inset-0 bg-black/50 z-20 md:hidden"
            onClick={() => setIsSidebarOpen(false)}
          />
        )}

        {/* Sidebar Desktop & Mobile */}
        <aside className={`
          absolute z-30 md:relative flex flex-col w-64 h-full border-r border-[var(--border-default)] bg-[var(--bg-surface)] transition-transform duration-300 ease-in-out
          ${isSidebarOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"}
        `}>
          <div className="flex items-center justify-between p-4 md:hidden border-b border-[var(--border-default)]">
            <span className="font-heading font-semibold text-[var(--text-primary)]">Menu</span>
            <button onClick={() => setIsSidebarOpen(false)} className="p-1 text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-surface-subtle)] rounded-md">
              <X className="h-5 w-5" />
            </button>
          </div>
          
          <nav className="flex-1 overflow-y-auto p-4 space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => { setActiveTab(item.id); setIsSidebarOpen(false); }}
                  className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg font-heading text-sm font-semibold transition-colors duration-150 ease ${
                    isActive 
                      ? "bg-[var(--brand-accent-subtle)] text-[var(--brand-primary)]" 
                      : "text-[var(--text-secondary)] hover:bg-[var(--bg-surface-subtle)] hover:text-[var(--text-primary)]"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <Icon className="h-4 w-4 shrink-0" />
                    <span className="text-left">{item.label}</span>
                  </div>
                  {item.count !== undefined && item.count > 0 && (
                    <Badge className="rounded-full px-2 py-0.5 bg-amber-500/10 text-amber-600 dark:text-amber-400 border-none ml-2 text-[10px] shadow-none">
                      {item.count}
                    </Badge>
                  )}
                </button>
              );
            })}
          </nav>
        </aside>

        {/* Content Area */}
        <main className="flex-1 overflow-y-auto p-4 sm:p-6 bg-[var(--bg-page)] relative w-full">
          <div className="max-w-5xl mx-auto space-y-6 pb-12">
            {/* Success Banner */}
            {successBanner && (
              <div className="flex items-center gap-3 rounded-md border border-emerald-500/30 bg-emerald-500/10 p-4 text-xs font-body text-emerald-700 dark:text-emerald-300 animate-in fade-in duration-200">
                <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
                <p className="font-semibold">{successBanner}</p>
              </div>
            )}

            {/* Error Notification Alert */}
            {errorMsg && (
              <div className="flex items-center gap-3 rounded-md border border-red-500/30 bg-red-500/10 p-4 text-xs font-body text-red-700 dark:text-red-300">
                <ShieldAlert className="h-4 w-4 text-red-600 dark:text-red-400 shrink-0" />
                <p className="font-semibold">{errorMsg}</p>
              </div>
            )}

            {/* Conditional Rendering based on activeTab */}
            {activeTab === "overview" && (
              <div className="space-y-6">
                {!batchId && (
                  <div className="rounded-xl bg-[var(--bg-surface)] shadow-card border border-[var(--border-default)] p-12 text-center animate-in fade-in duration-300">
                    <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-lg bg-[var(--brand-accent-subtle)] text-[var(--brand-primary)] border border-[var(--border-default)]">
                      <Sparkles className="h-7 w-7 text-[var(--brand-primary)]" />
                    </div>
                    <h2 className="mt-4 font-heading text-display font-normal text-[var(--text-primary)]">
                      Ready to Recover Failed Subscription Revenue
                    </h2>
                    <p className="mx-auto mt-2 max-w-lg font-body text-body text-[var(--text-secondary)] leading-relaxed font-bold">
                      Launch the autonomous recovery agent to diagnose root causes (insufficient funds, expired cards, bank declines, revoked mandates) and execute bounded Razorpay interventions.
                    </p>
                    <div className="mt-6 flex flex-wrap items-center justify-center gap-4">
                      <Button
                        onClick={() => handleRunBatch("all pending")}
                        className="h-11 shrink-0 whitespace-nowrap rounded-lg bg-[var(--brand-primary)] hover:bg-[var(--brand-accent)] text-white font-heading font-semibold text-base px-6 gap-2 shadow-card"
                      >
                        <Play className="h-4 w-4 fill-white text-white shrink-0" />
                        Run Full Synthetic Batch (75 Failed Payments)
                      </Button>
                    </div>
                  </div>
                )}
                {batchId && (
                  <div className="space-y-6 animate-in fade-in duration-300">
                    <MetricsCards metrics={metricsData} status={statusData} loading={isRunning} />
                    <FunnelChart status={statusData} metrics={metricsData} />
                  </div>
                )}
              </div>
            )}

            {activeTab === "resilience" && (
              <div className="animate-in fade-in duration-300">
                <ResilienceTestCard />
              </div>
            )}

            {activeTab === "approvals" && batchId && (
              <div className="animate-in fade-in duration-300">
                <PendingApprovalsCard
                  batchId={batchId}
                  items={pendingApprovals}
                  onDecisionComplete={handleApprovalDecisionComplete}
                />
              </div>
            )}
            
            {activeTab === "approvals" && !batchId && (
              <div className="text-center p-12 text-[var(--text-secondary)] font-body text-sm font-semibold border border-dashed border-[var(--border-default)] rounded-xl animate-in fade-in duration-300">
                Run a batch to see pending high-value approvals.
              </div>
            )}

            {activeTab === "promises" && batchId && (
              <div className="animate-in fade-in duration-300">
                <PromiseTrackerCard
                  batchId={batchId}
                  items={promisePayments}
                  onFastForwardComplete={async () => {
                    try {
                      const [st, mt, res, apprv, promises] = await Promise.all([
                        getBatchStatus(batchId),
                        getBatchMetrics(batchId),
                        getBatchResults(batchId),
                        getPendingApprovals(batchId).catch(() => ({ pending_approvals: [] })),
                        getPromiseTracker(batchId).catch(() => ({ promise_payments: [] })),
                      ]);
                      setStatusData(st);
                      setMetricsData(mt);
                      setPayments(res.results || []);
                      setPendingApprovals(apprv.pending_approvals || []);
                      setPromisePayments(promises.promise_payments || []);
                    } catch (err) {
                      console.error("Error refreshing after fast-forward:", err);
                    }
                  }}
                />
              </div>
            )}
            
            {activeTab === "promises" && !batchId && (
              <div className="text-center p-12 text-[var(--text-secondary)] font-body text-sm font-semibold border border-dashed border-[var(--border-default)] rounded-xl animate-in fade-in duration-300">
                Run a batch to see the promise-to-pay tracker.
              </div>
            )}

            {activeTab === "impact" && batchId && (
              <div className="animate-in fade-in duration-300">
                <ValueComparisonCard metrics={metricsData} loading={isRunning} />
              </div>
            )}
            
            {activeTab === "impact" && !batchId && (
              <div className="text-center p-12 text-[var(--text-secondary)] font-body text-sm font-semibold border border-dashed border-[var(--border-default)] rounded-xl animate-in fade-in duration-300">
                Run a batch to see the value impact comparison.
              </div>
            )}

            {activeTab === "analysis" && batchId && (
              <div className="animate-in fade-in duration-300">
                <ExceptionsView payments={payments} />
              </div>
            )}
            
            {activeTab === "analysis" && !batchId && (
              <div className="text-center p-12 text-[var(--text-secondary)] font-body text-sm font-semibold border border-dashed border-[var(--border-default)] rounded-xl animate-in fade-in duration-300">
                Run a batch to see the analysis and exception breakdown.
              </div>
            )}

            {activeTab === "payments" && batchId && (
              <div className="space-y-4 animate-in fade-in duration-300">
                <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-[var(--border-default)] pb-4">
                  <h2 className="font-heading text-lg font-semibold text-[var(--text-primary)] flex items-center gap-2">
                    <Activity className="h-5 w-5 text-[var(--brand-primary)]" />
                    All Payments Audit Trail
                  </h2>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-xs text-[var(--text-primary)] bg-[var(--bg-surface)] px-3 py-1.5 rounded-md border border-[var(--border-default)] shadow-card font-semibold">
                      Batch: {batchId}
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleExportCSV}
                      className="h-9 shrink-0 whitespace-nowrap gap-1.5 border border-[var(--border-default)] bg-[var(--bg-surface)] text-xs font-body text-[var(--text-primary)] hover:border-[var(--brand-accent)] hover:text-[var(--brand-accent)] rounded-md font-semibold px-3 shadow-card"
                    >
                      <FileSpreadsheet className="h-4 w-4 text-[var(--brand-primary)]" />
                      Export CSV
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleExportJSON}
                      className="h-9 shrink-0 whitespace-nowrap gap-1.5 border border-[var(--border-default)] bg-[var(--bg-surface)] text-xs font-body text-[var(--text-primary)] hover:border-[var(--brand-accent)] hover:text-[var(--brand-accent)] rounded-md font-semibold px-3 shadow-card"
                    >
                      <FileJson className="h-4 w-4 text-[var(--brand-primary)]" />
                      Export JSON
                    </Button>
                  </div>
                </div>
                <AuditTable batchId={batchId} payments={payments} />
              </div>
            )}
            
            {activeTab === "payments" && !batchId && (
              <div className="text-center p-12 text-[var(--text-secondary)] font-body text-sm font-semibold border border-dashed border-[var(--border-default)] rounded-xl animate-in fade-in duration-300">
                Run a batch to see the full payments audit trail.
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
