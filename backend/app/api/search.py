from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.db.session import get_session
from app.models.paper import Paper
from app.schemas.search import PaperSearchResult, SearchSaveRequest, SearchSaveResponse
from app.services.search.aggregator import normalize_doi, normalize_title, search_all_sources
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


def clamp_limit(limit: int) -> int:
    if limit < 1:
        return 1
    if limit > 50:
        return 50
    return limit


def find_existing_paper(
    session: Session,
    result: PaperSearchResult,
) -> Paper | None:
    normalized_doi = normalize_doi(result.doi)
    if normalized_doi:
        papers_with_doi = session.exec(
            select(Paper).where(Paper.doi.is_not(None))
        ).all()
        for paper in papers_with_doi:
            if normalize_doi(paper.doi) == normalized_doi:
                return paper

    title_key = normalize_title(result.title)
    if not title_key:
        return None
    return session.exec(
        select(Paper).where(Paper.normalized_title == title_key)
    ).first()


def update_existing_paper(paper: Paper, result: PaperSearchResult) -> bool:
    changed = False
    if not paper.pdf_url and result.open_access_pdf_url:
        paper.pdf_url = result.open_access_pdf_url
        changed = True
    if not paper.abstract and result.abstract:
        paper.abstract = result.abstract
        changed = True
    if result.citation_count > (paper.citation_count or 0):
        paper.citation_count = result.citation_count
        changed = True

    if changed:
        paper.updated_at = datetime.utcnow()
    return changed


def create_paper_from_search_result(result: PaperSearchResult) -> Paper:
    title = result.title.strip()
    normalized_doi = normalize_doi(result.doi)
    return Paper(
        title=title,
        normalized_title=normalize_title(title),
        doi=normalized_doi,
        year=result.year,
        venue=result.venue,
        abstract=result.abstract,
        citation_count=result.citation_count,
        pdf_url=result.open_access_pdf_url,
        status="DISCOVERED",
    )


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


@router.post("/all/save", response_model=SearchSaveResponse)
async def search_all_and_save_api(
    request: SearchSaveRequest,
    session: Session = Depends(get_session),
) -> SearchSaveResponse:
    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="query must not be empty")

    limit = clamp_limit(request.limit)
    results = await search_all_sources(query=query, limit=limit)
    if not results:
        return SearchSaveResponse(
            query=query,
            inserted_count=0,
            skipped_count=0,
            papers=[],
        )

    inserted_count = 0
    skipped_count = 0
    saved_papers: list[Paper] = []

    for result in results:
        existing_paper = find_existing_paper(session, result)
        if existing_paper:
            skipped_count += 1
            if update_existing_paper(existing_paper, result):
                session.add(existing_paper)
            saved_papers.append(existing_paper)
            continue

        paper = create_paper_from_search_result(result)
        session.add(paper)
        saved_papers.append(paper)
        inserted_count += 1

    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail="Paper DOI already exists") from exc

    for paper in saved_papers:
        session.refresh(paper)

    return SearchSaveResponse(
        query=query,
        inserted_count=inserted_count,
        skipped_count=skipped_count,
        papers=saved_papers,
    )
