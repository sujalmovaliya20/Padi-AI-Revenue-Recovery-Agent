"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Central config — reads from .env or environment variables."""

    # --- App ---
    APP_NAME: str = "Revenue Recovery Agent"
    DEBUG: bool = True
    PORT: int = 8000
    ALLOWED_ORIGINS: str = ""  # Comma-separated list, e.g. "https://my-app.vercel.app,https://custom-domain.com"

    # --- Database ---
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/revenue_recovery"

    # --- Razorpay ---
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""

    # --- LLM (NVIDIA NIM — OpenAI-compatible API) ---
    NVIDIA_NIM_API_KEY: str = ""
    NVIDIA_NIM_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    NVIDIA_NIM_MODEL: str = "meta/llama-3.1-70b-instruct"

    model_config = {
        "env_file": (".env", "../.env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()
