from datetime import datetime

from sqlmodel import Field, SQLModel


class PaperText(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    paper_id: int = Field(index=True, foreign_key="paper.id")
    full_text: str
    page_count: int
    extracted_pages: int
    char_count: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
