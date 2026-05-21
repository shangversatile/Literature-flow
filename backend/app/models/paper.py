from datetime import datetime

from sqlmodel import Field, SQLModel


class Paper(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    normalized_title: str | None = Field(default=None, index=True)
    doi: str | None = Field(default=None, unique=True, index=True)
    year: int | None = None
    venue: str | None = None
    abstract: str | None = None
    citation_count: int = 0
    pdf_url: str | None = None
    local_pdf_path: str | None = None
    status: str = "DISCOVERED"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
