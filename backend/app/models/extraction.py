from datetime import datetime

from sqlmodel import Field, SQLModel


class Extraction(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    paper_id: int = Field(index=True, foreign_key="paper.id")
    model_name: str
    prompt_version: str = "litflow_extraction_v1"
    extracted_json: str
    raw_llm_output: str | None = None
    human_edited: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
