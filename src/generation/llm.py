"""Ollama client wrapper: blocking `.generate()` + async streaming `.stream()`.

Streaming surfaces tokens to the UI as they arrive, cutting perceived latency
from "full 30-60s wait" to "first token in ~1s".

GPU tuning:
  * num_gpu = -1  -> offload all transformer layers to GPU
  * keep_alive    -> prevent Ollama from unloading the model between requests
"""

from __future__ import annotations

from typing import Any, AsyncIterator

from src.config import get_settings
from src.generation.prompts import SYSTEM_PROMPT, build_prompt
from src.utils.logger import get_logger

logger = get_logger(__name__)


class OllamaLLM:
    """Wrap the ollama Python client for chat-style generation."""

    def __init__(
        self,
        model: str | None = None,
        host: str | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
        max_tokens: int | None = None,
        keep_alive: str | None = None,
        num_gpu: int | None = None,
    ) -> None:
        settings = get_settings()
        self.model = model or settings.ollama_model
        self.host = host or settings.ollama_url
        self.temperature = temperature if temperature is not None else settings.llm_temperature
        self.top_p = top_p if top_p is not None else settings.llm_top_p
        self.max_tokens = max_tokens or settings.llm_max_tokens
        self.keep_alive = keep_alive or getattr(settings, "ollama_keep_alive", "30m")
        self.num_gpu = num_gpu if num_gpu is not None else getattr(settings, "ollama_num_gpu", -1)
        self._client = None
        self._async_client = None

    def _ensure_client(self) -> Any:
        if self._client is None:
            import ollama

            self._client = ollama.Client(host=self.host)
        return self._client

    def _ensure_async_client(self) -> Any:
        if self._async_client is None:
            import ollama

            self._async_client = ollama.AsyncClient(host=self.host)
        return self._async_client

    def _build_messages(
        self,
        question: str,
        context: str | list[dict[str, Any]],
    ) -> list[dict[str, str]]:
        if isinstance(context, list):
            prompt = build_prompt(question, context)
        else:
            prompt = build_prompt(question, [{"text": context, "metadata": {}}])
        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

    def _options(self) -> dict[str, Any]:
        return {
            "temperature": self.temperature,
            "top_p": self.top_p,
            "num_predict": self.max_tokens,
            "num_gpu": self.num_gpu,  # -1 means "all layers" for Ollama
            "num_ctx": 4096,          # RAG prompts are ~3K chars; 4K context is plenty
        }

    @staticmethod
    def _as_stream_part_dict(part: Any) -> dict[str, Any]:
        if isinstance(part, dict):
            return part
        model_dump = getattr(part, "model_dump", None)
        if callable(model_dump):
            return model_dump()
        as_dict = getattr(part, "dict", None)
        if callable(as_dict):
            return as_dict()
        return {}

    @staticmethod
    def _chat_stream_delta(part: dict[str, Any]) -> str:
        """Extract text delta from one streamed chat chunk (Ollama versions differ)."""
        msg = part.get("message")
        if isinstance(msg, dict):
            chunk = msg.get("content") or ""
            if chunk:
                return chunk
        if isinstance(msg, str) and msg:
            return msg
        # Legacy/alternate shapes
        if isinstance(part.get("content"), str):
            return part["content"]
        alt = part.get("response")
        return alt if isinstance(alt, str) else ""

    def generate(self, question: str, context: str | list[dict[str, Any]]) -> str:
        """Blocking generation. Prefer `stream()` in interactive UIs."""
        client = self._ensure_client()
        response = client.chat(
            model=self.model,
            messages=self._build_messages(question, context),
            options=self._options(),
            keep_alive=self.keep_alive,
        )
        return response["message"]["content"].strip()

    async def stream(
        self,
        question: str,
        context: str | list[dict[str, Any]],
    ) -> AsyncIterator[str]:
        """Async token stream. Yields text deltas as they are produced."""
        client = self._ensure_async_client()
        async for part in await client.chat(
            model=self.model,
            messages=self._build_messages(question, context),
            options=self._options(),
            keep_alive=self.keep_alive,
            stream=True,
        ):
            chunk = self._chat_stream_delta(self._as_stream_part_dict(part))
            if chunk:
                yield chunk
