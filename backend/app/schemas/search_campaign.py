from pydantic import BaseModel

from app.schemas.search import PaperSearchResult


class SearchCampaign(BaseModel):
    name: str
    description: str
    queries: list[str]
    default_limit_per_query: int


class RunCampaignRequest(BaseModel):
    campaign_name: str
    limit_per_query: int = 8
    save: bool = False


class RunCampaignResponse(BaseModel):
    campaign_name: str
    total_raw_results: int
    total_unique_results: int
    results: list[PaperSearchResult]
