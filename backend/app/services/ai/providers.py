"""Implementaciones concretas de proveedores de IA.

Las llamadas salientes están restringidas a los hosts del proveedor
configurado: nunca se descarga una URL proporcionada por el usuario.
"""

from __future__ import annotations

import httpx

from app.core.config import settings
from app.core.errors import AiProviderError
from app.core.logging import get_logger
from app.services.ai.base import AiProvider, NullProvider

logger = get_logger(__name__)

#: Modelos por defecto si el entorno no especifica uno.
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-5"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_OLLAMA_MODEL = "llama3.1"

_ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
_OPENAI_URL = "https://api.openai.com/v1/chat/completions"


class AnthropicProvider(AiProvider):
    name = "anthropic"

    def __init__(
        self, api_key: str, model: str | None = None, timeout: float | None = None
    ) -> None:
        self.api_key = api_key
        self.model = model or DEFAULT_ANTHROPIC_MODEL
        self.timeout = timeout or settings.ai_request_timeout_seconds
        self._client = httpx.Client(timeout=self.timeout)

    def complete_json(self, system_prompt: str, user_prompt: str) -> str:
        try:
            response = self._client.post(
                _ANTHROPIC_URL,
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": self.model,
                    "max_tokens": 1500,
                    "temperature": 0.2,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": user_prompt}],
                },
            )
        except httpx.HTTPError as exc:
            raise AiProviderError(detail=f"anthropic: {exc}") from exc

        if response.status_code != 200:
            raise AiProviderError(detail=f"anthropic HTTP {response.status_code}")

        payload = response.json()
        blocks = payload.get("content") or []
        texts = [
            b.get("text", "") for b in blocks if isinstance(b, dict) and b.get("type") == "text"
        ]
        return "".join(texts)

    def close(self) -> None:
        self._client.close()


class OpenAiProvider(AiProvider):
    name = "openai"

    def __init__(
        self, api_key: str, model: str | None = None, timeout: float | None = None
    ) -> None:
        self.api_key = api_key
        self.model = model or DEFAULT_OPENAI_MODEL
        self.timeout = timeout or settings.ai_request_timeout_seconds
        self._client = httpx.Client(timeout=self.timeout)

    def complete_json(self, system_prompt: str, user_prompt: str) -> str:
        try:
            response = self._client.post(
                _OPENAI_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "temperature": 0.2,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                },
            )
        except httpx.HTTPError as exc:
            raise AiProviderError(detail=f"openai: {exc}") from exc

        if response.status_code != 200:
            raise AiProviderError(detail=f"openai HTTP {response.status_code}")

        payload = response.json()
        choices = payload.get("choices") or []
        if not choices:
            raise AiProviderError(detail="openai: respuesta sin choices")
        return str((choices[0].get("message") or {}).get("content") or "")

    def close(self) -> None:
        self._client.close()


class OllamaProvider(AiProvider):
    """Proveedor local. Permite usar IA sin ninguna API de pago."""

    name = "ollama"

    def __init__(
        self, base_url: str, model: str | None = None, timeout: float | None = None
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model or DEFAULT_OLLAMA_MODEL
        self.timeout = timeout or settings.ai_request_timeout_seconds
        self._client = httpx.Client(timeout=self.timeout)

    def complete_json(self, system_prompt: str, user_prompt: str) -> str:
        try:
            response = self._client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0.2},
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                },
            )
        except httpx.HTTPError as exc:
            raise AiProviderError(detail=f"ollama: {exc}") from exc

        if response.status_code != 200:
            raise AiProviderError(detail=f"ollama HTTP {response.status_code}")

        payload = response.json()
        return str((payload.get("message") or {}).get("content") or "")

    def close(self) -> None:
        self._client.close()


def build_provider() -> AiProvider:
    """Crea el proveedor configurado. Devuelve `NullProvider` si no hay ninguno."""
    if not settings.ai_enabled:
        return NullProvider()

    provider = settings.ai_provider
    try:
        if provider == "anthropic":
            return AnthropicProvider(settings.anthropic_api_key, settings.anthropic_model or None)
        if provider == "openai":
            return OpenAiProvider(settings.openai_api_key, settings.openai_model or None)
        if provider == "ollama":
            return OllamaProvider(settings.ollama_base_url, settings.ollama_model or None)
    except Exception as exc:  # pragma: no cover - defensivo
        logger.warning("ai_provider_build_failed", provider=provider, error=str(exc))
    return NullProvider()


__all__ = [
    "DEFAULT_ANTHROPIC_MODEL",
    "DEFAULT_OLLAMA_MODEL",
    "DEFAULT_OPENAI_MODEL",
    "AnthropicProvider",
    "OllamaProvider",
    "OpenAiProvider",
    "build_provider",
]
