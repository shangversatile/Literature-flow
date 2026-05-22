from datetime import datetime

from sqlmodel import Field, SQLModel


class Author(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    normalized_name: str = Field(index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PaperAuthor(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    paper_id: int = Field(index=True, foreign_key="paper.id")
    author_id: int = Field(index=True, foreign_key="author.id")
    author_order: int
