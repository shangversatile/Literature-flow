from sqlmodel import Field, SQLModel


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
