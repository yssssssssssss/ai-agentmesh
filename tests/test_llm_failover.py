from __future__ import annotations

from dataclasses import dataclass

import pytest

from agentmesh.llm import LLMClient, LLMRequestError
from agentmesh.seed import USER
from agentmesh.store import store
from agentmesh.synthesis import FailoverChatLLM, chat_llm_client


@dataclass
class StubLLM:
    model: str
    result: str | None = None
    error: LLMRequestError | None = None
    calls: int = 0

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.result or ""


def install_model_factory(monkeypatch: pytest.MonkeyPatch, clients: dict[str, StubLLM]) -> None:
    monkeypatch.setattr(
        LLMClient,
        "from_model_id",
        classmethod(lambda cls, model_id, *, timeout_seconds=None: clients.get(str(model_id))),
    )


def test_primary_success_does_not_call_fallback() -> None:
    primary = StubLLM("primary-model", result="primary answer")
    fallback = StubLLM("fallback-model", result="fallback answer")
    client = FailoverChatLLM(primary, fallback)

    assert client.complete("system", "user") == "primary answer"
    assert primary.calls == 1
    assert fallback.calls == 0
    assert client.requested_model == "primary-model"
    assert client.actual_model == "primary-model"
    assert client.fallback_reason is None


@pytest.mark.parametrize("reason", ["timeout", "request_error", "http_status", "invalid_response"])
def test_eligible_primary_errors_call_fallback_once(reason: str) -> None:
    primary = StubLLM("primary-model", error=LLMRequestError(reason, "redacted"))
    fallback = StubLLM("fallback-model", result="fallback answer")
    client = FailoverChatLLM(primary, fallback)

    assert client.complete("system", "user") == "fallback answer"
    assert primary.calls == 1
    assert fallback.calls == 1
    assert client.actual_model == "fallback-model"
    assert client.fallback_reason == reason


def test_empty_primary_response_calls_fallback_once() -> None:
    primary = StubLLM("primary-model", result="   ")
    fallback = StubLLM("fallback-model", result="fallback answer")
    client = FailoverChatLLM(primary, fallback)

    assert client.complete("system", "user") == "fallback answer"
    assert primary.calls == 1
    assert fallback.calls == 1
    assert client.actual_model == "fallback-model"
    assert client.fallback_reason == "empty_response"


def test_auth_error_does_not_call_fallback() -> None:
    primary = StubLLM("primary-model", error=LLMRequestError("auth_error", "redacted"))
    fallback = StubLLM("fallback-model", result="fallback answer")
    client = FailoverChatLLM(primary, fallback)

    with pytest.raises(LLMRequestError, match="redacted"):
        client.complete("system", "user")
    assert primary.calls == 1
    assert fallback.calls == 0


def test_double_failure_has_stable_redacted_reason() -> None:
    primary = StubLLM("primary-model", error=LLMRequestError("timeout", "primary body secret"))
    fallback = StubLLM("fallback-model", error=LLMRequestError("request_error", "fallback body secret"))
    client = FailoverChatLLM(primary, fallback)

    with pytest.raises(LLMRequestError) as captured:
        client.complete("system", "user")
    assert captured.value.reason == "primary_timeout_fallback_request_error"
    assert "secret" not in str(captured.value)


def test_chat_client_wraps_selected_model_with_configured_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    primary = StubLLM("primary-model", result="primary answer")
    fallback = StubLLM("fallback-model", result="fallback answer")
    install_model_factory(monkeypatch, {"primary": primary, "fallback": fallback})
    monkeypatch.setattr("agentmesh.synthesis.resolve_agent_model_id", lambda repository, user: "primary")
    monkeypatch.setenv("AGENTMESH_LLM_FALLBACK_MODEL_ID", "fallback")

    client = chat_llm_client(store, USER)

    assert isinstance(client, FailoverChatLLM)
    assert client.primary is primary
    assert client.fallback is fallback


def test_injected_client_bypasses_environment_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    injected = StubLLM("injected", result="ok")
    monkeypatch.setenv("AGENTMESH_LLM_FALLBACK_MODEL_ID", "fallback")

    assert chat_llm_client(store, USER, injected) is injected


def test_explicit_fallback_selection_does_not_wrap_itself(monkeypatch: pytest.MonkeyPatch) -> None:
    fallback = StubLLM("fallback-model", result="fallback answer")
    install_model_factory(monkeypatch, {"fallback": fallback})
    monkeypatch.setattr("agentmesh.synthesis.resolve_agent_model_id", lambda repository, user: "fallback")
    monkeypatch.setenv("AGENTMESH_LLM_FALLBACK_MODEL_ID", "fallback")

    client = chat_llm_client(store, USER)

    assert client is fallback
    assert not isinstance(client, FailoverChatLLM)


def test_unconfigured_fallback_keeps_primary_client(monkeypatch: pytest.MonkeyPatch) -> None:
    primary = StubLLM("primary-model", result="primary answer")
    install_model_factory(monkeypatch, {"primary": primary})
    monkeypatch.setattr("agentmesh.synthesis.resolve_agent_model_id", lambda repository, user: "primary")
    monkeypatch.setenv("AGENTMESH_LLM_FALLBACK_MODEL_ID", "fallback")

    client = chat_llm_client(store, USER)

    assert client is primary
