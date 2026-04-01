"""Async client for the Europe PMC REST API."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx

from app.config import get_config
from app.utils.logging_setup import get_logger

logger = get_logger(__name__)

_BASE_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest"


def _normalize_result(item: dict) -> dict:
    """Normalise a raw EuropePMC result into our standard dict."""
    authors_raw = item.get("authorString") or ""
    year = None
    pub_year = item.get("pubYear")
    if pub_year:
        try:
            year = int(pub_year)
        except (TypeError, ValueError):
            pass

    pmcid = item.get("pmcid") or item.get("pmcId") or None
    pmid = str(item.get("pmid", "")) or None
    source_id = pmcid or pmid or item.get("id", "")

    pdf_url: Optional[str] = None
    if pmcid:
        pdf_url = f"https://europepmc.org/backend/ptpmcrender.fcgi?accid={pmcid}&blobtype=pdf"

    return {
        "source_id": source_id,
        "title": item.get("title", "").rstrip("."),
        "authors": authors_raw,
        "abstract": item.get("abstractText") or item.get("abstract") or "",
        "journal": item.get("journalTitle") or item.get("journal", {}).get("title", "") if isinstance(item.get("journal"), dict) else item.get("journalTitle", ""),
        "year": year,
        "doi": item.get("doi"),
        "pmcid": pmcid,
        "pmid": pmid,
        "pdf_url": pdf_url,
    }


class EuropePMCClient:
    def __init__(self) -> None:
        self.cfg = get_config()
        src_cfg = self.cfg.document_sources.get("europe_pmc", {})
        self.base_url = src_cfg.get("base_url", _BASE_URL)
        self.timeout = src_cfg.get("timeout_seconds", 30)
        self.format = src_cfg.get("format", "json")

    async def search(
        self,
        query: str,
        page_size: int = 25,
        page: int = 1,
        filters: Optional[List[str]] = None,
    ) -> List[dict]:
        """Search Europe PMC and return normalised result dicts."""
        filter_parts = filters or self.cfg.topic_defaults.get("filters", [])
        full_query = query
        if filter_parts:
            full_query = query + " " + " ".join(filter_parts)

        params: Dict[str, Any] = {
            "query": full_query,
            "resultType": "core",
            "pageSize": min(page_size, 100),
            "page": page,
            "format": self.format,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(f"{self.base_url}/search", params=params)
            resp.raise_for_status()
            data = resp.json()

        results = data.get("resultList", {}).get("result", [])
        normalised = [_normalize_result(r) for r in results]
        logger.info(
            f"event=epmc_search query={query!r} returned={len(normalised)}"
        )
        return normalised

    async def get_full_text(self, pmcid: str) -> Optional[str]:
        """Fetch full text XML for a PMC article."""
        url = f"{self.base_url}/{pmcid}/fullTextXML"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(url)
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
        return resp.text

    async def get_pdf_url(self, pmcid: str) -> Optional[str]:
        """Construct PDF download URL for a PMC article."""
        if not pmcid:
            return None
        return f"https://europepmc.org/backend/ptpmcrender.fcgi?accid={pmcid}&blobtype=pdf"
