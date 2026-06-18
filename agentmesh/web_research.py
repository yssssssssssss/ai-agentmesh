from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
from typing import Any, Protocol

from pydantic import BaseModel, Field

from agentmesh.acquisition import AcquisitionAgent, AcquisitionRequest, AcquisitionResult
from agentmesh.models import Source


class WebSearchResult(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    url: str = Field(min_length=1, max_length=1000)
    snippet: str = Field(default="", max_length=2000)


class WebSearchProvider(Protocol):
    def search(self, query: str, limit: int = 3) -> list[WebSearchResult]: ...


class CommandWebSearchProvider:
    def __init__(self, command: str, command_template: str | None = None):
        self.command = command
        self.command_template = command_template

    def search(self, query: str, limit: int = 3) -> list[WebSearchResult]:
        argv = self._argv(query, limit)
        executable = shutil.which(argv[0])
        if executable is None:
            raise RuntimeError(f"Web search command not found: {argv[0]}")
        completed = subprocess.run(
            [executable, *argv[1:]],
            capture_output=True,
            check=True,
            text=True,
            timeout=45,
        )
        payload = json.loads(completed.stdout or "[]")
        return [self._result_from_item(item) for item in self._items_from_payload(payload)[:limit]]

    def _argv(self, query: str, limit: int) -> list[str]:
        if not self.command_template:
            return [self.command, query, "--limit", str(limit), "--json"]
        rendered = self.command_template.format(query=shlex.quote(query), limit=str(limit))
        return shlex.split(rendered)

    @staticmethod
    def _items_from_payload(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [item for item in payload if CommandWebSearchProvider._has_url(item)]
        if not isinstance(payload, dict):
            return []
        for key in ("items", "results", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if CommandWebSearchProvider._has_url(item)]
        return []

    @staticmethod
    def _has_url(item: object) -> bool:
        return isinstance(item, dict) and bool(item.get("url") or item.get("href") or item.get("link"))

    @staticmethod
    def _result_from_item(item: dict[str, Any]) -> WebSearchResult:
        url = str(item.get("url") or item.get("href") or item.get("link") or "")
        return WebSearchResult(
            title=str(item.get("title") or item.get("name") or url),
            url=url,
            snippet=str(item.get("snippet") or item.get("content") or item.get("summary") or ""),
        )


class MockWebSearchProvider:
    def search(self, query: str, limit: int = 3) -> list[WebSearchResult]:
        return [
            WebSearchResult(
                title="Mock web research result",
                url="https://example.invalid/research",
                snippet=f"Mock result for: {query}",
            )
        ][:limit]


class WebAcquisitionAgent(AcquisitionAgent):
    actor = "web_research_agent"

    def __init__(self, provider: WebSearchProvider):
        self.provider = provider

    def acquire(self, request: AcquisitionRequest) -> AcquisitionResult:
        results = self.provider.search(request.query)
        if not results:
            return AcquisitionResult(
                actor=self.actor,
                title="未找到 Web 资料",
                content="Web 检索没有返回可用结果。",
                sources=[],
                metadata={"provider": "web"},
            )
        content = "\n".join(f"{item.title}: {item.snippet}" for item in results)
        return AcquisitionResult(
            actor=self.actor,
            title="Web 检索结果",
            content=content,
            sources=[Source(title=item.title, source_type="web_page", reference=item.url) for item in results],
            metadata={"provider": "web"},
        )


def provider_from_env() -> WebSearchProvider | None:
    provider = os.getenv("AGENTMESH_WEB_PROVIDER", "").strip().lower()
    if provider == "mock":
        return MockWebSearchProvider()
    if provider == "opencli":
        return CommandWebSearchProvider(
            os.getenv("AGENTMESH_OPENCLI_COMMAND", "opencli"),
            os.getenv("AGENTMESH_OPENCLI_COMMAND_TEMPLATE") or os.getenv("AGENTMESH_WEB_COMMAND_TEMPLATE"),
        )
    if provider == "agent_browser":
        return CommandWebSearchProvider(
            os.getenv("AGENTMESH_AGENT_BROWSER_COMMAND", "agent-browser"),
            os.getenv("AGENTMESH_AGENT_BROWSER_COMMAND_TEMPLATE") or os.getenv("AGENTMESH_WEB_COMMAND_TEMPLATE"),
        )
    return None
