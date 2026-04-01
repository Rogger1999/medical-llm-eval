"""Async OpenAI client for completion and evaluation tasks."""
from __future__ import annotations

from typing import Optional

from app.config import get_config
from app.utils.logging_setup import get_logger

logger = get_logger(__name__)


class OpenAIClient:
    def __init__(self) -> None:
        self.cfg = get_config()
        model_cfg = self.cfg.models.get("openai", {})
        self.model = model_cfg.get("model", "gpt-4o-mini")
        self.max_tokens = model_cfg.get("max_tokens", 1024)
        self.temperature = model_cfg.get("temperature", 0.1)
        self.api_key = model_cfg.get("api_key", "")

    def _get_client(self):
        from openai import AsyncOpenAI
        return AsyncOpenAI(api_key=self.api_key)

    async def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Send prompt to OpenAI chat completion and return text."""
        client = self._get_client()
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        try:
            response = await client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens or self.max_tokens,
                temperature=self.temperature,
            )
            text = response.choices[0].message.content or ""
            logger.info(
                f"event=openai_complete model={self.model} "
                f"in_tokens={response.usage.prompt_tokens} "
                f"out_tokens={response.usage.completion_tokens}"
            )
            return text
        except Exception as exc:
            logger.error(f"event=openai_error err={exc!r}")
            raise

    async def evaluate(
        self,
        primary_output: str,
        question: str,
        context: str,
    ) -> str:
        """Ask OpenAI to evaluate an answer against source context."""
        system = (
            "You are a medical literature evaluator. "
            "Assess whether the answer is well-supported by the provided context. "
            "Return a brief JSON with keys: grounded (bool), issues (list of strings)."
        )
        prompt = (
            f"Question: {question}\n\n"
            f"Answer:\n{primary_output}\n\n"
            f"Source context:\n{context}\n\n"
            "Is the answer grounded in the context? List any unsupported claims."
        )
        return await self.complete(prompt, system=system)

    async def judge(
        self,
        instruction: str,
        content: str,
        system: Optional[str] = None,
    ) -> str:
        """Generic LLM-as-judge call."""
        prompt = f"{instruction}\n\nContent to evaluate:\n{content}"
        judge_system = system or "You are an expert medical evaluator providing objective assessments."
        return await self.complete(prompt, system=judge_system)
