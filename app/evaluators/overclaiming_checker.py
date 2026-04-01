"""LLM-as-judge: check for causal overclaiming in model output."""
from __future__ import annotations

import json

from app.clients.openai_client import OpenAIClient
from app.models.document import Document
from app.prompts.overclaiming_check import (
    OVERCLAIMING_CHECK_SYSTEM,
    OVERCLAIMING_CHECK_USER_TEMPLATE,
)
from app.schemas.evaluation import CheckResult
from app.utils.logging_setup import get_logger
from app.utils.text_utils import truncate_to_tokens

logger = get_logger(__name__)


class OverclaimingChecker:
    """Detect when correlation is presented as causation or weak evidence as definitive."""

    def __init__(self) -> None:
        self.openai = OpenAIClient()

    async def check(self, doc: Document, answer: str) -> CheckResult:
        if not answer or len(answer.strip()) < 30:
            return CheckResult(
                category="overclaiming",
                pass_fail=None,
                score=None,
                details={"reason": "skipped_no_answer"},
                evaluator_type="llm",
            )

        prompt = OVERCLAIMING_CHECK_USER_TEMPLATE.format(
            answer=truncate_to_tokens(answer, 600),
            title=doc.title or "Medical Study",
        )

        try:
            response = await self.openai.complete(
                prompt, system=OVERCLAIMING_CHECK_SYSTEM
            )
            result = self._parse_response(response)
        except Exception as exc:
            logger.error(f"event=overclaiming_llm_error doc_id={doc.id} err={exc!r}")
            return CheckResult(
                category="overclaiming",
                pass_fail=None,
                score=None,
                details={"reason": "llm_unavailable", "error": str(exc)},
                evaluator_type="llm",
            )

        flagged = result.get("overclaiming_instances", [])
        count = len(flagged)
        score = max(0.0, 1.0 - count * 0.3)
        pass_fail = count == 0

        logger.info(
            f"event=overclaiming_check doc_id={doc.id} flagged={count} score={score:.2f}"
        )
        return CheckResult(
            category="overclaiming",
            pass_fail=pass_fail,
            score=round(score, 3),
            details={"overclaiming_instances": flagged, "total_flagged": count},
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
            # Count lines starting with "-" as instances
            lines = [
                ln.strip() for ln in response.split("\n") if ln.strip().startswith("-")
            ]
            overclaiming = [ln for ln in lines if any(
                w in ln.lower() for w in ["causes", "proves", "definitive", "certain"]
            )]
            return {
                "overclaiming_instances": overclaiming[:5],
                "raw": response[:200],
            }
