# 💸 Revenue Recovery Agent

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
          ↕ Razorpay API          ↕ LLM (OpenAI / Anthropic)
```

## Tech Stack

| Layer      | Technology                                                  |
| ---------- | ----------------------------------------------------------- |
| Frontend   | Next.js 14, TypeScript, Tailwind CSS, shadcn/ui, Recharts   |
| Backend    | Python 3.11, FastAPI, LangGraph, LangChain, Pydantic v2     |
| Database   | PostgreSQL 16 (Docker), SQLAlchemy 2.0, Alembic             |
| Payments   | Razorpay Python SDK                                         |
| AI / Agent | LangGraph state machine, OpenAI / Anthropic                 |
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

| Variable              | Description                              |
| --------------------- | ---------------------------------------- |
| `DATABASE_URL`        | PostgreSQL connection string             |
| `RAZORPAY_KEY_ID`     | Razorpay test/live key ID                |
| `RAZORPAY_KEY_SECRET` | Razorpay test/live key secret            |
| `OPENAI_API_KEY`      | OpenAI API key (for LangGraph agent)     |
| `ANTHROPIC_API_KEY`   | Anthropic API key (alternative provider) |
| `DEBUG`               | Enable debug mode (default: `true`)      |

## API Endpoints

| Method | Path      | Description                  |
| ------ | --------- | ---------------------------- |
| GET    | `/`       | Hello world / API status     |
| GET    | `/health` | Health check                 |

---

**Status:** Scaffold complete ✅ — no business logic yet.
