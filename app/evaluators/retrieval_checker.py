"""Retrieval quality checker: keyword recall over retrieved chunks."""
from __future__ import annotations

import re
from typing import Optional

from app.models.document import Document
from app.models.task import Task
from app.schemas.evaluation import CheckResult
from app.services.retrieval import ChunkRetriever, _tokenize
from app.services.storage import load_chunks
from app.utils.logging_setup import get_logger

logger = get_logger(__name__)

_DEFAULT_QUESTION = "What are the main findings and interventions described?"


class RetrievalChecker:
    """Checks whether retrieval correctly surfaces relevant content."""

    def check(
        self, doc: Document, task: Optional[Task] = None
    ) -> CheckResult:
        question = _DEFAULT_QUESTION
        if task and task.question:
            question = task.question

        chunks = load_chunks(doc.id)
        if not chunks:
            return CheckResult(
                category="retrieval",
                pass_fail=False,
                score=0.0,
                details={"reason": "no_chunks_available"},
                evaluator_type="rule",
            )

        retriever = ChunkRetriever()
        retrieved = retriever.retrieve(question, doc.id, top_k=5)

        # Single-chunk corpus: retrieval is trivial — pass if chunk was returned
        if len(chunks) == 1:
            passed = len(retrieved) > 0
            return CheckResult(
                category="retrieval",
                pass_fail=passed,
                score=1.0 if passed else 0.0,
                details={
                    "question": question,
                    "note": "single_chunk_corpus",
                    "chunks_retrieved": len(retrieved),
                    "total_chunks": 1,
                },
                evaluator_type="rule",
            )

        query_tokens = set(_tokenize(question))
        if not query_tokens:
            return CheckResult(
                category="retrieval",
                pass_fail=True,
                score=1.0,
                details={"reason": "empty_query_tokens"},
                evaluator_type="rule",
            )

        # Recall@k: fraction of query tokens found in top-k chunks
        found_tokens: set = set()
        for chunk, _score in retrieved:
            chunk_tokens = set(_tokenize(chunk["text"]))
            found_tokens |= query_tokens & chunk_tokens

        recall = len(found_tokens) / len(query_tokens) if query_tokens else 0.0
        coverage = len(retrieved) / min(5, len(chunks))

        score = 0.7 * recall + 0.3 * coverage
        pass_fail = score >= 0.3 and len(retrieved) > 0

        logger.info(
            f"event=retrieval_check doc_id={doc.id} recall={recall:.2f} "
            f"coverage={coverage:.2f} score={score:.2f}"
        )
        return CheckResult(
            category="retrieval",
            pass_fail=pass_fail,
            score=round(score, 3),
            details={
                "question": question,
                "recall_at_k": round(recall, 3),
                "chunks_retrieved": len(retrieved),
                "total_chunks": len(chunks),
                "found_tokens": list(found_tokens),
            },
            evaluator_type="rule",
        )
