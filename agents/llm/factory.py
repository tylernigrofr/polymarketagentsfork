from __future__ import annotations

from dataclasses import dataclass

from agents.llm.config import (
    ChatProvider,
    EmbeddingsProvider,
    get_chat_model_name_for_task,
    get_chat_provider_for_task,
    get_embeddings_model_name,
    get_embeddings_provider,
)


@dataclass(frozen=True)
class LLMRuntimeInfo:
    chat_provider: ChatProvider
    chat_model: str
    embeddings_provider: EmbeddingsProvider
    embeddings_model: str


def get_chat_model(task_name: str = "default", temperature: float = 0.0):
    provider = get_chat_provider_for_task(task_name)
    model = get_chat_model_name_for_task(task_name)

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=model, temperature=temperature)

    if provider == "openrouter":
        from langchain_openai import ChatOpenAI
        import os

        base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "Missing OPENROUTER_API_KEY (or OPENAI_API_KEY fallback) for OpenRouter."
            )
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=api_key,
            base_url=base_url,
        )

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(model=model, temperature=temperature)

    if provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(model=model, temperature=temperature)

    raise RuntimeError(f"Unsupported chat provider: {provider}")


def get_embedding_model():
    provider = get_embeddings_provider()
    model = get_embeddings_model_name()

    if provider == "openai":
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(model=model)

    if provider == "google":
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        return GoogleGenerativeAIEmbeddings(model=model)

    if provider == "openrouter":
        # OpenRouter is OpenAI-compatible for chat; embeddings support depends on the model.
        # We treat it as OpenAI-compatible embeddings endpoint via base_url if provided.
        from langchain_openai import OpenAIEmbeddings
        import os

        base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "Missing OPENROUTER_API_KEY (or OPENAI_API_KEY fallback) for OpenRouter."
            )
        return OpenAIEmbeddings(model=model, api_key=api_key, base_url=base_url)

    raise RuntimeError(f"Unsupported embeddings provider: {provider}")


def get_runtime_info(task_name: str = "default") -> LLMRuntimeInfo:
    chat_provider = get_chat_provider_for_task(task_name)
    chat_model = get_chat_model_name_for_task(task_name)
    emb_provider = get_embeddings_provider()
    emb_model = get_embeddings_model_name()
    return LLMRuntimeInfo(
        chat_provider=chat_provider,
        chat_model=chat_model,
        embeddings_provider=emb_provider,
        embeddings_model=emb_model,
    )

