"""Aggregate evaluation results into a MetricsSummary."""
from __future__ import annotations

from typing import Iterable, List

from app.config import get_config
from app.models.evaluation import Evaluation
from app.schemas.metrics import CategoryMetrics, MetricsSummary
from app.utils.logging_setup import get_logger

logger = get_logger(__name__)


class EvalAggregator:
    def __init__(self) -> None:
        self.cfg = get_config()
        self.weights: dict = self.cfg.evaluation.get("weights", {})

    def compute_summary(
        self,
        evaluations: Iterable[Evaluation],
    ) -> MetricsSummary:
        """Compute overall and per-category metrics from evaluation records."""
        evals = list(evaluations)

        if not evals:
            return MetricsSummary(
                total_evaluations=0,
                total_passed=0,
                total_failed=0,
                overall_pass_rate=0.0,
                by_category={},
            )

        category_buckets: dict = {}
        for ev in evals:
            cat = ev.eval_category.value if ev.eval_category else "unknown"
            category_buckets.setdefault(cat, []).append(ev)

        by_category: dict = {}
        total_passed = 0
        total_failed = 0
        weighted_num = 0.0
        weighted_den = 0.0

        for cat, cat_evals in category_buckets.items():
            passed = sum(1 for e in cat_evals if e.pass_fail is True)
            failed = sum(1 for e in cat_evals if e.pass_fail is False)
            total = len(cat_evals)
            # N/A rows (pass_fail=None) don't count toward pass rate denominator
            judged = passed + failed
            pass_rate = passed / judged if judged > 0 else 0.0

            scores = [e.score for e in cat_evals if e.score is not None]
            avg_score = sum(scores) / len(scores) if scores else None

            by_category[cat] = CategoryMetrics(
                category=cat,
                total=total,
                passed=passed,
                failed=failed,
                pass_rate=round(pass_rate, 3),
                avg_score=round(avg_score, 3) if avg_score is not None else None,
            )

            total_passed += passed
            total_failed += failed

            # Only include category in weighted score if it has judged rows
            if judged > 0:
                weight = self.weights.get(cat, 1.0)
                weighted_num += pass_rate * weight
                weighted_den += weight

        total_evals = total_passed + total_failed
        overall_pass_rate = total_passed / total_evals if total_evals > 0 else 0.0
        weighted_score = weighted_num / weighted_den if weighted_den > 0 else None

        summary = MetricsSummary(
            total_evaluations=total_evals,
            total_passed=total_passed,
            total_failed=total_failed,
            overall_pass_rate=round(overall_pass_rate, 3),
            weighted_score=round(weighted_score, 3) if weighted_score is not None else None,
            by_category=by_category,
        )

        logger.info(
            f"event=aggregation_done total={total_evals} "
            f"pass_rate={overall_pass_rate:.2%}"
        )
        return summary
