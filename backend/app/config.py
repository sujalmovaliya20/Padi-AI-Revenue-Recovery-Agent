"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Central config — reads from .env or environment variables."""

    # --- App ---
    APP_NAME: str = "Revenue Recovery Agent"
    DEBUG: bool = True

    # --- Database ---
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/revenue_recovery"

    # --- Razorpay ---
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""

    # --- LLM ---
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
