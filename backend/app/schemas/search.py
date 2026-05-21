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
    relevance_score: float | None = None
    quality_score: float | None = None
    sources: list[str] = Field(default_factory=list)


class SearchSaveRequest(SQLModel):
    query: str
    limit: int = 10


class SearchSaveResponse(SQLModel):
    query: str
    inserted_count: int
    skipped_count: int
    papers: list[PaperRead]
