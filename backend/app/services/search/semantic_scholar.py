import asyncio
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

from app.schemas.search import PaperSearchResult


PROJECT_ROOT = Path(__file__).resolve().parents[4]
BACKEND_ROOT = PROJECT_ROOT / "backend"
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(BACKEND_ROOT / ".env")

SEMANTIC_SCHOLAR_SEARCH_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
SEMANTIC_SCHOLAR_FIELDS = ",".join(
    [
        "title",
        "abstract",
        "year",
        "venue",
        "citationCount",
        "authors",
        "externalIds",
        "url",
        "openAccessPdf",
    ]
)
SEMANTIC_SCHOLAR_MAX_RETRIES = 3
SEMANTIC_SCHOLAR_RETRY_DELAYS = [2.0, 5.0, 10.0]


class SemanticScholarSearchError(Exception):
    pass


class SemanticScholarRateLimitError(SemanticScholarSearchError):
    pass


class SemanticScholarTimeoutError(SemanticScholarSearchError):
    pass


def clamp_limit(limit: int) -> int:
    if limit < 1:
        return 1
    if limit > 50:
        return 50
    return limit


def build_search_result(item: dict) -> PaperSearchResult:
    external_ids = item.get("externalIds") or {}
    open_access_pdf = item.get("openAccessPdf") or {}

    return PaperSearchResult(
        title=item.get("title") or "",
        abstract=item.get("abstract"),
        year=item.get("year"),
        venue=item.get("venue"),
        doi=external_ids.get("DOI"),
        citation_count=item.get("citationCount") or 0,
        authors=[
            author.get("name")
            for author in item.get("authors", [])
            if author.get("name")
        ],
        url=item.get("url"),
        external_ids=external_ids,
        open_access_pdf_url=open_access_pdf.get("url"),
    )


def build_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/json",
        "User-Agent": "LitFlow/0.1",
    }
    api_key = os.getenv("S2_API_KEY") or os.getenv("SEMANTIC_SCHOLAR_API_KEY")
    if api_key:
        headers["x-api-key"] = api_key
    return headers


async def search_semantic_scholar(
    query: str,
    limit: int = 10,
) -> list[PaperSearchResult]:
    limit = clamp_limit(limit)
    params = {
        "query": query,
        "limit": limit,
        "fields": SEMANTIC_SCHOLAR_FIELDS,
    }

    async with httpx.AsyncClient(timeout=10.0, headers=build_headers()) as client:
        for attempt in range(SEMANTIC_SCHOLAR_MAX_RETRIES + 1):
            try:
                response = await client.get(SEMANTIC_SCHOLAR_SEARCH_URL, params=params)
            except httpx.TimeoutException as exc:
                raise SemanticScholarTimeoutError(
                    "Semantic Scholar request timed out. Please try again later."
                ) from exc
            except httpx.HTTPError as exc:
                raise SemanticScholarSearchError(
                    "Semantic Scholar request failed. Please try again later."
                ) from exc

            if response.status_code != 429:
                break

            if attempt == SEMANTIC_SCHOLAR_MAX_RETRIES:
                raise SemanticScholarRateLimitError(
                    "Semantic Scholar rate limit reached. Set S2_API_KEY in .env or try again later."
                )

            await asyncio.sleep(SEMANTIC_SCHOLAR_RETRY_DELAYS[attempt])

    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise SemanticScholarSearchError(
            f"Semantic Scholar API returned an error: {response.status_code}."
        ) from exc

    payload = response.json()
    items = payload.get("data") or []
    return [build_search_result(item) for item in items]
