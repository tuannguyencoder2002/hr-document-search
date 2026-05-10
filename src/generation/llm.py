"""Thin Ollama client wrapper for the RAG generation step."""

from __future__ import annotations

from typing import Any

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
    ) -> None:
        settings = get_settings()
        self.model = model or settings.ollama_model
        self.host = host or settings.ollama_url
        self.temperature = temperature if temperature is not None else settings.llm_temperature
        self.top_p = top_p if top_p is not None else settings.llm_top_p
        self.max_tokens = max_tokens or settings.llm_max_tokens
        self._client = None

    def _ensure_client(self) -> Any:
        if self._client is None:
            import ollama

            self._client = ollama.Client(host=self.host)
        return self._client

    def generate(self, question: str, context: str | list[dict[str, Any]]) -> str:
        """Generate an answer given a question and either a context string or chunk list."""
        if isinstance(context, list):
            prompt = build_prompt(question, context)
        else:
            prompt = build_prompt(question, [{"text": context, "metadata": {}}])

        client = self._ensure_client()
        response = client.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            options={
                "temperature": self.temperature,
                "top_p": self.top_p,
                "num_predict": self.max_tokens,
            },
        )
        return response["message"]["content"].strip()
