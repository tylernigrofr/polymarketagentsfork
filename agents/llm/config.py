from __future__ import annotations

import os
from typing import Literal

ChatProvider = Literal["openai", "anthropic", "google", "openrouter"]
EmbeddingsProvider = Literal["openai", "google", "openrouter"]


def _env_lower(name: str, default: str) -> str:
    val = os.getenv(name)
    return (val if val is not None else default).strip().lower()


def get_chat_provider_for_task(task_name: str = "default") -> ChatProvider:
    # Task-specific override first, then global.
    provider = _env_lower(f"CHAT_PROVIDER_{task_name.upper()}", _env_lower("CHAT_PROVIDER", "openai"))
    if provider not in ("openai", "anthropic", "google", "openrouter"):
        raise RuntimeError(f"Unsupported CHAT_PROVIDER value: {provider}")
    return provider  # type: ignore[return-value]


def get_chat_model_name_for_task(task_name: str = "default") -> str:
    # Task-specific override first, then global.
    return os.getenv(f"CHAT_MODEL_{task_name.upper()}", os.getenv("CHAT_MODEL", "gpt-4o-mini")).strip()


def get_embeddings_provider() -> EmbeddingsProvider:
    provider = _env_lower("EMBEDDINGS_PROVIDER", "openai")
    if provider not in ("openai", "google", "openrouter"):
        raise RuntimeError(f"Unsupported EMBEDDINGS_PROVIDER value: {provider}")
    return provider  # type: ignore[return-value]


def get_embeddings_model_name() -> str:
    return os.getenv("EMBEDDINGS_MODEL", "text-embedding-3-small").strip()

