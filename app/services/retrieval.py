"""BM25-style keyword retrieval over document chunks."""
from __future__ import annotations

import math
import re
from typing import List, Tuple

from app.config import get_config
from app.services.storage import load_chunks
from app.utils.logging_setup import get_logger

logger = get_logger(__name__)

_STOP_WORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "to", "of", "in",
    "on", "at", "by", "for", "with", "about", "as", "or", "and",
    "but", "not", "this", "that", "it", "its", "from",
}


def _tokenize(text: str) -> List[str]:
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return [t for t in tokens if t not in _STOP_WORDS and len(t) > 1]


def _idf(df: int, n_docs: int) -> float:
    return math.log((n_docs - df + 0.5) / (df + 0.5) + 1)


def bm25_score(
    query_tokens: List[str],
    chunk_tokens: List[str],
    n_docs: int,
    df_map: dict,
    k1: float = 1.5,
    b: float = 0.75,
    avg_dl: float = 128.0,
) -> float:
    dl = len(chunk_tokens)
    if dl == 0:
        return 0.0
    tf_map: dict = {}
    for tok in chunk_tokens:
        tf_map[tok] = tf_map.get(tok, 0) + 1

    score = 0.0
    for q in query_tokens:
        if q not in tf_map:
            continue
        tf = tf_map[q]
        idf = _idf(df_map.get(q, 1), n_docs)
        numerator = tf * (k1 + 1)
        denominator = tf + k1 * (1 - b + b * dl / avg_dl)
        score += idf * numerator / denominator
    return score


class ChunkRetriever:
    def __init__(self) -> None:
        self.cfg = get_config()

    def retrieve(
        self,
        question: str,
        doc_id: str,
        top_k: int | None = None,
    ) -> List[Tuple[dict, float]]:
        """Return top-k (chunk, score) pairs sorted by BM25 score."""
        if top_k is None:
            top_k = self.cfg.retrieval.get("top_k", 5)

        chunks = load_chunks(doc_id)
        if not chunks:
            logger.warning(f"event=no_chunks doc_id={doc_id}")
            return []

        query_tokens = _tokenize(question)
        if not query_tokens:
            return []

        tokenized_chunks = [_tokenize(c["text"]) for c in chunks]
        n_docs = len(tokenized_chunks)
        avg_dl = sum(len(t) for t in tokenized_chunks) / max(n_docs, 1)

        # Build document frequency map
        df_map: dict = {}
        for tok_list in tokenized_chunks:
            seen = set(tok_list)
            for tok in seen:
                df_map[tok] = df_map.get(tok, 0) + 1

        scored: List[Tuple[dict, float]] = []
        for chunk, tok_list in zip(chunks, tokenized_chunks):
            score = bm25_score(
                query_tokens, tok_list, n_docs, df_map, avg_dl=avg_dl
            )
            scored.append((chunk, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        top = scored[:top_k]
        # With only 1 chunk there is no choice — always return it.
        # Apply min_score filter only when corpus has multiple chunks.
        if n_docs == 1:
            return top
        min_score = self.cfg.retrieval.get("min_score", 0.01)
        return [(c, s) for c, s in top if s >= min_score]
