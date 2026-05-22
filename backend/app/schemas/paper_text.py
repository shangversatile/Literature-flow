from datetime import datetime

from sqlmodel import SQLModel


class PaperTextRead(SQLModel):
    id: int
    paper_id: int
    full_text: str
    page_count: int
    extracted_pages: int
    char_count: int
    created_at: datetime
    updated_at: datetime


class PaperChunkRead(SQLModel):
    id: int
    paper_id: int
    chunk_index: int
    text: str
    char_count: int
    token_estimate: int
    page_start: int | None
    page_end: int | None
    section_title: str | None
    embedding_status: str
    created_at: datetime


class ParsePdfResponse(SQLModel):
    paper_id: int
    page_count: int
    extracted_pages: int
    char_count: int
    chunk_count: int
    status: str
