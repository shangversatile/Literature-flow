from fastapi import APIRouter, HTTPException

from app.schemas.search_campaign import (
    RunCampaignRequest,
    RunCampaignResponse,
    SearchCampaign,
)
from app.services.search.campaigns import (
    clamp_limit_per_query,
    get_campaign,
    list_campaigns,
    run_campaign_queries,
)


router = APIRouter(prefix="/search/campaigns", tags=["search-campaigns"])


@router.get("", response_model=list[SearchCampaign])
def read_search_campaigns() -> list[SearchCampaign]:
    return list_campaigns()


@router.post("/run", response_model=RunCampaignResponse)
async def run_search_campaign(request: RunCampaignRequest) -> RunCampaignResponse:
    campaign = get_campaign(request.campaign_name)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Search campaign not found")

    total_raw_results, results = await run_campaign_queries(
        campaign,
        clamp_limit_per_query(request.limit_per_query),
    )

    return RunCampaignResponse(
        campaign_name=campaign.name,
        total_raw_results=total_raw_results,
        total_unique_results=len(results),
        results=results,
    )
