"""Provider health check routes."""

from __future__ import annotations

import os
import shutil

from fastapi import APIRouter, Depends

from agentmesh.datasources import default_data_source_registry
from agentmesh.documents import CompositeDocumentParser
from agentmesh.llm import model_config_from_env
from agentmesh.models import User
from agentmesh.o2 import O2CommandRunner, maybe_register_o2_data_connector
from agentmesh.routes.deps import current_user

router = APIRouter(prefix="/api/health", tags=["health"])


def _llm_status() -> dict[str, object]:
    """检查 LLM 模型服务配置状态。"""
    default_config = model_config_from_env("default")
    if default_config is None or not default_config.get("api_key"):
        return {
            "provider": "llm",
            "status": "not_configured",
            "message": "未配置 AI_API_URL / AI_API_KEY / AI_MODEL 或 AGENTMESH_LLM_BASE_URL / API_KEY / MODEL",
        }
    return {
        "provider": "llm",
        "status": "configured",
        "base_url": default_config["base_url"],
        "model": default_config["model_name"],
        "label": default_config.get("label", ""),
        "api_style": default_config.get("api_style", "chat_completions"),
    }


def _web_provider_status() -> dict[str, object]:
    """检查 Web 研究 provider 配置状态。"""
    provider = os.getenv("AGENTMESH_WEB_PROVIDER", "").strip()
    if not provider:
        return {
            "provider": "web_research",
            "status": "not_configured",
            "message": "未配置 AGENTMESH_WEB_PROVIDER（可选: opencli, agent_browser）",
        }

    if provider == "opencli":
        command = os.getenv("AGENTMESH_OPENCLI_COMMAND", "opencli")
    elif provider == "agent_browser":
        command = os.getenv("AGENTMESH_AGENT_BROWSER_COMMAND", "agent-browser")
    else:
        command = provider

    binary_found = shutil.which(command) is not None
    return {
        "provider": "web_research",
        "status": "ready" if binary_found else "command_not_found",
        "provider_type": provider,
        "command": command,
        "binary_found": binary_found,
    }


def _o2_status() -> dict[str, object]:
    """检查 Oxygen-CLI 状态。"""
    runner = O2CommandRunner()
    installed = runner.available()
    if not installed:
        return {
            "provider": "o2",
            "status": "not_installed",
            "binary": runner.binary,
            "message": f"Oxygen-CLI ({runner.binary}) 未找到",
        }

    research_enabled = os.getenv("AGENTMESH_O2_RESEARCH_ENABLED", "").lower() in {"1", "true", "yes"}
    data_enabled = os.getenv("AGENTMESH_O2_DATA_ENABLED", "").lower() in {"1", "true", "yes"}

    return {
        "provider": "o2",
        "status": "installed",
        "binary": runner.binary,
        "research_enabled": research_enabled,
        "data_enabled": data_enabled,
        "research_cli": os.getenv("AGENTMESH_O2_RESEARCH_CLI", "metasearch") if research_enabled else None,
        "data_cli": os.getenv("AGENTMESH_O2_DATA_CLI", "metasearch") if data_enabled else None,
    }


def _data_connectors_status() -> dict[str, object]:
    """检查数据源连接器注册状态。"""
    registry = default_data_source_registry()
    maybe_register_o2_data_connector(registry)
    connectors = registry.list_connectors()
    return {
        "provider": "data_connectors",
        "status": "ready" if connectors else "empty",
        "count": len(connectors),
        "connectors": connectors,
    }


def _document_parser_status() -> dict[str, object]:
    """检查文档解析器支持状态。"""
    parser = CompositeDocumentParser()
    supported = sorted(parser.supported_extensions)
    pdf_available = False
    try:
        import fitz  # noqa: F401

        pdf_available = True
    except ImportError:
        pass
    ocr_command = os.getenv("AGENTMESH_TESSERACT_COMMAND", "tesseract")
    ocr_available = shutil.which(ocr_command) is not None
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
    """返回所有外部 provider 的健康状态。"""
    checks = [
        _llm_status(),
        _web_provider_status(),
        _o2_status(),
        _data_connectors_status(),
        _document_parser_status(),
    ]
    all_ready = all(c["status"] in ("ready", "configured", "installed") for c in checks)
    return {
        "overall": "healthy" if all_ready else "degraded",
        "providers": checks,
    }
