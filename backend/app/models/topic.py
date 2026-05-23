from datetime import datetime

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class ResearchTopic(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    normalized_name: str = Field(index=True, unique=True)
    description: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PaperTopic(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("paper_id", "topic_id"),)

    id: int | None = Field(default=None, primary_key=True)
    paper_id: int = Field(foreign_key="paper.id", index=True)
    topic_id: int = Field(foreign_key="researchtopic.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
