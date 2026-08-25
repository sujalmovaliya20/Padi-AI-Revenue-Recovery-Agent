# Revenue Recovery Agent

**Track 03 — AI Revenue Recovery | Razorpay Buildathon 2026**

An autonomous agent that detects failed subscription/mandate payments, diagnoses the root cause, executes a bounded recovery workflow on Razorpay's test-mode APIs, and reports measured revenue recovered — with a full audit trail, human approval gates, and cost-aware stopping rules.

`LangGraph` · `NVIDIA NIM` · `Razorpay Test-Mode API` · `FastAPI` · `Next.js`

---

## Table of Contents

- [The Problem](#the-problem)
- [The Solution](#the-solution)
- [Live Demo Screenshots](#live-demo-screenshots)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Tech Stack & Why](#tech-stack--why)
- [Results](#results)
- [What Broke & How We Fixed It](#what-broke--how-we-fixed-it)
- [Setup & Run Locally](#setup--run-locally)
- [Project Structure](#project-structure)
- [Judging Bar — Self Check](#judging-bar--self-check)

---

## The Problem

Revenue loss from failed recurring payments rarely happens in one clean step. A card expires, a bank declines a debit, a mandate gets revoked — and unless someone (or something) intervenes, that revenue is simply gone. Most businesses handle this manually or not at all.

**This agent closes that loop end-to-end**: detect the failure → diagnose why it happened → pick the right bounded recovery action → execute it on real Razorpay test-mode infrastructure → track the outcome → know when to stop.

## The Solution

A single-domain, deeply-built subscription/mandate retry recovery agent built on LangGraph, with:

- Rule-first root-cause classification (LLM only for ambiguous cases — NVIDIA NIM)
- Policy-gated intervention selection, not free-form LLM decision-making
- Real Razorpay test-mode execution (Orders, Payment Links, Subscriptions APIs)
- A hard, human-in-the-loop approval gate for high-value transactions
- A cost-aware stop rule — the agent stops retrying when the cost of another attempt exceeds the expected recovery value, not just after N tries
- A live dashboard with full node-by-node audit trail and plain-English decision summaries

---

## Live Demo Screenshots

> _Add screenshots here before submission — recommended shots:_
> 1. `docs/screenshots/dashboard-overview.png` — main dashboard after a batch run (metric cards + funnel)
> 2. `docs/screenshots/audit-trail.png` — expanded audit trail accordion showing the decision chain
> 3. `docs/screenshots/pending-approval.png` — the human-in-the-loop approval card in action
> 4. `docs/screenshots/resilience-test.png` — the resilience test panel showing a caught + recovered failure
> 5. `docs/screenshots/dark-mode.png` — dark theme toggle
>
> Embed with: `![Dashboard overview](docs/screenshots/dashboard-overview.png)`

---

## Key Features

| Feature | Why it matters |
|---|---|
| **Rule-engine + LLM-fallback classification** | Cheap, fast, deterministic for known cases; LLM only where genuinely ambiguous — shows engineering judgment, not LLM-everything |
| **Policy-gated intervention selection** | Every recovery action passes a decision table + a hard whitelist gate before execution — nothing auto-fires outside allowed bounds |
| **Human-in-the-loop approval** | Payments above ₹5,000 pause the graph (via LangGraph `interrupt_before`) and wait for a real approve/reject click on the dashboard |
| **Cost-aware stop rule** | Stops retrying when estimated retry cost exceeds ~30% of the payment's value — a financially-reasoned stop, not just a retry counter |
| **Resilience test panel** | Deliberately injects an API timeout/failure and shows the agent catching it, retrying with backoff, and recovering gracefully — no crash, no silent skip |
| **Promise-to-pay tracking** | Customer payment promises are tracked with a scheduled re-check; broken promises auto-escalate |
| **Full audit trail** | Every node writes its input state, decision, reason, and tool result — persisted via LangGraph's checkpointer, browsable per payment on the dashboard |
| **Plain-English decision summaries** | Each payment gets a deterministic one-line explanation (no LLM) so evaluators can scan outcomes without expanding every node |
| **Agent vs. no-agent comparison** | Shows ₹0 recovered baseline vs. actual agent recovery — makes the value proposition immediate |
| **Light/dark theme, accessible typography** | WCAG AA-checked contrast, consistent type scale, no color-only status signaling |

---

## Architecture

See [`ARCHITECTURE.md`](./ARCHITECTURE.md) for the full breakdown — state schema, node-by-node design, gating logic, and data flow diagram.

**One-line summary:** a LangGraph state machine — `classify_failure → select_intervention → check_gate → execute_action → check_stop_rule` — loops until a payment is recovered, escalated, or stopped, with every transition checkpointed for audit.

```
Failed Payment Batch
        │
        ▼
 classify_failure  (rule engine, LLM fallback via NVIDIA NIM)
        │
        ▼
 select_intervention  (policy table + gated LLM fallback)
        │
        ▼
 check_gate  (whitelist + amount ceiling + retry limit)
        │
   ┌────┴────┐
   ▼         ▼
execute    escalate_human
 action    (or pause for approval)
   │
   ▼
check_stop_rule  (max retries / max days / cost > value)
   │
   ├── loop back to select_intervention
   └── terminate → recovered / escalated / stopped
```

---

## Tech Stack & Why

| Choice | Reasoning |
|---|---|
| **LangGraph** over AutoGen / CrewAI | The judging bar itself ("bounded, gated, explainable, audit trail, stopping rules") maps directly onto LangGraph's primitives — conditional edges, `interrupt_before`, and the checkpointer give deterministic control and free audit logging. AutoGen/CrewAI are built for open-ended multi-agent conversation, not hard-gated financial actions. |
| **NVIDIA NIM** (OpenAI-compatible) over OpenAI/Anthropic direct | Used only as a fallback for ambiguous classification/intervention cases — the rule engine handles the majority deterministically, keeping the system cheap, fast, and auditable. |
| **Rule engine first, LLM second** | Reduces cost, increases determinism, and demonstrates the LLM was used *where it adds value*, not everywhere by default. |
| **FastAPI** | Async background batch processing, clean typed endpoints for the dashboard to poll. |
| **Razorpay Test-Mode APIs (real, not mocked)** | Orders, Payment Links, and Subscriptions calls are real sandbox calls against provisioned test orders — not faked responses. |
| **Next.js + Tailwind + shadcn/ui** | Fast to build a live-polling dashboard with accessible, themeable components. |

---

## Results

> _Fill in with your final batch numbers before submission — pull these from the dashboard after a fresh run._

| Metric | Value |
|---|---|
| Batch size | 75 synthetic failed payments |
| Total revenue at risk | ₹___ |
| Total revenue recovered | ₹___ |
| Recovery rate | ___% |
| Escalation rate | ___% |
| Avg. retries to recovery | ___ |
| Cost-aware early stops | ___ payments, ~₹___ saved |
| Resilience test | 1 injected failure → caught → recovered gracefully |

Honest exception list: all escalated/stopped payments and their reasons are browsable in the "Exception List" view on the dashboard — nothing is hidden or cherry-picked.

---

## What Broke & How We Fixed It

> _Replace with your real build issues — keep 1–2 genuine ones, don't invent._

**1. [Example shape — replace with real issue]**
- **What broke:** `npm ci` failed during Docker build — lock file out of sync with `package.json` (missing `picomatch@4.0.5`).
- **How we found it:** Docker build logs showed `EUSAGE` error on the frontend build stage.
- **Fix:** Regenerated `package-lock.json` with `npm install` locally, committed the sync, and added a proper `.dockerignore` to stop `node_modules`/`.next` from bloating the build context (was transferring 380MB+ per build).

**2. [Second real issue — e.g. NIM function-calling reliability, LangGraph checkpoint resume, Razorpay test-order mapping]**
- **What broke:** _describe_
- **How we found it:** _describe_
- **Fix:** _describe_

---

## Setup & Run Locally

```bash
# clone
git clone <your-repo-url>
cd revenue-recovery-agent

# environment
cp .env.example .env
# fill in RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET (test mode),
# NVIDIA_NIM_API_KEY, DATABASE_URL

# run everything
docker-compose up --build

# backend: http://localhost:8000
# frontend: http://localhost:3000
```

To seed a fresh synthetic batch and provision matching Razorpay test-mode orders:

```bash
python data/generate_synthetic_batch.py
python data/create_test_orders.py
```

---

## Project Structure

```
/backend
  /agent        — LangGraph state machine (graph.py)
  /tools        — Razorpay test-mode API wrappers
  /models       — Pydantic + SQLAlchemy schemas
  main.py       — FastAPI app & endpoints
/frontend
  /app          — Next.js App Router pages
  /components   — dashboard, audit trail, approval, resilience panels
/data
  generate_synthetic_batch.py
  create_test_orders.py
ARCHITECTURE.md
PITCH_SCRIPT.md
README.md
```

---

## Judging Bar — Self Check

| Requirement | Where it's addressed |
|---|---|
| Detect revenue at risk | `classify_failure` node, synthetic batch ingestion |
| Determine right intervention | `select_intervention` node, policy table |
| Execute bounded recovery workflow | `check_gate` + `execute_action`, whitelist + amount ceiling |
| Measured money recovered across a batch | `/batch/{id}/metrics` endpoint, dashboard metric cards |
| Compliant escalation | `mandate_revoked` → immediate escalation, no forced retry |
| Stopping rules | `check_stop_rule` — max retries, max days, cost-aware stop |
| Audit trail | LangGraph checkpointer + `audit_log` table + dashboard accordion |
| One failure handled gracefully | Resilience Test panel — injected timeout, caught, retried, recovered |

---

Built for the Razorpay Buildathon 2026 — Track 03: AI Revenue Recovery.
