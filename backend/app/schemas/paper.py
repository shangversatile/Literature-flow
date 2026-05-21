from datetime import datetime

from sqlmodel import SQLModel


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
