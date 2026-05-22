from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class LiteratureExtraction(BaseModel):
    title: str | None = None
    authors: list[str] = Field(default_factory=list)
    venue: str | None = None
    year: int | None = None
    research_background: str
    research_problem: str
    methodology: str
    main_contributions: list[str] = Field(default_factory=list)
    experiments_or_evaluation: str
    main_conclusions: str
    limitations: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    relevance_to_user_topic: str
    possible_followup_questions: list[str] = Field(default_factory=list)
    evidence_chunk_indices: list[int] = Field(default_factory=list)


class ExtractionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    paper_id: int
    model_name: str
    prompt_version: str
    extracted_json: str
    raw_llm_output: str | None
    human_edited: bool
    created_at: datetime


class ExtractRequest(BaseModel):
    mode: Literal["mock", "openai"] = "mock"
    user_topic: str | None = None
    max_chunks: int = Field(default=8, ge=1)


class ExtractResponse(BaseModel):
    paper_id: int
    extraction_id: int
    model_name: str
    prompt_version: str
    data: LiteratureExtraction
