"""Stratified subset selection for evaluation."""
from __future__ import annotations

import random
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_config
from app.models.document import Document, DocumentStatus
from app.models.evaluation import Evaluation
from app.utils.logging_setup import get_logger

logger = get_logger(__name__)


class SubsetSelector:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.cfg = get_config()

    async def select_subset(
        self, desired_size: Optional[int] = None
    ) -> List[Document]:
        """Select documents for evaluation with stratification."""
        eval_cfg = self.cfg.evaluation
        fraction = eval_cfg.get("subset_fraction", 0.10)
        min_size = eval_cfg.get("min_subset_size", 5)
        max_size = eval_cfg.get("max_subset_size", 50)

        # Get all parsed docs
        result = await self.session.execute(
            select(Document).where(
                Document.status.in_([DocumentStatus.parsed, DocumentStatus.chunked])
            )
        )
        all_docs = result.scalars().all()
        total = len(all_docs)

        if total == 0:
            logger.warning("event=no_docs_for_eval")
            return []

        if desired_size is not None:
            size = max(min_size, min(desired_size, max_size, total))
        else:
            size = max(min_size, min(int(total * fraction), max_size, total))

        # Docs with previous failures get priority
        failed_doc_ids = await self._get_failed_doc_ids()
        priority = [d for d in all_docs if d.id in failed_doc_ids]
        remainder = [d for d in all_docs if d.id not in failed_doc_ids]

        # Stratify remainder by year
        year_buckets: dict = {}
        for doc in remainder:
            yr = doc.year or 0
            year_buckets.setdefault(yr, []).append(doc)

        selected: List[Document] = list(priority[:size])
        slots_left = size - len(selected)

        if slots_left > 0 and year_buckets:
            bucket_keys = sorted(year_buckets.keys(), reverse=True)
            per_bucket = max(1, slots_left // len(bucket_keys))
            for key in bucket_keys:
                bucket = year_buckets[key]
                random.shuffle(bucket)
                selected.extend(bucket[:per_bucket])
                if len(selected) >= size:
                    break

        # Top up with random if still short
        if len(selected) < size:
            remaining_pool = [d for d in remainder if d not in selected]
            random.shuffle(remaining_pool)
            selected.extend(remaining_pool[: size - len(selected)])

        final = selected[:size]
        logger.info(
            f"event=subset_selected total={total} selected={len(final)} priority={len(priority)}"
        )
        return final

    async def _get_failed_doc_ids(self) -> set:
        result = await self.session.execute(
            select(Evaluation.document_id).where(Evaluation.pass_fail == False)  # noqa: E712
        )
        return {row[0] for row in result.all()}
