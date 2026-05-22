from sqlmodel import Field, SQLModel

from app.schemas.paper import PaperRead


class PaperSearchResult(SQLModel):
    title: str
    abstract: str | None = None
    year: int | None = None
    venue: str | None = None
    doi: str | None = None
    citation_count: int = 0
    authors: list[str] = Field(default_factory=list)
    url: str | None = None
    external_ids: dict = Field(default_factory=dict)
    open_access_pdf_url: str | None = None
    source: str = "semantic_scholar"
    venue_normalized: str | None = None
    venue_type: str | None = None
    publication_type: str | None = None
    publication_status: str | None = None
    rank_source: str | None = None
    rank_value: str | None = None
    rank_note: str | None = None
    venue_rank: str | None = None
    venue_rank_source: str | None = None
    venue_rank_note: str | None = None
    relevance_score: float | None = None
    authority_score: float | None = None
    frontier_score: float | None = None
    accessibility_score: float | None = None
    final_score: float | None = None
    quality_score: float | None = None
    sources: list[str] = Field(default_factory=list)


class SearchSaveRequest(SQLModel):
    query: str
    limit: int = 10


class SearchSaveSelectedRequest(SQLModel):
    query: str | None = None
    papers: list[PaperSearchResult] = Field(default_factory=list)


class SearchSaveResponse(SQLModel):
    query: str
    inserted_count: int
    skipped_count: int
    papers: list[PaperRead]
