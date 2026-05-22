from pydantic import BaseModel


class WorkspaceSaveResponse(BaseModel):
    paper_id: int
    workspace_path: str
    pdf_path: str | None = None
    markdown_path: str
    bibtex_path: str
    metadata_path: str
    assets_path: str | None = None


class WorkspaceInfoResponse(WorkspaceSaveResponse):
    exists: bool
    pdf_exists: bool
    markdown_exists: bool
    bibtex_exists: bool
    metadata_exists: bool
    assets_exists: bool
