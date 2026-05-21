import httpx

from app.schemas.search import PaperSearchResult


OPENALEX_SEARCH_URL = "https://api.openalex.org/works"


class OpenAlexSearchError(Exception):
    pass


class OpenAlexRateLimitError(OpenAlexSearchError):
    pass


class OpenAlexTimeoutError(OpenAlexSearchError):
    pass


def clamp_limit(limit: int) -> int:
    if limit < 1:
        return 1
    if limit > 50:
        return 50
    return limit


def restore_abstract(inverted_index: dict | None) -> str | None:
    if not inverted_index:
        return None

    words_by_position: dict[int, str] = {}
    for word, positions in inverted_index.items():
        for position in positions:
            words_by_position[position] = word

    return " ".join(words_by_position[position] for position in sorted(words_by_position))


def get_primary_location(item: dict) -> dict:
    return item.get("primary_location") or {}


def get_pdf_url(item: dict) -> str | None:
    primary_location = get_primary_location(item)
    primary_pdf_url = primary_location.get("pdf_url")
    if primary_pdf_url:
        return primary_pdf_url

    best_oa_location = item.get("best_oa_location") or {}
    return best_oa_location.get("pdf_url")


def build_search_result(item: dict) -> PaperSearchResult:
    primary_location = get_primary_location(item)
    source = primary_location.get("source") or {}
    ids = item.get("ids") or {}
    doi = ids.get("doi")

    return PaperSearchResult(
        title=item.get("title") or "",
        abstract=restore_abstract(item.get("abstract_inverted_index")),
        year=item.get("publication_year"),
        venue=source.get("display_name"),
        doi=doi.removeprefix("https://doi.org/") if doi else None,
        citation_count=item.get("cited_by_count") or 0,
        authors=[
            authorship.get("author", {}).get("display_name")
            for authorship in item.get("authorships", [])
            if authorship.get("author", {}).get("display_name")
        ],
        url=item.get("doi") or item.get("id"),
        external_ids=ids,
        open_access_pdf_url=get_pdf_url(item),
        source="openalex",
    )


async def search_openalex(query: str, limit: int = 10) -> list[PaperSearchResult]:
    limit = clamp_limit(limit)
    params = {
        "search": query,
        "per-page": limit,
    }
    headers = {
        "Accept": "application/json",
        "User-Agent": "LitFlow/0.1",
    }

    async with httpx.AsyncClient(timeout=10.0, headers=headers) as client:
        try:
            response = await client.get(OPENALEX_SEARCH_URL, params=params)
        except httpx.TimeoutException as exc:
            raise OpenAlexTimeoutError(
                "OpenAlex request timed out. Please try again later."
            ) from exc
        except httpx.HTTPError as exc:
            raise OpenAlexSearchError(
                "OpenAlex request failed. Please try again later."
            ) from exc

    if response.status_code == 429:
        raise OpenAlexRateLimitError(
            "OpenAlex rate limit reached. Please try again later."
        )
    if 500 <= response.status_code < 600:
        raise OpenAlexSearchError(
            f"OpenAlex service returned an error: {response.status_code}."
        )

    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise OpenAlexSearchError(
            f"OpenAlex API returned an error: {response.status_code}."
        ) from exc

    payload = response.json()
    items = payload.get("results") or []
    return [build_search_result(item) for item in items]
