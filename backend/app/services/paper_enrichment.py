import re

from app.models.paper import Paper
from app.schemas.paper import PaperEnrichedRead
from app.schemas.search import PaperSearchResult
from app.services.search.scoring import score_paper_result


def extract_arxiv_id(value: str | None) -> str | None:
    if not value:
        return None

    patterns = [
        r"arxiv\.org/(?:abs|pdf)/([^/?#]+)",
        r"arxiv[:./\s]+([0-9]{4}\.[0-9]{4,5}(?:v[0-9]+)?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, value, flags=re.IGNORECASE)
        if match:
            return match.group(1).removesuffix(".pdf")
    return None


def infer_sources(paper: Paper) -> list[str]:
    sources: list[str] = []
    if paper.pdf_url and "arxiv.org" in paper.pdf_url.lower():
        sources.append("arxiv")
    if paper.doi:
        sources.append("doi")
    return sources


def build_external_ids(paper: Paper) -> dict[str, str]:
    external_ids: dict[str, str] = {}
    if paper.doi:
        external_ids["DOI"] = paper.doi

    arxiv_id = extract_arxiv_id(paper.pdf_url) or extract_arxiv_id(paper.doi)
    if arxiv_id:
        external_ids["ArXiv"] = arxiv_id
    return external_ids


def enrich_paper_for_display(
    paper: Paper,
    query: str | None = None,
    authors: list[str] | None = None,
    topics: list[str] | None = None,
) -> PaperEnrichedRead:
    sources = infer_sources(paper)
    search_result = PaperSearchResult(
        title=paper.title,
        abstract=paper.abstract,
        year=paper.year,
        venue=paper.venue,
        doi=paper.doi,
        citation_count=paper.citation_count,
        url=paper.pdf_url,
        external_ids=build_external_ids(paper),
        open_access_pdf_url=paper.pdf_url,
        source=sources[0] if sources else "database",
        sources=sources,
    )
    score_paper_result(search_result, query or paper.title or "")

    data = paper.model_dump()
    data.update(
        {
            "venue_normalized": search_result.venue_normalized,
            "venue_type": search_result.venue_type,
            "publication_type": search_result.publication_type,
            "publication_status": search_result.publication_status,
            "rank_source": search_result.rank_source,
            "rank_value": search_result.rank_value,
            "rank_note": search_result.rank_note,
            "venue_rank": search_result.venue_rank,
            "venue_rank_source": search_result.venue_rank_source,
            "venue_rank_note": search_result.venue_rank_note,
            "relevance_score": search_result.relevance_score,
            "authority_score": search_result.authority_score,
            "foundation_score": search_result.foundation_score,
            "implementation_score": search_result.implementation_score,
            "survey_value_score": search_result.survey_value_score,
            "frontier_score": search_result.frontier_score,
            "accessibility_score": search_result.accessibility_score,
            "final_score": search_result.final_score,
            "quality_score": search_result.quality_score,
            "sources": search_result.sources,
            "authors": authors or [],
            "topics": topics or [],
        }
    )
    return PaperEnrichedRead.model_validate(data)
