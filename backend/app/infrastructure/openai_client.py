"""
OpenAI Client
=============
Async client wrapper for OpenAI Chat Completions with streaming support.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from openai import APIConnectionError, APITimeoutError, AsyncOpenAI, OpenAIError

from app.core.config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL, OPENAI_TIMEOUT


class OpenAIClientError(Exception):
    """Raised when OpenAI API calls fail or are misconfigured."""


class OpenAIClient:
    def __init__(
        self,
        *,
        api_key: str = OPENAI_API_KEY,
        base_url: str = OPENAI_BASE_URL,
        model: str = OPENAI_MODEL,
        timeout: int = OPENAI_TIMEOUT,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self._client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
        )

    async def ping(self) -> bool:
        """Return True if API key works and models endpoint is reachable."""
        if not self.api_key:
            return False
        try:
            await self._client.models.list()
            return True
        except Exception:
            return False

    async def list_models(self) -> list[str]:
        if not self.api_key:
            raise OpenAIClientError("OPENAI_API_KEY is not configured.")
        try:
            models = await self._client.models.list()
            return sorted(m.id for m in models.data)
        except APITimeoutError:
            raise OpenAIClientError(
                f"OpenAI API timed out after {self.timeout}s."
            )
        except APIConnectionError:
            raise OpenAIClientError(
                f"Cannot connect to OpenAI API at {self.base_url}."
            )
        except OpenAIError as exc:
            raise OpenAIClientError(str(exc))

    async def generate(
        self,
        *,
        prompt: str,
        system: str | None = None,
        model: str | None = None,
        temperature: float = 0.3,
        json_mode: bool = False,
    ) -> str:
        if not self.api_key:
            raise OpenAIClientError("OPENAI_API_KEY is not configured.")

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        request_kwargs = {
            "model": model or self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if json_mode:
            request_kwargs["response_format"] = {"type": "json_object"}

        try:
            resp = await self._client.chat.completions.create(**request_kwargs)
        except OpenAIError as exc:
            if json_mode and "response_format" in str(exc).lower():
                fallback_kwargs = dict(request_kwargs)
                fallback_kwargs.pop("response_format", None)
                resp = await self._client.chat.completions.create(**fallback_kwargs)
            else:
                raise OpenAIClientError(str(exc))
        except APITimeoutError:
            raise OpenAIClientError(
                f"OpenAI request timed out after {self.timeout}s."
            )
        except APIConnectionError:
            raise OpenAIClientError(
                f"Cannot connect to OpenAI API at {self.base_url}."
            )

        text = resp.choices[0].message.content or ""
        return text.strip()

    async def generate_stream(
        self,
        *,
        prompt: str,
        system: str | None = None,
        model: str | None = None,
        temperature: float = 0.3,
        json_mode: bool = False,
    ) -> AsyncGenerator[str, None]:
        if not self.api_key:
            raise OpenAIClientError("OPENAI_API_KEY is not configured.")

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        request_kwargs = {
            "model": model or self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }
        if json_mode:
            request_kwargs["response_format"] = {"type": "json_object"}

        try:
            stream = await self._client.chat.completions.create(**request_kwargs)
        except OpenAIError as exc:
            if json_mode and "response_format" in str(exc).lower():
                fallback_kwargs = dict(request_kwargs)
                fallback_kwargs.pop("response_format", None)
                stream = await self._client.chat.completions.create(**fallback_kwargs)
            else:
                raise OpenAIClientError(str(exc))
        try:
            async for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                token = delta.content or ""
                if token:
                    yield token
        except APITimeoutError:
            raise OpenAIClientError(
                f"OpenAI stream timed out after {self.timeout}s."
            )
        except APIConnectionError:
            raise OpenAIClientError(
                f"Cannot connect to OpenAI API at {self.base_url}."
            )
        except OpenAIError as exc:
            raise OpenAIClientError(str(exc))
