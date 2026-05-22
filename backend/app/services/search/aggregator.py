import asyncio
import logging
import re
import string

from app.schemas.search import PaperSearchResult
from app.services.search.arxiv import search_arxiv
from app.services.search.openalex import search_openalex
from app.services.search.scoring import score_paper_result
from app.services.search.semantic_scholar import search_semantic_scholar
from app.services.search.venue_classifier import normalize_venue_name


logger = logging.getLogger(__name__)

SOURCE_URL_PRIORITY = {
    "semantic_scholar": 0,
    "openalex": 1,
    "arxiv": 2,
}


def clamp_limit(limit: int) -> int:
    if limit < 1:
        return 1
    if limit > 50:
        return 50
    return limit


def normalize_doi(doi: str | None) -> str | None:
    if not doi:
        return None

    value = doi.strip().lower()
    for prefix in ("https://doi.org/", "http://dx.doi.org/", "doi:"):
        if value.startswith(prefix):
            value = value.removeprefix(prefix)
    return value.strip() or None


def normalize_title(title: str | None) -> str:
    if not title:
        return ""

    translator = str.maketrans("", "", string.punctuation)
    value = title.lower().translate(translator)
    return re.sub(r"\s+", " ", value).strip()


def dedupe_key(result: PaperSearchResult) -> str:
    doi = normalize_doi(result.doi)
    if doi:
        return f"doi:{doi}"
    return f"title:{normalize_title(result.title)}"


def source_list(result: PaperSearchResult) -> list[str]:
    sources = list(result.sources)
    if result.source and result.source not in sources:
        sources.append(result.source)
    return sources


def prefer_longer(current: str | None, incoming: str | None) -> str | None:
    if not current:
        return incoming
    if incoming and len(incoming) > len(current):
        return incoming
    return current


def merge_authors(current: list[str], incoming: list[str]) -> list[str]:
    merged = list(current)
    seen = {author.lower() for author in merged}
    for author in incoming:
        key = author.lower()
        if key not in seen:
            merged.append(author)
            seen.add(key)
    return merged


def merge_year(current: int | None, incoming: int | None) -> int | None:
    if current is None:
        return incoming
    if incoming is None:
        return current
    if 1800 <= current <= 2100 and 1800 <= incoming <= 2100:
        return min(current, incoming)
    return current


def merge_venue(current: str | None, incoming: str | None) -> str | None:
    if not current:
        return incoming
    current_normalized = normalize_venue_name(current)
    incoming_normalized = normalize_venue_name(incoming)
    if current_normalized == "arXiv" and incoming_normalized and incoming_normalized != "arXiv":
        return incoming
    return current


def should_replace_url(current: PaperSearchResult, incoming: PaperSearchResult) -> bool:
    if not current.url:
        return bool(incoming.url)
    if not incoming.url:
        return False
    return SOURCE_URL_PRIORITY.get(incoming.source, 99) < SOURCE_URL_PRIORITY.get(
        current.source, 99
    )


def merge_results(current: PaperSearchResult, incoming: PaperSearchResult) -> PaperSearchResult:
    current.title = prefer_longer(current.title, incoming.title) or ""
    current.abstract = prefer_longer(current.abstract, incoming.abstract)
    current.year = merge_year(current.year, incoming.year)
    current.venue = merge_venue(current.venue, incoming.venue)
    current.doi = current.doi or incoming.doi
    current.citation_count = max(current.citation_count or 0, incoming.citation_count or 0)
    current.authors = merge_authors(current.authors, incoming.authors)

    if should_replace_url(current, incoming):
        current.url = incoming.url
        current.source = incoming.source

    current.open_access_pdf_url = current.open_access_pdf_url or incoming.open_access_pdf_url
    current.external_ids = {**current.external_ids, **incoming.external_ids}
    for source in source_list(incoming):
        if source not in current.sources:
            current.sources.append(source)
    return current


async def run_source(name: str, query: str, limit: int) -> list[PaperSearchResult]:
    search_functions = {
        "semantic_scholar": search_semantic_scholar,
        "openalex": search_openalex,
        "arxiv": search_arxiv,
    }

    try:
        return await search_functions[name](query=query, limit=limit)
    except Exception as exc:
        logger.warning("%s search failed: %s", name, exc)
        return []


async def search_all_sources(query: str, limit: int = 10) -> list[PaperSearchResult]:
    limit = clamp_limit(limit)
    source_results = await asyncio.gather(
        run_source("semantic_scholar", query, limit),
        run_source("openalex", query, limit),
        run_source("arxiv", query, limit),
    )

    merged_by_key: dict[str, PaperSearchResult] = {}
    for results in source_results:
        for result in results:
            result.sources = source_list(result)
            key = dedupe_key(result)
            if key in ("title:", "doi:"):
                continue

            if key not in merged_by_key:
                merged_by_key[key] = result
            else:
                merge_results(merged_by_key[key], result)

    merged_results = list(merged_by_key.values())
    for result in merged_results:
        score_paper_result(result, query)

    merged_results.sort(
        key=lambda result: (
            result.final_score or 0.0,
            result.relevance_score or 0.0,
            result.authority_score or 0.0,
            result.citation_count or 0,
            result.year or 0,
        ),
        reverse=True,
    )
    return merged_results[:limit]
