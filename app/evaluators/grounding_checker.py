"""LLM-as-judge: verify claims in answer are grounded in source chunks."""
from __future__ import annotations

import json
from typing import Optional

from app.clients.openai_client import OpenAIClient
from app.models.document import Document
from app.models.task import Task
from app.prompts.grounding_check import GROUNDING_CHECK_SYSTEM, GROUNDING_CHECK_USER_TEMPLATE
from app.schemas.evaluation import CheckResult
from app.services.retrieval import ChunkRetriever
from app.services.storage import load_chunks, load_parsed_text
from app.utils.logging_setup import get_logger
from app.utils.text_utils import truncate_to_tokens

logger = get_logger(__name__)


class GroundingChecker:
    """Check whether task output claims are grounded in source evidence."""

    def __init__(self) -> None:
        self.openai = OpenAIClient()
        self.retriever = ChunkRetriever()

    async def check(
        self, doc: Document, task: Optional[Task] = None
    ) -> CheckResult:
        if task is None or not task.primary_output:
            return CheckResult(
                category="grounding",
                pass_fail=None,
                score=None,
                details={"reason": "skipped_no_task_output"},
                evaluator_type="llm",
            )

        answer = task.primary_output
        question = task.question or "What are the key findings?"

        chunks = load_chunks(doc.id)
        if chunks:
            retrieved = self.retriever.retrieve(question, doc.id, top_k=5)
            context = "\n\n".join(c["text"] for c, _ in retrieved)
        else:
            context = load_parsed_text(doc.id) or doc.abstract or ""

        context = truncate_to_tokens(context, 1500)

        prompt = GROUNDING_CHECK_USER_TEMPLATE.format(
            answer=truncate_to_tokens(answer, 500),
            context=context,
        )

        try:
            response = await self.openai.complete(prompt, system=GROUNDING_CHECK_SYSTEM)
            result = self._parse_response(response)
        except Exception as exc:
            logger.error(f"event=grounding_llm_error doc_id={doc.id} err={exc!r}")
            return CheckResult(
                category="grounding",
                pass_fail=None,
                score=None,
                details={"reason": "llm_unavailable", "error": str(exc)},
                evaluator_type="llm",
            )

        score = result.get("grounding_score", 0.5)
        pass_fail = score >= 0.6
        logger.info(f"event=grounding_check doc_id={doc.id} score={score:.2f}")
        return CheckResult(
            category="grounding",
            pass_fail=pass_fail,
            score=score,
            details=result,
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
            grounded = "not grounded" not in response.lower() and "unsupported" not in response.lower()
            return {
                "grounding_score": 0.8 if grounded else 0.3,
                "raw": response[:200],
            }
