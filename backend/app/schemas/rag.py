from pydantic import BaseModel, Field


class AskPaperRequest(BaseModel):
    question: str
    mode: str = "mock"
    top_k: int = 5


class EvidenceChunk(BaseModel):
    chunk_index: int
    text: str
    score: float
    page_start: int | None = None
    page_end: int | None = None
    section_title: str | None = None


class AskPaperResponse(BaseModel):
    paper_id: int
    question: str
    mode: str
    answer: str
    evidence_chunks: list[EvidenceChunk] = Field(default_factory=list)
    evidence_chunk_indices: list[int] = Field(default_factory=list)
