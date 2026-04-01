"""Rule + LLM hybrid: verify numeric values in answer match source."""
from __future__ import annotations

import re
from typing import List

from app.clients.openai_client import OpenAIClient
from app.models.document import Document
from app.schemas.evaluation import CheckResult
from app.services.storage import load_parsed_text
from app.utils.logging_setup import get_logger
from app.utils.text_utils import extract_numbers, truncate_to_tokens

logger = get_logger(__name__)


def _normalise_number(s: str) -> str:
    return s.replace(",", "").strip().lower()


class NumericChecker:
    """Check that numeric values in the answer appear in the source text."""

    def __init__(self) -> None:
        self.openai = OpenAIClient()

    def check(self, doc: Document, answer: str) -> CheckResult:
        if not answer:
            return CheckResult(
                category="numeric",
                pass_fail=True,
                score=1.0,
                details={"reason": "no_answer"},
                evaluator_type="hybrid",
            )

        source = load_parsed_text(doc.id) or doc.abstract or ""
        answer_numbers = extract_numbers(answer)

        if not answer_numbers:
            return CheckResult(
                category="numeric",
                pass_fail=True,
                score=1.0,
                details={"reason": "no_numbers_in_answer"},
                evaluator_type="hybrid",
            )

        mismatches: List[str] = []
        for num_str in answer_numbers:
            clean_num = _normalise_number(num_str)
            # Check if the number appears anywhere in the source
            if clean_num not in source.lower().replace(",", ""):
                mismatches.append(num_str)

        mismatch_rate = len(mismatches) / len(answer_numbers)
        score = max(0.0, 1.0 - mismatch_rate)
        pass_fail = mismatch_rate <= 0.3

        logger.info(
            f"event=numeric_check doc_id={doc.id} "
            f"numbers={len(answer_numbers)} mismatches={len(mismatches)}"
        )
        return CheckResult(
            category="numeric",
            pass_fail=pass_fail,
            score=round(score, 3),
            details={
                "answer_numbers": answer_numbers[:20],
                "mismatched_numbers": mismatches[:10],
                "mismatch_rate": round(mismatch_rate, 3),
            },
            evaluator_type="hybrid",
        )

    async def check_async(self, doc: Document, answer: str) -> CheckResult:
        """Enhanced check with LLM verification of borderline cases."""
        rule_result = self.check(doc, answer)

        # Only call LLM if there are actual mismatches worth verifying
        if rule_result.pass_fail or not rule_result.details.get("mismatched_numbers"):
            return rule_result

        source = load_parsed_text(doc.id) or doc.abstract or ""
        mismatched = rule_result.details.get("mismatched_numbers", [])
        prompt = (
            f"These numbers appear in an answer but not verbatim in the source: {mismatched}\n\n"
            f"Source text (excerpt):\n{truncate_to_tokens(source, 800)}\n\n"
            "Are these numbers reasonable given the source (e.g., calculations, rounding)? "
            'Return JSON: {"verified": bool, "explanation": str}'
        )
        try:
            response = await self.openai.judge(prompt, answer[:200])
            import json
            data = json.loads(response) if "{" in response else {}
            if data.get("verified"):
                rule_result.pass_fail = True
                rule_result.score = min(1.0, rule_result.score + 0.2)
                rule_result.details["llm_verified"] = True
        except Exception:
            pass

        rule_result.evaluator_type = "hybrid"
        return rule_result
