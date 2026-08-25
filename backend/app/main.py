"""FastAPI application entry-point for Revenue Recovery Agent."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db
from app.routers import health, batch, demo

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    try:
        init_db()
        logger.info("Database tables initialized successfully.")
    except Exception as e:
        logger.warning("Could not auto-initialize database on startup (PostgreSQL may be offline): %s", e)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="AI agent that detects failed subscription/mandate payments, "
    "diagnoses root cause, and executes bounded recovery actions.",
    version="0.1.0",
    lifespan=lifespan,
)

# --- CORS (allow Next.js frontend origins) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routers ---
app.include_router(health.router)
app.include_router(batch.router)
app.include_router(demo.router)


@app.get("/")
def root():
    return {
        "service": settings.APP_NAME,
        "status": "online",
        "version": "0.1.0",
        "endpoints": {
            "health": "/health",
            "run_batch": "POST /batch/run",
            "batch_status": "GET /batch/{batch_id}/status",
            "batch_results": "GET /batch/{batch_id}/results",
            "batch_audit": "GET /batch/{batch_id}/audit/{payment_id}",
            "batch_metrics": "GET /batch/{batch_id}/metrics",
            "promise_tracker": "GET /batch/{batch_id}/promise-tracker",
            "fast_forward": "POST /batch/{batch_id}/fast-forward",
            "resilience_test": "POST /demo/trigger-resilience-test",
            "docs": "/docs",
        },
    }
