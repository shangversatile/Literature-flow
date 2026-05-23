from pydantic import BaseModel

from app.schemas.workflow import ProcessStepResult


class BatchProcessRequest(BaseModel):
    paper_ids: list[int]
    resolve_pdf: bool = True
    download_pdf: bool = True
    parse_pdf: bool = True
    extract: bool = True
    extract_assets: bool = False
    save_workspace: bool = False
    extract_mode: str = "openai"
    user_topic: str | None = None
    max_chunks: int = 8


class BatchPaperResult(BaseModel):
    paper_id: int
    title: str | None
    status: str
    final_status: str | None
    steps: list[ProcessStepResult]
    error: str | None = None


class BatchProcessResponse(BaseModel):
    total: int
    succeeded: int
    failed: int
    skipped: int
    results: list[BatchPaperResult]
