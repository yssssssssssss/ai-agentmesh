#!/usr/bin/env python3
"""Run one redacted, read-only probe for each selected real provider."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from time import monotonic

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agentmesh.provider_status import ProviderStatus, provider_error_code  # noqa: E402

SmokeHandler = Callable[[], ProviderStatus]
_PROVIDER_ORDER = ("embedding", "o2", "web", "data", "llm")


def load_server_env(path: Path | None = None) -> None:
    env_path = path or PROJECT_ROOT / ".env"
    if not env_path.is_file():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = value.strip().strip('"').strip("'")


def _failed(name: str, configured: bool, error: BaseException, started: float) -> ProviderStatus:
    return ProviderStatus(
        name=name,
        configured=configured,
        ready=False,
        mode="fallback",
        last_error=provider_error_code(error),
        latency_ms=(monotonic() - started) * 1000,
    )


def smoke_embedding() -> ProviderStatus:
    from agentmesh.embedding import EmbeddingConfig, embed_text

    started = monotonic()
    try:
        config = EmbeddingConfig.from_env()
        configured = config.enabled and bool(config.api_url and config.api_key)
        if not configured:
            raise RuntimeError("not configured")
        vector = embed_text("AgentMesh provider readiness probe")
        if not vector:
            raise ValueError("Embedding provider returned no vector")
        return ProviderStatus(
            name="embedding", configured=True, ready=True, mode="real", latency_ms=(monotonic() - started) * 1000
        )
    except Exception as error:
        return _failed("embedding", "config" in locals() and config.enabled, error, started)


def smoke_o2() -> ProviderStatus:
    from agentmesh.o2 import O2ResearchProvider, env_flag, o2_research_provider_status

    started = monotonic()
    configured = env_flag("AGENTMESH_O2_RESEARCH_ENABLED")
    try:
        status = o2_research_provider_status()
        if not status.ready:
            raise RuntimeError(status.last_error or "not configured")
        results = O2ResearchProvider().search("AgentMesh provider readiness probe", limit=1)
        if not results:
            raise ValueError("O2 provider returned no source")
        return ProviderStatus(
            name="o2_research", configured=True, ready=True, mode="real", latency_ms=(monotonic() - started) * 1000
        )
    except Exception as error:
        return _failed("o2_research", configured, error, started)


def smoke_web() -> ProviderStatus:
    from agentmesh.web_research import MockWebSearchProvider, provider_from_env

    started = monotonic()
    provider = provider_from_env()
    configured = provider is not None and not isinstance(provider, MockWebSearchProvider)
    try:
        if not configured or provider is None:
            raise RuntimeError("not configured")
        results = provider.search("AgentMesh provider readiness probe", limit=1)
        if not results:
            raise ValueError("Web provider returned no source")
        return ProviderStatus(
            name="web_research", configured=True, ready=True, mode="real", latency_ms=(monotonic() - started) * 1000
        )
    except Exception as error:
        return _failed("web_research", configured, error, started)


def smoke_data() -> ProviderStatus:
    from agentmesh.datasources import DataSourceQuery, HTTPDataAPIConnector

    started = monotonic()
    connector = HTTPDataAPIConnector()
    configured = bool(connector.base_url)
    try:
        if not configured:
            raise RuntimeError("not configured")
        operation = os.getenv("AGENTMESH_DATA_API_SMOKE_OPERATION", "query")
        result = connector.query(
            DataSourceQuery(
                connector_name=connector.connector_name,
                operation=operation,
                parameters={"query": "AgentMesh provider readiness probe", "limit": 1},
                workspace_id="smoke",
                project_id="smoke",
                requested_by="provider_smoke",
            )
        )
        if not result.records:
            raise ValueError("Data API returned no records")
        return ProviderStatus(
            name="data_api", configured=True, ready=True, mode="real", latency_ms=(monotonic() - started) * 1000
        )
    except Exception as error:
        return _failed("data_api", configured, error, started)


def smoke_llm() -> ProviderStatus:
    from agentmesh.llm import LLMClient

    started = monotonic()
    client = LLMClient.from_env(timeout_seconds=10.0)
    configured = client is not None
    try:
        if client is None:
            raise RuntimeError("not configured")
        output = client.complete("Return a short readiness acknowledgement.", "health check")
        if not output.strip():
            raise ValueError("LLM returned no text")
        return ProviderStatus(
            name="llm", configured=True, ready=True, mode="real", latency_ms=(monotonic() - started) * 1000
        )
    except Exception as error:
        return _failed("llm", configured, error, started)


SMOKE_HANDLERS: dict[str, SmokeHandler] = {
    "embedding": smoke_embedding,
    "o2": smoke_o2,
    "web": smoke_web,
    "data": smoke_data,
    "llm": smoke_llm,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in _PROVIDER_ORDER:
        parser.add_argument(f"--{name}", action="store_true", help=f"probe the {name} provider")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    selected = [name for name in _PROVIDER_ORDER if getattr(args, name)]
    if not selected:
        build_parser().print_usage(sys.stderr)
        return 2
    load_server_env()
    statuses = [SMOKE_HANDLERS[name]() for name in selected]
    for status in statuses:
        latency = "-" if status.latency_ms is None else f"{status.latency_ms:.1f}"
        error = status.last_error or "-"
        print(
            f"{status.name}: configured={str(status.configured).lower()} "
            f"ready={str(status.ready).lower()} mode={status.mode} latency_ms={latency} error={error}"
        )
    return 0 if all(status.ready and status.mode == "real" for status in statuses) else 1


if __name__ == "__main__":
    raise SystemExit(main())
