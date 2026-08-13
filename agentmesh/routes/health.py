"""Provider health check routes."""

from __future__ import annotations

import os
import shutil

from fastapi import APIRouter, Depends

from agentmesh.datasources import data_api_provider_status, default_data_source_registry
from agentmesh.documents import CompositeDocumentParser
from agentmesh.embedding import embedding_provider_status
from agentmesh.llm import llm_provider_status, llm_timeout_config, model_config_from_env
from agentmesh.models import User
from agentmesh.o2 import O2CommandRunner, maybe_register_o2_data_connector, o2_research_provider_status
from agentmesh.provider_status import ProviderStatus, redact_url
from agentmesh.routes.deps import current_user
from agentmesh.web_research import web_research_provider_status

router = APIRouter(prefix="/api/health", tags=["health"])


def _status_payload(status: ProviderStatus, *, provider: str | None = None) -> dict[str, object]:
    payload: dict[str, object] = status.model_dump(mode="json")
    payload["provider"] = provider or status.name
    if not status.configured:
        payload["status"] = "not_configured"
    elif status.ready:
        payload["status"] = "ready"
    else:
        payload["status"] = "degraded"
    return payload


def _embedding_status() -> dict[str, object]:
    return _status_payload(embedding_provider_status())


def _llm_status() -> dict[str, object]:
    status = llm_provider_status()
    payload = _status_payload(status)
    config = model_config_from_env("default")
    if config is not None:
        payload.update(
            {
                "status": "configured" if status.ready else "degraded",
                "base_url": redact_url(config["base_url"]),
                "model": config["model_name"],
                "label": config.get("label", ""),
                "api_style": config.get("api_style", "chat_completions"),
                "timeouts": llm_timeout_config(),
            }
        )
    return payload


def _web_provider_status() -> dict[str, object]:
    status = web_research_provider_status()
    payload = _status_payload(status)
    provider_type = os.getenv("AGENTMESH_WEB_PROVIDER", "").strip().lower()
    if provider_type:
        payload["provider_type"] = provider_type
    if status.configured and not status.ready:
        payload["status"] = "command_not_found"
    return payload


def _o2_status() -> dict[str, object]:
    runner = O2CommandRunner()
    status = o2_research_provider_status(runner)
    payload = _status_payload(status, provider="o2")
    research_enabled = os.getenv("AGENTMESH_O2_RESEARCH_ENABLED", "").lower() in {"1", "true", "yes", "on"}
    data_enabled = os.getenv("AGENTMESH_O2_DATA_ENABLED", "").lower() in {"1", "true", "yes", "on"}
    payload.update(
        {
            "status": "installed" if runner.available() else "not_installed",
            "research_enabled": research_enabled,
            "data_enabled": data_enabled,
            "research_cli": os.getenv("AGENTMESH_O2_RESEARCH_CLI", "metasearch") if research_enabled else None,
            "data_cli": os.getenv("AGENTMESH_O2_DATA_CLI", "metasearch") if data_enabled else None,
        }
    )
    return payload


def _data_connectors_status() -> dict[str, object]:
    status = data_api_provider_status()
    payload = _status_payload(status, provider="data_connectors")
    registry = default_data_source_registry()
    maybe_register_o2_data_connector(registry)
    connectors = registry.list_connectors()
    payload.update({"status": "ready" if connectors else "empty", "count": len(connectors), "connectors": connectors})
    return payload


def _document_parser_status() -> dict[str, object]:
    parser = CompositeDocumentParser()
    supported = sorted(parser.supported_extensions)
    try:
        import fitz  # noqa: F401

        pdf_available = True
    except ImportError:
        pdf_available = False
    ocr_available = shutil.which(os.getenv("AGENTMESH_TESSERACT_COMMAND", "tesseract")) is not None
    return {
        "provider": "document_parser",
        "status": "ready" if pdf_available and ocr_available else "partial",
        "supported_extensions": supported,
        "pdf_available": pdf_available,
        "word_available": True,
        "slide_available": True,
        "ocr_available": ocr_available,
        "message": "支持 UTF-8 文本、Markdown、PDF、Word、PPT 和图片 OCR。",
    }


@router.get("/providers")
def provider_health_check(_: User = Depends(current_user)) -> dict[str, object]:
    """Return secret-safe provider readiness for authenticated users."""

    providers = [
        _embedding_status(),
        _o2_status(),
        _web_provider_status(),
        _data_connectors_status(),
        _llm_status(),
    ]
    all_ready = all(bool(item["ready"]) for item in providers)
    return {
        "overall": "healthy" if all_ready else "degraded",
        "providers": [*providers, _document_parser_status()],
    }
