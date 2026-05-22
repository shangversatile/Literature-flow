from datetime import datetime

from pydantic import BaseModel


class PaperAssetRead(BaseModel):
    id: int
    paper_id: int
    asset_type: str
    asset_index: int
    page_number: int | None
    caption: str | None
    local_path: str | None
    text_content: str | None
    created_at: datetime


class ExtractAssetsResponse(BaseModel):
    paper_id: int
    asset_count: int
    page_image_count: int
    figure_caption_count: int
    table_caption_count: int
    status: str
