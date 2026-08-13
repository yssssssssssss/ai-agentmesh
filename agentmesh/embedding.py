"""Embedding client for vector search."""

from __future__ import annotations

import logging
import os
import struct

import httpx

logger = logging.getLogger(__name__)

EMBEDDING_API_URL = os.getenv("AGENTMESH_EMBEDDING_API_URL", "http://llm-gw.jd.local/v1/embeddings")
EMBEDDING_API_KEY = os.getenv("AGENTMESH_EMBEDDING_API_KEY", "ce86bac4424c4a968fc30cc75323ca2a")
EMBEDDING_MODEL = os.getenv("AGENTMESH_EMBEDDING_MODEL", "Qwen3-Embedding-8B-joybuilder")
EMBEDDING_DIMENSIONS = 4096
EMBEDDING_ENABLED = os.getenv("AGENTMESH_EMBEDDING_ENABLED", "true").lower() in {"1", "true", "yes", "on"}

_client: httpx.Client | None = None


def _get_client() -> httpx.Client:
    global _client
    if _client is None:
        _client = httpx.Client(timeout=30.0)
    return _client


def embed_text(text: str) -> list[float] | None:
    if not EMBEDDING_ENABLED or not text.strip():
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
    except Exception as exc:
        logger.warning("Embedding API call failed: %s", exc)
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
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
