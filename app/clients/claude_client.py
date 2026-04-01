"""Async Anthropic Claude client."""
from __future__ import annotations

import json
from typing import Any, Optional

from app.config import get_config
from app.utils.logging_setup import get_logger

logger = get_logger(__name__)


class ClaudeClient:
    def __init__(self) -> None:
        self.cfg = get_config()
        model_cfg = self.cfg.models.get("claude", {})
        self.model = model_cfg.get("model", "claude-opus-4-5")
        self.max_tokens = model_cfg.get("max_tokens", 2048)
        self.temperature = model_cfg.get("temperature", 0.1)
        self.api_key = model_cfg.get("api_key", "")

    def _get_client(self):
        import anthropic
        return anthropic.AsyncAnthropic(api_key=self.api_key)

    async def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Send a prompt to Claude and return the text response."""
        client = self._get_client()
        messages = [{"role": "user", "content": prompt}]
        kwargs: dict = {
            "model": self.model,
            "max_tokens": max_tokens or self.max_tokens,
            "messages": messages,
        }
        if system:
            kwargs["system"] = system

        try:
            response = await client.messages.create(**kwargs)
            text = response.content[0].text
            logger.info(
                f"event=claude_complete model={self.model} "
                f"in_tokens={response.usage.input_tokens} "
                f"out_tokens={response.usage.output_tokens}"
            )
            return text
        except Exception as exc:
            logger.error(f"event=claude_error err={exc!r}")
            raise

    async def extract_structured(
        self,
        prompt: str,
        schema_description: str,
    ) -> Any:
        """Complete a prompt and attempt to parse JSON from the response."""
        system = (
            f"You extract structured data. Return valid JSON matching: {schema_description}. "
            "Return ONLY the JSON object, no prose."
        )
        text = await self.complete(prompt, system=system)
        # Extract JSON block if wrapped in markdown
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            text = text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            text = text[start:end].strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            logger.warning("event=claude_json_parse_fail returning raw text")
            return text
