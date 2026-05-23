from pydantic import BaseModel, Field


class LibraryAskRequest(BaseModel):
    question: str
    mode: str = "mock"
    top_k: int = 10
    topic: str | None = None


class LibraryEvidenceChunk(BaseModel):
    paper_id: int
    paper_title: str
    paper_year: int | None = None
    paper_venue: str | None = None
    chunk_index: int
    text: str
    score: float
    page_start: int | None = None
    page_end: int | None = None
    section_title: str | None = None
    matched_terms: list[str] = Field(default_factory=list)
    retrieval_method: str = "library_bm25_like_v3"


class LibraryAskResponse(BaseModel):
    question: str
    mode: str
    topic: str | None = None
    answer: str
    evidence_chunks: list[LibraryEvidenceChunk] = Field(default_factory=list)
    evidence_count: int
