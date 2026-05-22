from datetime import datetime

from sqlmodel import Field, SQLModel


class PaperAsset(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    paper_id: int = Field(index=True, foreign_key="paper.id")
    asset_type: str = Field(index=True)
    asset_index: int
    page_number: int | None = Field(default=None, index=True)
    caption: str | None = None
    local_path: str | None = None
    text_content: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
