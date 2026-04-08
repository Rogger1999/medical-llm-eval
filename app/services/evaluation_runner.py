"""Run the full evaluation pipeline across all 8 evaluator categories."""
from __future__ import annotations

import json
import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

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
from app.models.evaluation import Evaluation, EvalCategory, EvaluationRun, EvalRunStatus, EvaluatorType
from app.models.task import Task, TaskType
from app.schemas.evaluation import EvaluationRunRequest
from app.services.subset_selector import SubsetSelector
from app.utils.logging_setup import get_logger

logger = get_logger(__name__)


class EvaluationRunner:
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self.factory = session_factory
        self.cfg = get_config()

    async def run(self, run_id: str, request: EvaluationRunRequest) -> None:
        """Full evaluation pipeline.

        Sessions are kept short-lived so that SQLite write locks are not held
        during long LLM API calls.  Pattern per document:
          1. short session  → fetch doc + task data
          2. no session     → LLM evaluation calls
          3. short session  → write Evaluation rows
        """
        logger.info(f"event=eval_run_start run_id={run_id} subset_size={request.subset_size} categories={request.categories}")

        # --- 1. Initialise run: fetch subset and update run metadata ----------
        async with self.factory() as session:
            logger.info(f"event=eval_subset_select_start run_id={run_id}")
            selector = SubsetSelector(session)
            subset = await selector.select_subset(request.subset_size)
            logger.info(f"event=eval_subset_selected run_id={run_id} count={len(subset)}")

            result = await session.execute(
                select(EvaluationRun).where(EvaluationRun.id == run_id)
            )
            run = result.scalar_one_or_none()
            if run is None:
                logger.error(f"event=eval_run_not_found run_id={run_id} — row may not have been committed before background task started")
            else:
                from app.models.document import DocumentStatus
                total_result = await session.execute(
                    select(Document).where(
                        Document.status.in_([DocumentStatus.parsed, DocumentStatus.chunked])
                    )
                )
                total_docs = len(total_result.scalars().all())
                run.subset_size = len(subset)
                run.total_docs = total_docs
                session.add(run)
                logger.info(f"event=eval_run_metadata_updated run_id={run_id} subset={len(subset)} total_docs={total_docs}")

            doc_ids = [doc.id for doc in subset]
            await session.commit()
            logger.info(f"event=eval_init_committed run_id={run_id}")

        all_evals: list[Evaluation] = []
        for i, doc_id in enumerate(doc_ids):
            logger.info(f"event=eval_doc_start run_id={run_id} doc_id={doc_id} progress={i+1}/{len(doc_ids)}")
            try:
                evals = await self._evaluate_document(doc_id, run_id, request.categories)
                all_evals.extend(evals)
                logger.info(f"event=eval_doc_done run_id={run_id} doc_id={doc_id} evals_written={len(evals)}")
            except Exception as exc:
                logger.error(f"event=eval_doc_error run_id={run_id} doc_id={doc_id} err={exc!r}", exc_info=True)

        logger.info(f"event=eval_all_docs_done run_id={run_id} total_evals={len(all_evals)}")

        # --- 3. Finalise run --------------------------------------------------
        aggregator = EvalAggregator()
        summary = aggregator.compute_summary(all_evals)
        logger.info(f"event=eval_summary_computed run_id={run_id} pass_rate={summary.overall_pass_rate}")

        async with self.factory() as session:
            result = await session.execute(
                select(EvaluationRun).where(EvaluationRun.id == run_id)
            )
            run = result.scalar_one_or_none()
            if run is None:
                logger.error(f"event=eval_run_finalise_not_found run_id={run_id}")
            else:
                run.status = EvalRunStatus.completed
                run.summary_json = json.dumps(summary.model_dump())
                session.add(run)
            await session.commit()

        logger.info(f"event=eval_run_complete run_id={run_id} docs={len(doc_ids)} evals={len(all_evals)}")

    async def _evaluate_document(
        self,
        doc_id: str,
        run_id: str,
        categories: Optional[list[str]],
    ) -> List[Evaluation]:
        """Evaluate one document.

        DB access is split into two short windows:
          - fetch window: read doc + task (session closed before LLM calls)
          - write window: persist Evaluation rows (session closed immediately after)
        """
        # --- fetch window -----------------------------------------------------
        async with self.factory() as session:
            doc_result = await session.execute(
                select(Document).where(Document.id == doc_id)
            )
            doc = doc_result.scalar_one_or_none()
            if doc is None:
                logger.warning(f"event=eval_doc_missing run_id={run_id} doc_id={doc_id}")
                return []

            task_result = await session.execute(
                select(Task)
                .where(Task.document_id == doc_id)
                .where(Task.task_type == TaskType.summarize)
                .order_by(Task.created_at.desc())
            )
            task = task_result.scalars().first()
            has_task = task is not None
            output = task.primary_output or "" if task else ""
            task_id = task.id if task else None
            session.expunge_all()

        logger.info(f"event=eval_doc_fetched run_id={run_id} doc_id={doc_id} has_task={has_task} output_len={len(output)}")

        # --- LLM evaluation (no DB session held) ------------------------------
        ingest_checker = IngestChecker()
        retrieval_checker = RetrievalChecker()
        grounding_checker = GroundingChecker()
        hallucination_checker = HallucinationChecker()
        numeric_checker = NumericChecker()
        abstention_checker = AbstentionChecker()
        adversarial_checker = AdversarialChecker()
        overclaiming_checker = OverclaimingChecker()

        logger.info(f"event=eval_checkers_start run_id={run_id} doc_id={doc_id}")
        try:
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
        except Exception as exc:
            logger.error(f"event=eval_checkers_error run_id={run_id} doc_id={doc_id} err={exc!r}", exc_info=True)
            raise
        logger.info(f"event=eval_checkers_done run_id={run_id} doc_id={doc_id} categories={list(results_map.keys())}")

        # --- write window -----------------------------------------------------
        evals: List[Evaluation] = []
        async with self.factory() as session:
            for category, check_result in results_map.items():
                if categories and category.value not in categories:
                    continue
                ev = Evaluation(
                    id=str(uuid.uuid4()),
                    document_id=doc_id,
                    task_id=task_id,
                    run_id=run_id,
                    eval_category=category,
                    pass_fail=check_result.pass_fail,
                    score=check_result.score,
                    details=json.dumps(check_result.details),
                    evaluator_type=EvaluatorType(check_result.evaluator_type),
                )
                session.add(ev)
                evals.append(ev)
            await session.flush()
            await session.commit()

        logger.info(f"event=eval_doc_written run_id={run_id} doc_id={doc_id} rows={len(evals)}")
        return evals
