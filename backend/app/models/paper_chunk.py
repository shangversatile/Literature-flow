from datetime import datetime

from sqlmodel import Field, SQLModel


class PaperChunk(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    paper_id: int = Field(index=True, foreign_key="paper.id")
    chunk_index: int
    text: str
    char_count: int
    token_estimate: int
    page_start: int | None = None
    page_end: int | None = None
    section_title: str | None = None
    embedding_status: str = "NOT_EMBEDDED"
    created_at: datetime = Field(default_factory=datetime.utcnow)
