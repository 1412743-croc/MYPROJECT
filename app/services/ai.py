"""Configurable AI providers with deterministic fallback behavior."""

import logging
from dataclasses import dataclass
from typing import Any, Protocol, Sequence

import httpx

from app.core.config import Settings
from app.models.risk import RiskLevel
from app.services.mock_ai import MockProvider
from app.services.prompts import build_system_prompt

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ChatTurn:
    role: str
    content: str


class AIProvider(Protocol):
    name: str

    def generate(
        self,
        message: str,
        risk_level: RiskLevel,
        history: Sequence[ChatTurn],
    ) -> str: ...


class AIProviderError(RuntimeError):
    pass


class OpenAICompatibleProvider:
    name = "openai"

    def __init__(self, settings: Settings, client: httpx.Client | None = None) -> None:
        self.base_url = settings.openai_base_url.rstrip("/")
        self.api_key = settings.openai_api_key.get_secret_value()
        self.model = settings.openai_model
        self.temperature = settings.ai_temperature
        self.timeout = settings.ai_timeout_seconds
        self.client = client

    def generate(
        self,
        message: str,
        risk_level: RiskLevel,
        history: Sequence[ChatTurn],
    ) -> str:
        messages = [
            {"role": "developer", "content": build_system_prompt(risk_level)},
            *({"role": turn.role, "content": turn.content} for turn in history),
            {"role": "user", "content": message},
        ]
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            data = self._post("/chat/completions", payload, headers)
            content = data["choices"][0]["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                raise ValueError("empty model response")
            return content.strip()
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            raise AIProviderError(f"openai request failed: {type(exc).__name__}") from exc

    def _post(
        self,
        path: str,
        payload: dict[str, Any],
        headers: dict[str, str],
    ) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        if self.client is not None:
            response = self.client.post(url, json=payload, headers=headers, timeout=self.timeout)
        else:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()


class OllamaProvider:
    name = "ollama"

    def __init__(self, settings: Settings, client: httpx.Client | None = None) -> None:
        self.base_url = settings.ollama_base_url.rstrip("/")
        self.model = settings.ollama_model
        self.temperature = settings.ai_temperature
        self.timeout = settings.ai_timeout_seconds
        self.client = client

    def generate(
        self,
        message: str,
        risk_level: RiskLevel,
        history: Sequence[ChatTurn],
    ) -> str:
        messages = [
            {"role": "system", "content": build_system_prompt(risk_level)},
            *({"role": turn.role, "content": turn.content} for turn in history),
            {"role": "user", "content": message},
        ]
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": self.temperature},
        }
        try:
            data = self._post(payload)
            content = data["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                raise ValueError("empty model response")
            return content.strip()
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            raise AIProviderError(f"ollama request failed: {type(exc).__name__}") from exc

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}/api/chat"
        if self.client is not None:
            response = self.client.post(url, json=payload, timeout=self.timeout)
        else:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(url, json=payload)
        response.raise_for_status()
        return response.json()


class FallbackAIProvider:
    name = "fallback"

    def __init__(self, primary: AIProvider, fallback: AIProvider) -> None:
        self.primary = primary
        self.fallback = fallback

    def generate(
        self,
        message: str,
        risk_level: RiskLevel,
        history: Sequence[ChatTurn],
    ) -> str:
        try:
            return self.primary.generate(message, risk_level, history)
        except AIProviderError as exc:
            logger.warning(
                "AI provider '%s' failed (%s); fallback to '%s'",
                self.primary.name,
                type(exc.__cause__).__name__ if exc.__cause__ else type(exc).__name__,
                self.fallback.name,
            )
            return self.fallback.generate(message, risk_level, history)


def build_ai_provider(
    settings: Settings,
    client: httpx.Client | None = None,
) -> AIProvider:
    provider_name = settings.ai_provider.strip().lower()
    fallback = MockProvider()

    if provider_name == "mock":
        return fallback
    if provider_name == "openai":
        if not settings.openai_api_key.get_secret_value() or not settings.openai_model:
            logger.warning("OpenAI configuration is incomplete; 回退 to MockProvider")
            return fallback
        return FallbackAIProvider(OpenAICompatibleProvider(settings, client), fallback)
    if provider_name == "ollama":
        if not settings.ollama_model:
            logger.warning("Ollama model is not configured; 回退 to MockProvider")
            return fallback
        return FallbackAIProvider(OllamaProvider(settings, client), fallback)

    logger.warning("Unknown AI provider '%s'; 回退 to MockProvider", provider_name)
    return fallback


def provider_status(settings: Settings) -> dict[str, str | bool]:
    configured = settings.ai_provider.strip().lower()
    effective = configured
    model = ""
    fallback_reason = ""

    if configured == "openai":
        model = settings.openai_model
        if not settings.openai_api_key.get_secret_value() or not model:
            effective = "mock"
            fallback_reason = "OpenAI configuration is incomplete"
    elif configured == "ollama":
        model = settings.ollama_model
        if not model:
            effective = "mock"
            fallback_reason = "Ollama model is not configured"
    elif configured != "mock":
        effective = "mock"
        fallback_reason = "Unknown AI provider"

    return {
        "configured_provider": configured,
        "effective_provider": effective,
        "model": model if effective != "mock" else "mock",
        "fallback_enabled": configured in {"openai", "ollama"},
        "fallback_reason": fallback_reason,
    }
