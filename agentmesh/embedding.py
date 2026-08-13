"""Embedding client for vector search."""

from __future__ import annotations

import logging
import os
import struct
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class EmbeddingConfig:
    enabled: bool
    api_url: str | None
    api_key: str | None
    model: str
    dimensions: int
    timeout_seconds: float

    @classmethod
    def from_env(cls) -> EmbeddingConfig:
        enabled = os.getenv("AGENTMESH_EMBEDDING_ENABLED", "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        api_url = os.getenv("AGENTMESH_EMBEDDING_API_URL", "").strip() or None
        api_key = os.getenv("AGENTMESH_EMBEDDING_API_KEY", "").strip() or None
        if enabled and (api_url is None or api_key is None):
            raise ValueError("Embedding requires API URL and API key")
        return cls(
            enabled=enabled,
            api_url=api_url,
            api_key=api_key,
            model=os.getenv("AGENTMESH_EMBEDDING_MODEL", "Qwen3-Embedding-8B-joybuilder"),
            dimensions=4096,
            timeout_seconds=30.0,
        )


_config = EmbeddingConfig.from_env()
EMBEDDING_API_URL = _config.api_url
EMBEDDING_API_KEY = _config.api_key
EMBEDDING_MODEL = _config.model
EMBEDDING_DIMENSIONS = _config.dimensions
EMBEDDING_ENABLED = _config.enabled

_client: httpx.Client | None = None


def _get_client() -> httpx.Client:
    global _client
    if _client is None:
        _client = httpx.Client(timeout=_config.timeout_seconds)
    return _client


def embed_text(text: str) -> list[float] | None:
    if not EMBEDDING_ENABLED or not EMBEDDING_API_URL or not EMBEDDING_API_KEY or not text.strip():
        return None
    try:
        response = _get_client().post(
            EMBEDDING_API_URL,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {EMBEDDING_API_KEY}",
            },
            json={"model": EMBEDDING_MODEL, "input": text[:2000]},
        )
        response.raise_for_status()
        data = response.json()
        return data["data"][0]["embedding"]
    except Exception:
        logger.warning("Embedding API call failed")
        return None


def embed_texts(texts: list[str]) -> list[list[float] | None]:
    if not EMBEDDING_ENABLED:
        return [None] * len(texts)
    results: list[list[float] | None] = []
    for text in texts:
        results.append(embed_text(text))
    return results


def serialize_embedding(embedding: list[float]) -> bytes:
    return struct.pack(f"{len(embedding)}f", *embedding)


def deserialize_embedding(data: bytes) -> list[float]:
    count = len(data) // 4
    return list(struct.unpack(f"{count}f", data))


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
