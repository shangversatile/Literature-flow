from pydantic import BaseModel


class RefreshEnrichmentResponse(BaseModel):
    paper_id: int
    title: str
    old_venue: str | None
    venue_normalized: str | None
    rank_value: str | None
    rank_source: str | None
    final_score: float | None
    message: str


class RefreshEnrichmentBatchRequest(BaseModel):
    paper_ids: list[int] | None = None


class RefreshEnrichmentBatchResponse(BaseModel):
    total: int
    succeeded: int
    failed: int
    results: list[RefreshEnrichmentResponse]
