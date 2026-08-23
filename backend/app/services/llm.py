"""
NVIDIA NIM LLM client — wraps the OpenAI Python SDK pointed at NIM's
OpenAI-compatible endpoint.

Usage:
    from app.services.llm import get_llm_client, nim_completion, nim_json_completion

Since NVIDIA NIM exposes an OpenAI-compatible API, we use the standard
`openai.OpenAI` client with a custom `base_url`.
"""

import json
import logging
from functools import lru_cache

from openai import OpenAI
from pydantic import BaseModel

from app.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache
def get_llm_client() -> OpenAI:
    """Return a singleton OpenAI client configured for NVIDIA NIM."""
    settings = get_settings()
    if not settings.NVIDIA_NIM_API_KEY:
        raise ValueError(
            "NVIDIA_NIM_API_KEY is not set. "
            "Please set it in .env or as an environment variable."
        )
    return OpenAI(
        base_url=settings.NVIDIA_NIM_BASE_URL,
        api_key=settings.NVIDIA_NIM_API_KEY,
    )


def get_langchain_nim_llm(
    temperature: float = 0.2,
    max_tokens: int = 1024,
):
    """
    Return a LangChain ChatOpenAI instance configured for NVIDIA NIM.
    NVIDIA NIM provides an OpenAI-compatible API, so ChatOpenAI works
    seamlessly with base_url and api_key overrides.
    """
    from langchain_openai import ChatOpenAI

    settings = get_settings()
    return ChatOpenAI(
        model=settings.NVIDIA_NIM_MODEL,
        openai_api_key=settings.NVIDIA_NIM_API_KEY,
        openai_api_base=settings.NVIDIA_NIM_BASE_URL,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def nim_completion(
    prompt: str,
    *,
    system: str = "You are a helpful assistant.",
    temperature: float = 0.2,
    max_tokens: int = 1024,
) -> str:
    """Simple text completion via NVIDIA NIM."""
    settings = get_settings()
    client = get_llm_client()
    response = client.chat.completions.create(
        model=settings.NVIDIA_NIM_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content or ""


def nim_json_completion(
    prompt: str,
    *,
    system: str = "You are a helpful assistant. Always respond with valid JSON.",
    temperature: float = 0.1,
    max_tokens: int = 1024,
    response_model: type[BaseModel] | None = None,
) -> dict | BaseModel:
    """
    Structured JSON completion via NVIDIA NIM.

    Strategy:
    1. Request JSON output via strict prompt instructions
       (NIM models may not support OpenAI's response_format=json_object
        reliably, so we use prompt-based JSON enforcement).
    2. Parse the response as JSON.
    3. If `response_model` is provided, validate with Pydantic.
    4. Falls back gracefully — extracts JSON from markdown fences if needed.
    """
    settings = get_settings()
    client = get_llm_client()

    json_system = (
        f"{system}\n\n"
        "IMPORTANT: You MUST respond with ONLY valid JSON. "
        "No markdown, no explanation, no code fences — just the raw JSON object."
    )

    response = client.chat.completions.create(
        model=settings.NVIDIA_NIM_MODEL,
        messages=[
            {"role": "system", "content": json_system},
            {"role": "user", "content": prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )

    raw = response.choices[0].message.content or "{}"

    # Strip markdown code fences if the model wraps output
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        # Remove first and last lines (fences)
        lines = [l for l in lines if not l.strip().startswith("```")]
        raw = "\n".join(lines)

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.warning("NIM returned invalid JSON: %s — raw: %s", e, raw[:200])
        raise ValueError(f"NIM model returned invalid JSON: {e}") from e

    if response_model is not None:
        return response_model.model_validate(parsed)

    return parsed
