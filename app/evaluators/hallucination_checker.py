"""LLM-as-judge: detect hallucinated facts in model output."""
from __future__ import annotations

import json

from app.clients.openai_client import OpenAIClient
from app.models.document import Document
from app.prompts.hallucination_check import (
    HALLUCINATION_CHECK_SYSTEM,
    HALLUCINATION_CHECK_USER_TEMPLATE,
)
from app.schemas.evaluation import CheckResult
from app.services.storage import load_parsed_text
from app.utils.logging_setup import get_logger
from app.utils.text_utils import truncate_to_tokens

logger = get_logger(__name__)


class HallucinationChecker:
    """Detect invented facts, statistics, or claims not in source text."""

    def __init__(self) -> None:
        self.openai = OpenAIClient()

    async def check(self, doc: Document, answer: str) -> CheckResult:
        if not answer or len(answer.strip()) < 20:
            return CheckResult(
                category="hallucination",
                pass_fail=None,
                score=None,
                details={"reason": "skipped_no_answer"},
                evaluator_type="llm",
            )

        source = load_parsed_text(doc.id) or doc.abstract or ""
        source = truncate_to_tokens(source, 1500)

        prompt = HALLUCINATION_CHECK_USER_TEMPLATE.format(
            answer=truncate_to_tokens(answer, 600),
            source=source,
        )

        try:
            response = await self.openai.complete(
                prompt, system=HALLUCINATION_CHECK_SYSTEM
            )
            result = self._parse_response(response)
        except Exception as exc:
            logger.error(
                f"event=hallucination_llm_error doc_id={doc.id} err={exc!r}"
            )
            return CheckResult(
                category="hallucination",
                pass_fail=None,
                score=None,
                details={"reason": "llm_unavailable", "error": str(exc)},
                evaluator_type="llm",
            )

        flagged = result.get("flagged_claims", [])
        hallucination_count = len(flagged)
        score = max(0.0, 1.0 - hallucination_count * 0.25)
        pass_fail = hallucination_count == 0

        logger.info(
            f"event=hallucination_check doc_id={doc.id} "
            f"flagged={hallucination_count} score={score:.2f}"
        )
        return CheckResult(
            category="hallucination",
            pass_fail=pass_fail,
            score=round(score, 3),
            details={"flagged_claims": flagged, "total_flagged": hallucination_count},
            evaluator_type="llm",
        )

    def _parse_response(self, response: str) -> dict:
        try:
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                response = response[start:end].strip()
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                response = response[start:end].strip()
            return json.loads(response)
        except json.JSONDecodeError:
            # Heuristic: count lines that look like flagged claims
            lines = [ln.strip() for ln in response.split("\n") if ln.strip().startswith("-")]
            return {"flagged_claims": lines[:5], "raw": response[:200]}
