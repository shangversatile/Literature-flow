from datetime import datetime

from sqlmodel import Field, SQLModel


class PaperBase(SQLModel):
    title: str
    doi: str | None = None
    year: int | None = None
    venue: str | None = None
    abstract: str | None = None
    citation_count: int = 0
    pdf_url: str | None = None
    local_pdf_path: str | None = None
    status: str = "DISCOVERED"


class PaperCreate(PaperBase):
    pass


class PaperRead(PaperBase):
    id: int
    normalized_title: str | None
    created_at: datetime
    updated_at: datetime
    authors: list[str] = Field(default_factory=list)


class PaperEnrichedRead(PaperRead):
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


class PaperUpdate(SQLModel):
    title: str | None = None
    doi: str | None = None
    year: int | None = None
    venue: str | None = None
    abstract: str | None = None
    citation_count: int | None = None
    pdf_url: str | None = None
    local_pdf_path: str | None = None
    status: str | None = None
