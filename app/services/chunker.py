"""Split parsed document text into overlapping chunks."""
from __future__ import annotations

from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_config
from app.models.document import Document, DocumentStatus
from app.services.storage import load_parsed_text, save_chunks
from app.utils.logging_setup import get_logger
from app.utils.text_utils import split_sentences

logger = get_logger(__name__)


def _approx_tokens(text: str) -> int:
    return len(text) // 4


class TextChunker:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.cfg = get_config()

    async def chunk_document(self, doc: Document) -> List[dict]:
        """Load parsed text, chunk it, save chunks file. Return chunk list."""
        text = load_parsed_text(doc.id)
        if not text:
            logger.warning(f"event=chunk_skip reason=no_text doc_id={doc.id}")
            return []

        chunks = self._chunk_text(text, doc.id)
        if chunks:
            save_chunks(doc.id, chunks)
            doc.status = DocumentStatus.chunked
            self.session.add(doc)
            logger.info(f"event=chunked doc_id={doc.id} chunks={len(chunks)}")
        return chunks

    def _chunk_text(self, text: str, doc_id: str) -> List[dict]:
        cfg_c = self.cfg.chunking
        chunk_size = cfg_c.get("chunk_size", 512)
        overlap = cfg_c.get("overlap", 64)
        min_size = cfg_c.get("min_chunk_size", 50)
        preserve = cfg_c.get("preserve_sentences", True)

        if preserve:
            return self._sentence_aware_chunks(
                text, doc_id, chunk_size, overlap, min_size
            )
        return self._simple_chunks(text, doc_id, chunk_size, overlap, min_size)

    def _sentence_aware_chunks(
        self,
        text: str,
        doc_id: str,
        chunk_size: int,
        overlap: int,
        min_size: int,
    ) -> List[dict]:
        sentences = split_sentences(text)
        chunks: List[dict] = []
        current_tokens = 0
        current_sentences: List[str] = []
        char_start = 0
        chunk_index = 0

        for sentence in sentences:
            toks = _approx_tokens(sentence)
            if current_tokens + toks > chunk_size and current_sentences:
                chunk_text = " ".join(current_sentences)
                char_end = char_start + len(chunk_text)
                if _approx_tokens(chunk_text) >= min_size:
                    chunks.append({
                        "doc_id": doc_id,
                        "chunk_index": chunk_index,
                        "char_start": char_start,
                        "char_end": char_end,
                        "text": chunk_text,
                    })
                    chunk_index += 1
                # Keep overlap sentences
                overlap_tokens = 0
                overlap_sents: List[str] = []
                for s in reversed(current_sentences):
                    if overlap_tokens + _approx_tokens(s) <= overlap:
                        overlap_sents.insert(0, s)
                        overlap_tokens += _approx_tokens(s)
                    else:
                        break
                char_start = char_end - sum(len(s) for s in overlap_sents)
                current_sentences = overlap_sents
                current_tokens = overlap_tokens
            current_sentences.append(sentence)
            current_tokens += toks

        if current_sentences:
            chunk_text = " ".join(current_sentences)
            if _approx_tokens(chunk_text) >= min_size:
                chunks.append({
                    "doc_id": doc_id,
                    "chunk_index": chunk_index,
                    "char_start": char_start,
                    "char_end": char_start + len(chunk_text),
                    "text": chunk_text,
                })
        return chunks

    def _simple_chunks(
        self,
        text: str,
        doc_id: str,
        chunk_size: int,
        overlap: int,
        min_size: int,
    ) -> List[dict]:
        chunk_chars = chunk_size * 4
        overlap_chars = overlap * 4
        chunks = []
        start = 0
        idx = 0
        while start < len(text):
            end = start + chunk_chars
            chunk_text = text[start:end]
            if len(chunk_text) >= min_size:
                chunks.append({
                    "doc_id": doc_id,
                    "chunk_index": idx,
                    "char_start": start,
                    "char_end": start + len(chunk_text),
                    "text": chunk_text,
                })
                idx += 1
            start = end - overlap_chars
            if start >= len(text):
                break
        return chunks
