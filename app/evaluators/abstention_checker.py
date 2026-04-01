"""Check if model appropriately hedges when evidence is limited."""
from __future__ import annotations

from typing import Optional

from app.models.document import Document
from app.models.task import Task
from app.schemas.evaluation import CheckResult
from app.services.retrieval import ChunkRetriever
from app.utils.logging_setup import get_logger
from app.utils.text_utils import contains_hedging

logger = get_logger(__name__)

_OVERCONFIDENT_PHRASES = [
    "definitely",
    "certainly",
    "absolutely",
    "conclusively proves",
    "definitively shows",
    "100%",
    "guaranteed",
    "always effective",
    "proven cure",
    "always works",
]

_LOW_RETRIEVAL_SCORE_THRESHOLD = 0.2


class AbstentionChecker:
    """Verify model hedges appropriately when retrieval quality is low."""

    def check(
        self, doc: Document, answer: str, task: Optional[Task] = None
    ) -> CheckResult:
        if not answer:
            return CheckResult(
                category="abstention",
                pass_fail=True,
                score=1.0,
                details={"reason": "no_answer"},
                evaluator_type="rule",
            )

        question = (task.question if task else None) or "What are the findings?"
        retriever = ChunkRetriever()
        retrieved = retriever.retrieve(question, doc.id, top_k=3)

        avg_score = (
            sum(s for _, s in retrieved) / len(retrieved) if retrieved else 0.0
        )
        low_retrieval = avg_score < _LOW_RETRIEVAL_SCORE_THRESHOLD or len(retrieved) == 0

        has_hedging = contains_hedging(answer)
        answer_lower = answer.lower()
        overconfident = any(p in answer_lower for p in _OVERCONFIDENT_PHRASES)

        issues = []
        score = 1.0

        if overconfident:
            issues.append("overconfident_language_detected")
            score -= 0.4

        if low_retrieval and not has_hedging:
            issues.append("missing_hedging_on_low_retrieval")
            score -= 0.3

        if low_retrieval and has_hedging:
            # Good: model hedged when it should
            pass

        score = max(0.0, min(1.0, score))
        pass_fail = score >= 0.6

        logger.info(
            f"event=abstention_check doc_id={doc.id} "
            f"low_retrieval={low_retrieval} hedging={has_hedging} pass={pass_fail}"
        )
        return CheckResult(
            category="abstention",
            pass_fail=pass_fail,
            score=round(score, 3),
            details={
                "low_retrieval": low_retrieval,
                "avg_retrieval_score": round(avg_score, 3),
                "has_hedging": has_hedging,
                "overconfident": overconfident,
                "issues": issues,
            },
            evaluator_type="rule",
        )
