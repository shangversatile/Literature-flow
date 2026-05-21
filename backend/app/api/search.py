from fastapi import APIRouter, HTTPException, Query

from app.schemas.search import PaperSearchResult
from app.services.search.aggregator import search_all_sources
from app.services.search.arxiv import (
    ArxivParseError,
    ArxivSearchError,
    ArxivTimeoutError,
    search_arxiv,
)
from app.services.search.openalex import (
    OpenAlexRateLimitError,
    OpenAlexSearchError,
    OpenAlexTimeoutError,
    search_openalex,
)
from app.services.search.semantic_scholar import (
    SemanticScholarRateLimitError,
    SemanticScholarSearchError,
    SemanticScholarTimeoutError,
    search_semantic_scholar,
)


router = APIRouter(prefix="/search", tags=["search"])


@router.get("/semantic-scholar", response_model=list[PaperSearchResult])
async def search_semantic_scholar_api(
    query: str = Query(..., min_length=1),
    limit: int = 10,
) -> list[PaperSearchResult]:
    try:
        return await search_semantic_scholar(query=query, limit=limit)
    except SemanticScholarTimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except SemanticScholarRateLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except SemanticScholarSearchError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/openalex", response_model=list[PaperSearchResult])
async def search_openalex_api(
    query: str = Query(..., min_length=1),
    limit: int = 10,
) -> list[PaperSearchResult]:
    try:
        return await search_openalex(query=query, limit=limit)
    except OpenAlexTimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except OpenAlexRateLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except OpenAlexSearchError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/arxiv", response_model=list[PaperSearchResult])
async def search_arxiv_api(
    query: str = Query(..., min_length=1),
    limit: int = 10,
) -> list[PaperSearchResult]:
    try:
        return await search_arxiv(query=query, limit=limit)
    except ArxivTimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except ArxivParseError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ArxivSearchError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/all", response_model=list[PaperSearchResult])
async def search_all_api(
    query: str = Query(..., min_length=1),
    limit: int = 10,
) -> list[PaperSearchResult]:
    return await search_all_sources(query=query, limit=limit)
