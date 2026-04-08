"""Orchestrate LLM tasks: summarize, extract, QA."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.clients.claude_client import ClaudeClient
from app.clients.openai_client import OpenAIClient
from app.config import get_config
from app.models.document import Document
from app.models.task import Task, TaskStatus, TaskType
from app.prompts.extraction import EXTRACTION_SYSTEM, EXTRACTION_USER_TEMPLATE
from app.prompts.grounded_qa import GROUNDED_QA_SYSTEM, GROUNDED_QA_USER_TEMPLATE
from app.prompts.summarization import SUMMARIZATION_SYSTEM, SUMMARIZATION_USER_TEMPLATE
from app.services.retrieval import ChunkRetriever
from app.services.storage import load_parsed_text
from app.utils.logging_setup import get_logger
from app.utils.text_utils import truncate_to_tokens

logger = get_logger(__name__)


class TaskRunner:
    """Run LLM tasks with short-lived DB sessions.

    The factory is used to open sessions only around DB operations so that
    SQLite write locks are never held during LLM API calls.
    """

    def __init__(self, session_factory: async_sessionmaker) -> None:
        self.factory = session_factory
        self.cfg = get_config()
        self.claude = ClaudeClient()
        self.openai = OpenAIClient()
        self.retriever = ChunkRetriever()

    async def _fetch_doc(self, document_id: str) -> Document:
        async with self.factory() as session:
            result = await session.execute(
                select(Document).where(Document.id == document_id)
            )
            doc = result.scalar_one_or_none()
            if doc is None:
                raise ValueError(f"Document not found: {document_id}")
            session.expunge(doc)
        return doc

    async def _create_task(self, doc_id: str, task_type: TaskType, question: str | None = None) -> str:
        """Insert a running task row and return its ID."""
        task = Task(
            id=str(uuid.uuid4()),
            document_id=doc_id,
            task_type=task_type,
            status=TaskStatus.running,
            primary_model=self.cfg.get("models", "claude", "model"),
            checker_model=self.cfg.get("models", "openai", "model"),
            question=question,
        )
        async with self.factory() as session:
            session.add(task)
            await session.commit()
        return task.id

    async def _finish_task(self, task_id: str, primary: str, checker: str) -> Task:
        async with self.factory() as session:
            result = await session.execute(select(Task).where(Task.id == task_id))
            task = result.scalar_one()
            task.primary_output = primary
            task.checker_output = checker
            task.status = TaskStatus.done
            task.completed_at = datetime.now(timezone.utc)
            session.add(task)
            await session.commit()
            session.expunge(task)
        return task

    async def _fail_task(self, task_id: str, error: str) -> None:
        try:
            async with self.factory() as session:
                result = await session.execute(select(Task).where(Task.id == task_id))
                task = result.scalar_one_or_none()
                if task:
                    task.status = TaskStatus.failed
                    task.error = error
                    session.add(task)
                    await session.commit()
        except Exception as exc:
            logger.error(f"event=fail_task_update_error task_id={task_id} err={exc!r}")

    async def _run_checker(self, prompt: str, system: str) -> str:
        """Call OpenAI checker; return error note on failure (non-blocking)."""
        try:
            return await self.openai.complete(prompt, system=system)
        except Exception as exc:
            logger.warning(f"event=checker_unavailable err={exc!r}")
            return f"[Checker unavailable: {type(exc).__name__}: {exc}]"

    async def run_summarize(self, document_id: str) -> Task:
        doc = await self._fetch_doc(document_id)          # DB: read, session closed
        task_id = await self._create_task(document_id, TaskType.summarize)  # DB: write, session closed
        try:
            # No DB session held during LLM calls.
            text = load_parsed_text(document_id) or doc.abstract or ""
            context = truncate_to_tokens(text, 3000)
            prompt = SUMMARIZATION_USER_TEMPLATE.format(
                title=doc.title or "Unknown",
                text=context,
            )
            primary = await self.claude.complete(prompt, system=SUMMARIZATION_SYSTEM)
            checker_prompt = f"Evaluate this summary for accuracy:\n\nSummary:\n{primary}\n\nSource text:\n{context[:1000]}"
            checker = await self._run_checker(checker_prompt, "You are a medical literature evaluator.")
            return await self._finish_task(task_id, primary, checker)  # DB: write, session closed
        except Exception as exc:
            await self._fail_task(task_id, str(exc))
            logger.error(f"event=summarize_fail doc={document_id} err={exc!r}")
            raise

    async def run_extract(self, document_id: str) -> Task:
        doc = await self._fetch_doc(document_id)
        task_id = await self._create_task(document_id, TaskType.extract)
        try:
            text = load_parsed_text(document_id) or doc.abstract or ""
            context = truncate_to_tokens(text, 3000)
            prompt = EXTRACTION_USER_TEMPLATE.format(
                title=doc.title or "Unknown",
                text=context,
            )
            primary = await self.claude.complete(prompt, system=EXTRACTION_SYSTEM)
            checker_prompt = f"Check this extracted data for accuracy:\n{primary}\n\nSource:\n{context[:1000]}"
            checker = await self._run_checker(checker_prompt, "You are a medical data validator.")
            return await self._finish_task(task_id, primary, checker)
        except Exception as exc:
            await self._fail_task(task_id, str(exc))
            raise

    async def run_qa(self, document_id: str, question: str) -> Task:
        doc = await self._fetch_doc(document_id)
        task_id = await self._create_task(document_id, TaskType.qa, question=question)
        try:
            retrieved = self.retriever.retrieve(question, document_id)
            if retrieved:
                context = "\n\n".join(f"[Chunk {i+1}]: {c['text']}" for i, (c, _) in enumerate(retrieved))
            else:
                context = load_parsed_text(document_id) or doc.abstract or ""
                context = truncate_to_tokens(context, 2000)
            prompt = GROUNDED_QA_USER_TEMPLATE.format(
                question=question, context=context
            )
            primary = await self.claude.complete(prompt, system=GROUNDED_QA_SYSTEM)
            checker_prompt = f"Evaluate answer groundedness:\n\nQuestion: {question}\nAnswer: {primary}\nContext: {context[:800]}"
            checker = await self._run_checker(checker_prompt, "You are a medical grounding evaluator.")
            return await self._finish_task(task_id, primary, checker)
        except Exception as exc:
            await self._fail_task(task_id, str(exc))
            raise
