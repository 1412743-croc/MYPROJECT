import json
import logging

import httpx
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.models.risk import RiskLevel
from app.services.ai import (
    ChatTurn,
    FallbackAIProvider,
    MockProvider,
    OllamaProvider,
    OpenAICompatibleProvider,
    build_ai_provider,
)
from app.services.prompts import build_system_prompt

STUDENT_AUTH = ("student", "student123")


def test_default_provider_is_mock() -> None:
    provider = build_ai_provider(Settings())

    assert isinstance(provider, MockProvider)
    assert "谢谢你" in provider.generate("你好", RiskLevel.LOW, [])


def test_openai_provider_maps_request_and_response_without_network() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["authorization"] = request.headers["authorization"]
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "这是动态模型回复"}}]},
        )

    settings = Settings(
        ai_provider="openai",
        openai_base_url="https://api.example.test/v1",
        openai_api_key="secret-test-key",
        openai_model="test-chat-model",
    )
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        provider = OpenAICompatibleProvider(settings, client=client)
        reply = provider.generate(
            "我最近有些焦虑",
            RiskLevel.MEDIUM,
            [ChatTurn(role="assistant", content="你愿意多说一点吗？")],
        )

    body = captured["body"]
    assert reply == "这是动态模型回复"
    assert captured["url"] == "https://api.example.test/v1/chat/completions"
    assert captured["authorization"] == "Bearer secret-test-key"
    assert body["model"] == "test-chat-model"
    assert body["messages"][0]["role"] == "developer"
    assert body["messages"][-1] == {"role": "user", "content": "我最近有些焦虑"}


def test_openai_provider_parses_streaming_sse_without_network() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["stream"] is True
        return httpx.Response(
            200,
            text=(
                'data: {"choices":[{"delta":{"content":"逐段"}}]}\n\n'
                'data: {"choices":[{"delta":{"content":"回复"}}]}\n\n'
                "data: [DONE]\n\n"
            ),
            headers={"content-type": "text/event-stream"},
        )

    settings = Settings(
        ai_provider="openai",
        openai_base_url="https://api.example.test/v1",
        openai_api_key="secret-test-key",
        openai_model="test-chat-model",
    )
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        provider = OpenAICompatibleProvider(settings, client=client)
        chunks = list(provider.stream("你好", RiskLevel.LOW, []))

    assert chunks == ["逐段", "回复"]


def test_ollama_provider_maps_native_chat_request_without_network() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"message": {"content": "本地模型回复"}})

    settings = Settings(
        ai_provider="ollama",
        ollama_base_url="http://localhost:11434",
        ollama_model="local-test-model",
    )
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        reply = OllamaProvider(settings, client=client).generate("你好", RiskLevel.LOW, [])

    assert reply == "本地模型回复"
    assert captured["url"] == "http://localhost:11434/api/chat"
    assert captured["body"]["stream"] is False
    assert captured["body"]["messages"][0]["role"] == "system"


def test_ollama_provider_parses_streaming_ndjson_without_network() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["stream"] is True
        return httpx.Response(
            200,
            text=(
                '{"message":{"content":"本地"},"done":false}\n'
                '{"message":{"content":"流式"},"done":false}\n'
                '{"message":{"content":""},"done":true}\n'
            ),
        )

    settings = Settings(
        ai_provider="ollama",
        ollama_base_url="http://localhost:11434",
        ollama_model="local-test-model",
    )
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        chunks = list(OllamaProvider(settings, client=client).stream("你好", RiskLevel.LOW, []))

    assert chunks == ["本地", "流式"]


def test_mock_provider_stream_reassembles_complete_reply() -> None:
    provider = MockProvider()

    complete = provider.generate("最近压力很大", RiskLevel.MEDIUM, [])
    chunks = list(provider.stream("最近压力很大", RiskLevel.MEDIUM, []))

    assert len(chunks) > 1
    assert "".join(chunks) == complete


def test_missing_openai_key_falls_back_to_mock(caplog) -> None:
    caplog.set_level(logging.WARNING)
    settings = Settings(ai_provider="openai", openai_api_key="", openai_model="test-model")

    provider = build_ai_provider(settings)

    assert isinstance(provider, MockProvider)
    assert "回退" in caplog.text


def test_provider_failure_falls_back_without_logging_key(caplog) -> None:
    caplog.set_level(logging.WARNING)

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "unavailable"})

    secret_key = "must-not-appear-in-logs"
    settings = Settings(
        ai_provider="openai",
        openai_base_url="https://api.example.test/v1",
        openai_api_key=secret_key,
        openai_model="test-model",
    )
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        provider = FallbackAIProvider(
            OpenAICompatibleProvider(settings, client=client),
            MockProvider(),
        )
        reply = provider.generate("最近压力很大", RiskLevel.MEDIUM, [])

    assert "压力" in reply
    assert "fallback" in caplog.text.lower()
    assert secret_key not in caplog.text


def test_high_risk_prompt_prioritizes_immediate_safety() -> None:
    prompt = build_system_prompt(RiskLevel.HIGH)

    assert "当地紧急服务" in prompt
    assert "可信赖的人" in prompt
    assert "不得虚构电话号码" in prompt


def test_ai_status_never_exposes_api_key(client: TestClient) -> None:
    response = client.get("/api/ai/status", auth=STUDENT_AUTH)

    assert response.status_code == 200
    assert response.json()["effective_provider"] == "mock"
    assert "key" not in response.text.casefold()
