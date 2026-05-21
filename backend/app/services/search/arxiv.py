from urllib.parse import urlparse
import xml.etree.ElementTree as ET

import httpx

from app.schemas.search import PaperSearchResult


ARXIV_SEARCH_URL = "https://export.arxiv.org/api/query"
ATOM_NS = "{http://www.w3.org/2005/Atom}"
ARXIV_NS = "{http://arxiv.org/schemas/atom}"


class ArxivSearchError(Exception):
    pass


class ArxivTimeoutError(ArxivSearchError):
    pass


class ArxivParseError(ArxivSearchError):
    pass


def clamp_limit(limit: int) -> int:
    if limit < 1:
        return 1
    if limit > 50:
        return 50
    return limit


def clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    return " ".join(value.split())


def child_text(element: ET.Element, tag: str) -> str | None:
    child = element.find(tag)
    if child is None:
        return None
    return clean_text(child.text)


def extract_year(published: str | None) -> int | None:
    if not published or len(published) < 4:
        return None
    try:
        return int(published[:4])
    except ValueError:
        return None


def extract_arxiv_ids(entry_id: str | None) -> dict:
    if not entry_id:
        return {}

    path = urlparse(entry_id).path
    raw_id = path.removeprefix("/abs/")
    if not raw_id:
        return {}

    arxiv_id = raw_id
    version = None
    if "v" in raw_id:
        possible_id, possible_version = raw_id.rsplit("v", 1)
        if possible_version.isdigit():
            arxiv_id = possible_id
            version = f"v{possible_version}"

    external_ids = {"ArXiv": arxiv_id}
    if version:
        external_ids["ArXivVersion"] = version
    return external_ids


def extract_pdf_url(entry: ET.Element, arxiv_id: str | None) -> str | None:
    for link in entry.findall(f"{ATOM_NS}link"):
        if (
            link.attrib.get("rel") == "related"
            and link.attrib.get("type") == "application/pdf"
            and link.attrib.get("href")
        ):
            return link.attrib["href"]

    if arxiv_id:
        return f"https://arxiv.org/pdf/{arxiv_id}"
    return None


def build_search_result(entry: ET.Element) -> PaperSearchResult:
    entry_id = child_text(entry, f"{ATOM_NS}id")
    external_ids = extract_arxiv_ids(entry_id)
    arxiv_id = external_ids.get("ArXiv")
    doi = child_text(entry, f"{ARXIV_NS}doi")

    return PaperSearchResult(
        title=child_text(entry, f"{ATOM_NS}title") or "",
        abstract=child_text(entry, f"{ATOM_NS}summary"),
        year=extract_year(child_text(entry, f"{ATOM_NS}published")),
        venue="arXiv",
        doi=doi,
        citation_count=0,
        authors=[
            name
            for author in entry.findall(f"{ATOM_NS}author")
            if (name := child_text(author, f"{ATOM_NS}name"))
        ],
        url=entry_id,
        external_ids=external_ids,
        open_access_pdf_url=extract_pdf_url(entry, arxiv_id),
        source="arxiv",
    )


async def search_arxiv(query: str, limit: int = 10) -> list[PaperSearchResult]:
    limit = clamp_limit(limit)
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": limit,
    }
    headers = {
        "Accept": "application/atom+xml",
        "User-Agent": "LitFlow/0.1",
    }

    async with httpx.AsyncClient(timeout=10.0, headers=headers) as client:
        try:
            response = await client.get(ARXIV_SEARCH_URL, params=params)
        except httpx.TimeoutException as exc:
            raise ArxivTimeoutError(
                "arXiv request timed out. Please try again later."
            ) from exc
        except httpx.HTTPError as exc:
            raise ArxivSearchError(
                "arXiv request failed. Please try again later."
            ) from exc

    if response.status_code != 200:
        raise ArxivSearchError(f"arXiv API returned an error: {response.status_code}.")

    try:
        root = ET.fromstring(response.text)
    except ET.ParseError as exc:
        raise ArxivParseError("arXiv returned invalid XML.") from exc

    entries = root.findall(f"{ATOM_NS}entry")
    return [build_search_result(entry) for entry in entries]
