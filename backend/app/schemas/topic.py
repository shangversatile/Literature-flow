from datetime import datetime

from sqlmodel import SQLModel


class ResearchTopicRead(SQLModel):
    id: int
    name: str
    normalized_name: str
    description: str | None = None
    created_at: datetime


class ResearchTopicCreate(SQLModel):
    name: str
    description: str | None = None


class PaperTopicUpdate(SQLModel):
    topic_names: list[str]


class PaperTopicsResponse(SQLModel):
    paper_id: int
    topics: list[ResearchTopicRead]


class PaperTopicName(SQLModel):
    topic_name: str
