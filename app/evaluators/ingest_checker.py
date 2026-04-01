"""Rule-based ingest quality checker."""
from __future__ import annotations

from app.models.document import Document, DocumentStatus
from app.schemas.evaluation import CheckResult
from app.services.storage import load_parsed_text
from app.utils.logging_setup import get_logger
from app.utils.text_utils import clean_text, count_words

logger = get_logger(__name__)

_MIN_TEXT_CHARS = 100
_MIN_WORDS = 20


class IngestChecker:
    """Checks ingestion quality: parse success, text length, metadata."""

    def check(self, doc: Document) -> CheckResult:
        issues: list[str] = []
        score = 1.0

        # Check parser status
        if doc.status == DocumentStatus.failed:
            issues.append("document_parse_failed")
            score -= 0.5

        # Check title
        if not doc.title or len(doc.title.strip()) < 3:
            issues.append("missing_title")
            score -= 0.15

        # Check abstract
        if not doc.abstract or len(doc.abstract.strip()) < 50:
            issues.append("missing_or_short_abstract")
            score -= 0.15

        # Check parsed text
        parsed = load_parsed_text(doc.id)
        if parsed is None:
            issues.append("no_parsed_text_file")
            score -= 0.3
        else:
            cleaned = clean_text(parsed)
            if len(cleaned) < _MIN_TEXT_CHARS:
                issues.append(f"parsed_text_too_short_chars={len(cleaned)}")
                score -= 0.3
            elif count_words(cleaned) < _MIN_WORDS:
                issues.append(f"parsed_text_too_few_words={count_words(cleaned)}")
                score -= 0.2

        # Check for null-content document
        has_any_content = bool(doc.title or doc.abstract or parsed)
        if not has_any_content:
            issues.append("empty_document")
            score = 0.0

        score = max(0.0, min(1.0, score))
        pass_fail = score >= 0.6 and "document_parse_failed" not in issues

        logger.info(
            f"event=ingest_check doc_id={doc.id} pass={pass_fail} score={score:.2f}"
        )
        return CheckResult(
            category="ingest",
            pass_fail=pass_fail,
            score=score,
            details={"issues": issues, "doc_status": doc.status.value if doc.status else "unknown"},
            evaluator_type="rule",
        )
