from pydantic import BaseModel


class ProcessPaperRequest(BaseModel):
    resolve_pdf: bool = True
    download_pdf: bool = True
    parse_pdf: bool = True
    extract: bool = True
    extract_assets: bool = False
    save_workspace: bool = False
    extract_mode: str = "mock"
    user_topic: str | None = None
    max_chunks: int = 8


class ProcessStepResult(BaseModel):
    name: str
    status: str
    message: str


class ProcessPaperResponse(BaseModel):
    paper_id: int
    steps: list[ProcessStepResult]
    final_status: str
