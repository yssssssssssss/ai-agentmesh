import pytest

from agentmesh.acquisition import AcquisitionRequest
from agentmesh.models import Intent
from agentmesh.seed import PROJECT, WORKSPACE
from agentmesh.web_research import (
    CommandWebSearchProvider,
    MockWebSearchProvider,
    WebAcquisitionAgent,
    provider_from_env,
)


def test_mock_web_search_provider_returns_contract() -> None:
    results = MockWebSearchProvider().search("618 家电会场")

    assert results[0].title == "Mock web research result"
    assert results[0].url.startswith("https://")


def test_missing_command_provider_fails_explicitly() -> None:
    provider = CommandWebSearchProvider("agentmesh-command-that-does-not-exist")

    with pytest.raises(RuntimeError, match="Web search command not found"):
        provider.search("query")


def test_command_provider_uses_template_and_results_payload(tmp_path) -> None:
    command = tmp_path / "fake_search.py"
    command.write_text(
        "\n".join(
            [
                "#!/usr/bin/env python3",
                "import json",
                "import sys",
                "print(json.dumps({'results': [{'name': sys.argv[1], 'href': 'https://example.invalid/a', 'summary': sys.argv[2]}]}))",
            ]
        ),
        encoding="utf-8",
    )
    command.chmod(0o755)

    provider = CommandWebSearchProvider(str(command), command_template=f"{command} {{query}} {{limit}}")

    results = provider.search("618 家电", limit=2)

    assert results[0].title == "618 家电"
    assert results[0].url == "https://example.invalid/a"
    assert results[0].snippet == "2"


def test_provider_from_env_supports_provider_specific_template(monkeypatch) -> None:
    monkeypatch.setenv("AGENTMESH_WEB_PROVIDER", "opencli")
    monkeypatch.setenv("AGENTMESH_OPENCLI_COMMAND", "opencli")
    monkeypatch.setenv("AGENTMESH_OPENCLI_COMMAND_TEMPLATE", "opencli search {query} --count {limit} --json")

    provider = provider_from_env()

    assert isinstance(provider, CommandWebSearchProvider)
    assert provider.command_template == "opencli search {query} --count {limit} --json"


def test_web_acquisition_agent_converts_results_to_evidence() -> None:
    agent = WebAcquisitionAgent(MockWebSearchProvider())

    result = agent.acquire(
        AcquisitionRequest(
            query="618 家电会场",
            intent=Intent.REQUEST_EXTERNAL_RESEARCH,
            workspace_id=WORKSPACE.id,
            project_id=PROJECT.id,
            user_id="usr",
            task_id="task_web",
            request_post_id="bb_web",
        )
    )

    assert result.actor == "web_research_agent"
    assert result.title == "Web 检索结果"
    assert result.sources[0].source_type == "web_page"
    assert "Mock result" in result.content
