"""FastAPI application entry-point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import health

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    description="AI agent that detects failed subscription/mandate payments, "
    "diagnoses root cause, and executes bounded recovery actions.",
    version="0.1.0",
)

# --- CORS (allow Next.js dev server) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routers ---
app.include_router(health.router)
