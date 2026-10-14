"""Embedding provider wrapper. Swap providers via EMBEDDING_PROVIDER in .env."""
from functools import lru_cache

from app.core.config import settings

BATCH_SIZE = 50


class EmbeddingError(Exception):
    pass


@lru_cache
def _gemini():
    from google import genai

    return genai.Client(api_key=settings.gemini_api_key)


@lru_cache
def _openai():
    from openai import OpenAI

    return OpenAI(api_key=settings.openai_api_key)


def _embed_batch(texts: list[str], is_query: bool) -> list[list[float]]:
    if settings.embedding_provider == "gemini":
        from google.genai import types

        resp = _gemini().models.embed_content(
            model=settings.gemini_embedding_model,
            contents=texts,
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_QUERY" if is_query else "RETRIEVAL_DOCUMENT",
                output_dimensionality=settings.embedding_dim,
            ),
        )
        return [list(e.values) for e in resp.embeddings]
    resp = _openai().embeddings.create(
        model=settings.openai_embedding_model, input=texts, dimensions=settings.embedding_dim
    )
    return [d.embedding for d in resp.data]


def embed_texts(texts: list[str], *, is_query: bool = False) -> list[list[float]]:
    vectors: list[list[float]] = []
    try:
        for i in range(0, len(texts), BATCH_SIZE):
            vectors.extend(_embed_batch(texts[i : i + BATCH_SIZE], is_query))
    except Exception as exc:
        raise EmbeddingError(f"Embedding request failed: {str(exc)[:200]}") from exc
    if len(vectors) != len(texts) or any(len(v) != settings.embedding_dim for v in vectors):
        raise EmbeddingError("Embedding provider returned unexpected vector sizes.")
    return vectors
