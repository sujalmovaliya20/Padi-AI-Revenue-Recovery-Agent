# 💸 Padi(Revenue Recovery Agent) - Live :- https://ai-revenue-recovery-agent-phi.vercel.app/

> **Hackathon Prototype** — An AI agent that detects failed subscription/mandate payments, diagnoses root cause, and executes bounded recovery actions.

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  Frontend (Next.js 14 · App Router · shadcn/ui)     │  :3000
├─────────────────────────────────────────────────────┤
│  Backend  (FastAPI · LangGraph · SQLAlchemy)         │  :8000
├─────────────────────────────────────────────────────┤
│  Database (PostgreSQL 16)                            │  :5432
└─────────────────────────────────────────────────────┘
          ↕ Razorpay API          ↕ LLM (NVIDIA NIM)
```

## The Problem

Failed subscription and mandate payments silently bleed revenue — most businesses only discover the loss weeks later, if at all, and manual dunning recovers a fraction of what's recoverable. This agent detects every failed payment the moment it drops, classifies the root cause, selects a bounded intervention, and executes the recovery action end-to-end against real Razorpay test-mode infrastructure — replacing the manual spreadsheet-and-email loop with a deterministic, auditable state machine.

## What This Agent Does

- **Rule-first root-cause classification** of failed payments — LLM fallback via NVIDIA NIM (`meta/llama-3.1-70b-instruct`) fires only for ambiguous/unmapped failure reasons
- **Policy-gated intervention selection** — chooses `retry_now` / `retry_later` / `switch_payment_method` / `escalate_human` from a deterministic decision table keyed on `(fail_category, retry_count)`, not free-form LLM choice
- **Hard gate check before any money-moving action** — category→action whitelist matrix + retry-count ceiling (3) + amount ceiling (₹5,000) enforced deterministically before any tool is invoked
- **Human-in-the-loop approval** — payments above ₹5,000 pause the LangGraph execution (via conditional edge routing to `END` at the gate checkpoint) and wait for a real approve/reject decision before the `execute_action` node runs
- **Real Razorpay test-mode execution** — `retry_charge`, `send_payment_link`, `check_mandate_status` all call actual Razorpay sandbox APIs, not mocked responses
- **Cost-aware stop rule** — stops retrying a payment early when the estimated cumulative cost of intervention (₹150/attempt × attempt count) exceeds 30% of the payment's invoice value, in addition to standard max-retries (3) and max-days (7) limits
- **Promise-to-pay tracking** — logs customer payment commitments with a target date, auto-escalates to human specialist queue if a promised date passes without payment (via fast-forward simulation endpoint)
- **Full audit trail** — every LangGraph node writes its input state, decision, reason, and tool result into `intervention_history`, persisted via the `MemorySaver` checkpointer, queryable per payment via the audit API
- **Deterministic plain-English decision summaries** generated per payment (rule-based sentence composer using `generate_summary()`, not LLM) for fast human review — pattern: `"[category] detected ([reason]) → [action] → [outcome]"`
- **Resilience handling** — API timeouts (`RazorpayTimeoutError`), rate-limits (`RazorpayRateLimitError`), and invalid-order errors (`RazorpayInvalidOrderError`) from Razorpay are caught and routed to graceful fallback (retry-with-backoff, queue-for-later, or immediate escalation) — the batch never crashes on a single failed call

## Agent Workflow (LangGraph State Machine)

```
                  Failed Payment Batch
                          │
                          ▼
               ┌─────────────────────┐
               │  classify_failure   │
               └────────┬────────────┘
                         │
                         ▼
               ┌─────────────────────┐
               │ select_intervention │
               └────────┬────────────┘
                         │
                         ▼
               ┌─────────────────────┐
               │     check_gate      │
               └────────┬────────────┘
                    ┌────┴─────┐
                    ▼          ▼
             execute_action   END (pause for
                    │         human approval
                    ▼         or escalate)
               ┌─────────────────────┐
               │   track_promise     │
               └────────┬────────────┘
                         │
                         ▼
               ┌─────────────────────┐
               │   check_stop_rule   │
               └────────┬────────────┘
                    ┌────┴─────┐
                    ▼          ▼
          select_intervention  END
             (loop back)    (recovered / escalated /
                             stopped / awaiting_promise)
```

| Node | Role |
| --- | --- |
| `classify_failure` | Maps raw `fail_reason` string to a canonical category (`insufficient_funds`, `expired_card`, `bank_decline`, `mandate_revoked`, `technical_error`) using a rule table; calls NVIDIA NIM only if no rule matches |
| `select_intervention` | Picks the next recovery action from a policy decision table keyed on `(fail_category, retry_count)`; LLM fallback only for uncovered category combinations |
| `check_gate` | Deterministic safety gate — validates the proposed action against a category→action whitelist, enforces max 3 retries, and pauses execution for human approval on amounts > ₹5,000 |
| `execute_action` | Dispatches the approved action to real Razorpay sandbox tools (`retry_charge`, `send_payment_link`, `check_mandate_status`) with full exception handling for timeouts, rate-limits, and invalid orders |
| `track_promise` | Detects customer promise-to-pay signals, logs the commitment date, and sets status to `awaiting_promise` to pause the retry loop |
| `check_stop_rule` | Evaluates terminal conditions: payment recovered, cost ceiling breached (cumulative retry cost > 30% of invoice), max retries (3) exceeded, or recovery window (7 days) expired — routes back to `select_intervention` or terminates |

## Why LangGraph

The judging criteria — **bounded autonomy, hard gates, explainable decisions, full audit trail, and autonomous stopping rules** — map directly onto LangGraph primitives: conditional edges for branching (`route_after_gate`, `route_after_stop_rule`), checkpoint-based pause/resume for human-in-the-loop approval, and the built-in `MemorySaver` checkpointer for per-payment state persistence. This is a controlled, gated financial workflow — not an open-ended multi-agent conversation — which is why LangGraph was chosen over frameworks like AutoGen or CrewAI that optimize for free-form agent collaboration rather than deterministic state machines with hard safety invariants.

## Tech Stack

| Layer      | Technology                                                  |
| ---------- | ----------------------------------------------------------- |
| Frontend   | Next.js 14, TypeScript, Tailwind CSS, shadcn/ui, Recharts   |
| Backend    | Python 3.11, FastAPI, LangGraph, LangChain, Pydantic v2     |
| Database   | PostgreSQL 16 (Docker), SQLAlchemy 2.0, Alembic             |
| Payments   | Razorpay Python SDK                                         |
| AI / Agent | LangGraph state machine, NVIDIA NIM (meta/llama-3.1-70b)    |
| DevOps     | Docker Compose, python-dotenv                               |

## Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── agent/          # LangGraph recovery workflows
│   │   ├── routers/        # FastAPI route handlers
│   │   ├── services/       # Business logic (Razorpay, etc.)
│   │   ├── config.py       # Pydantic Settings (env vars)
│   │   ├── database.py     # SQLAlchemy engine & session
│   │   ├── main.py         # FastAPI app entry-point
│   │   ├── models.py       # ORM models
│   │   └── schemas.py      # Pydantic v2 request/response DTOs
│   ├── agent/              # Core graph.py (1,147 lines) — all 6 nodes, edges, checkpointer
│   ├── tools/              # Razorpay SDK wrappers with fault injection
│   ├── models/             # Shared Pydantic schemas & enums
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/            # Next.js App Router pages
│   │   ├── components/ui/  # shadcn/ui components
│   │   └── lib/            # Utilities
│   ├── Dockerfile
│   └── package.json
├── data/
│   └── generate_payments.py  # Synthetic dataset generation
├── docker-compose.yml
├── .env.example
└── README.md
```

## Quick Start

### Prerequisites

- **Python 3.11+**
- **Node.js 20+** & npm
- **Docker** (for PostgreSQL, or provide your own Postgres)

### 1. Clone & configure environment

```bash
cp .env.example .env
# Edit .env with your API keys
```

### 2. Start PostgreSQL

```bash
docker compose up db -d
```

### 3. Run the backend

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload
```

Backend is live at **http://localhost:8000** — visit `/` or `/health` to verify.

### 4. Run the frontend

```bash
cd frontend
npm install   # already done if you cloned fresh
npm run dev
```

Frontend is live at **http://localhost:3000** — the landing page will show backend connectivity status.

### 5. (Optional) Run everything via Docker Compose

```bash
docker compose up --build
```

## Environment Variables

| Variable              | Description                                                      |
| --------------------- | ---------------------------------------------------------------- |
| `DATABASE_URL`        | PostgreSQL connection string                                     |
| `RAZORPAY_KEY_ID`     | Razorpay test/live key ID                                        |
| `RAZORPAY_KEY_SECRET` | Razorpay test/live key secret                                    |
| `NVIDIA_NIM_API_KEY`  | NVIDIA NIM API key                                               |
| `NVIDIA_NIM_BASE_URL` | NVIDIA NIM base URL (default: https://integrate.api.nvidia.com/v1)|
| `NVIDIA_NIM_MODEL`    | NVIDIA NIM Model (e.g. meta/llama-3.1-70b-instruct)              |
| `DEBUG`               | Enable debug mode (default: `true`)                              |

## API Endpoints

| Method | Path | Description |
| ------ | ---- | ----------- |
| GET | `/` | API status and endpoint directory |
| GET | `/health` | Health check |
| POST | `/batch/run` | Launch batch recovery — processes all pending payments (or specific IDs) through the LangGraph agent in background |
| GET | `/batch/{batch_id}/status` | Real-time progress polling — processed count, progress %, live status distribution |
| GET | `/batch/{batch_id}/results` | Final state of every payment in the batch |
| GET | `/batch/{batch_id}/audit/{payment_id}` | Full per-payment audit trail — node transitions, decisions, reasons, tool call results |
| GET | `/batch/{batch_id}/metrics` | Aggregate ROI metrics — revenue at risk, recovered, recovery rate %, escalation rate, avg retries, cost-aware stops, savings, breakdown by fail category |
| GET | `/batch/{batch_id}/pending-approvals` | List all payments currently paused at the human approval gate (amount > ₹5,000) |
| POST | `/batch/{batch_id}/approve/{payment_id}` | Submit approve/reject decision for a gated payment — resumes LangGraph execution from checkpoint |
| GET | `/batch/{batch_id}/promise-tracker` | List all payments in `awaiting_promise` state with their promised payment dates |
| POST | `/batch/{batch_id}/fast-forward` | Time-simulation for demos — fast-forwards N days, evaluates promise-to-pay deadlines, auto-resolves as kept (recovered) or broken (escalated) |
| GET | `/batch/{batch_id}/export` | Export full batch metadata, aggregate metrics, and every payment's complete audit trail as JSON |
| POST | `/batch/reset` | Reset demo state — clears all batches, regenerates 75 fresh synthetic payments, provisions live Razorpay test orders |
| POST | `/demo/trigger-resilience-test` | Inject a controlled fault (API_TIMEOUT / RATE_LIMIT / INVALID_ORDER) and execute a single payment through the full agent to verify graceful fallback |

## Results

Representative metrics from a 75-payment synthetic batch run on Razorpay test-mode:

| Metric | Value |
| ------ | ----- |
| Total payments processed | 75 |
| Total revenue at risk | ₹2,82,459 |
| Total revenue recovered | ₹1,46,878 |
| Recovery rate | 52.0% |
| Escalation rate | 20.0% |
| Avg retries to recovery | 1.3 |
| Cost-aware early stops | 8 |
| Estimated ₹ saved by early stops | ₹2,400 |
| Payments awaiting promise | ~6 |
| Human approval gates triggered | ~12 |

> **Note:** These numbers come from the synthetic dataset generator — each batch run produces slightly different results due to stochastic promise-to-pay triggers (~20% probability) and simulated payment outcomes. Run `POST /batch/run` and `GET /batch/{batch_id}/metrics` to get your own measured results.

---

**Status:** Core agent + full recovery workflow complete — built for **Track 03, Razorpay Buildathon 2026.** 🚀
