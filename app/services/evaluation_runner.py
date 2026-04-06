"""Run the full evaluation pipeline across all 8 evaluator categories."""
from __future__ import annotations

import json
import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_config
from app.evaluators.abstention_checker import AbstentionChecker
from app.evaluators.adversarial_checker import AdversarialChecker
from app.evaluators.aggregator import EvalAggregator
from app.evaluators.grounding_checker import GroundingChecker
from app.evaluators.hallucination_checker import HallucinationChecker
from app.evaluators.ingest_checker import IngestChecker
from app.evaluators.numeric_checker import NumericChecker
from app.evaluators.overclaiming_checker import OverclaimingChecker
from app.evaluators.retrieval_checker import RetrievalChecker
from app.models.document import Document
from app.models.evaluation import Evaluation, EvalCategory, EvalRunStatus, EvaluatorType
from app.models.task import Task, TaskType
from app.schemas.evaluation import EvaluationRunRequest
from app.services.subset_selector import SubsetSelector
from app.utils.logging_setup import get_logger

logger = get_logger(__name__)


class EvaluationRunner:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.cfg = get_config()

    async def run(self, run_id: str, request: EvaluationRunRequest) -> None:
        """Full evaluation pipeline."""
        from app.models.evaluation import EvaluationRun

        selector = SubsetSelector(self.session)
        subset = await selector.select_subset(request.subset_size)

        result = await self.session.execute(
            select(EvaluationRun).where(EvaluationRun.id == run_id)
        )
        run = result.scalar_one_or_none()
        if run:
            from sqlalchemy import select as _select
            from app.models.document import DocumentStatus
            total_result = await self.session.execute(
                _select(Document).where(
                    Document.status.in_([DocumentStatus.parsed, DocumentStatus.chunked])
                )
            )
            total_docs = len(total_result.scalars().all())
            run.subset_size = len(subset)
            run.total_docs = total_docs
            self.session.add(run)
            await self.session.flush()

        all_evals: list[Evaluation] = []
        for doc in subset:
            doc_id = doc.id  # capture before any potential rollback expires the object
            try:
                evals = await self._evaluate_document(doc, run_id, request.categories)
                all_evals.extend(evals)
            except Exception as exc:
                await self.session.rollback()
                logger.error(f"event=eval_doc_error doc_id={doc_id} err={exc!r}")

        aggregator = EvalAggregator()
        summary = aggregator.compute_summary(all_evals)

        if run:
            run.status = EvalRunStatus.completed
            run.summary_json = json.dumps(summary.model_dump())
            self.session.add(run)

        await self.session.commit()
        logger.info(f"event=eval_run_complete run_id={run_id} docs={len(subset)}")

    async def _evaluate_document(
        self,
        doc: Document,
        run_id: str,
        categories: Optional[list[str]],
    ) -> List[Evaluation]:
        """Run all evaluators on a single document."""
        ingest_checker = IngestChecker()
        retrieval_checker = RetrievalChecker()
        grounding_checker = GroundingChecker()
        hallucination_checker = HallucinationChecker()
        numeric_checker = NumericChecker()
        abstention_checker = AbstentionChecker()
        adversarial_checker = AdversarialChecker()
        overclaiming_checker = OverclaimingChecker()

        task = await self._get_or_create_task(doc)
        output = task.primary_output or "" if task else ""
        results_map = {
            EvalCategory.ingest: ingest_checker.check(doc),
            EvalCategory.retrieval: retrieval_checker.check(doc, task),
            EvalCategory.grounding: await grounding_checker.check(doc, task),
            EvalCategory.hallucination: await hallucination_checker.check(doc, output),
            EvalCategory.numeric: numeric_checker.check(doc, output),
            EvalCategory.abstention: abstention_checker.check(doc, output),
            EvalCategory.adversarial: adversarial_checker.check(doc, output),
            EvalCategory.overclaiming: await overclaiming_checker.check(doc, output),
        }

        evals: List[Evaluation] = []
        for category, check_result in results_map.items():
            if categories and category.value not in categories:
                continue
            ev = Evaluation(
                id=str(uuid.uuid4()),
                document_id=doc.id,
                task_id=task.id if task else None,
                run_id=run_id,
                eval_category=category,
                pass_fail=check_result.pass_fail,
                score=check_result.score,
                details=json.dumps(check_result.details),
                evaluator_type=EvaluatorType(check_result.evaluator_type),
            )
            self.session.add(ev)
            evals.append(ev)

        await self.session.flush()
        return evals

    async def _get_or_create_task(self, doc: Document) -> Optional[Task]:
        result = await self.session.execute(
            select(Task)
            .where(Task.document_id == doc.id)
            .where(Task.task_type == TaskType.summarize)
            .order_by(Task.created_at.desc())
        )
        return result.scalars().first()
