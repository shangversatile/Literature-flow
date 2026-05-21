from urllib.parse import urlparse

from app.models.paper import Paper
from app.services.download.unpaywall import get_unpaywall_email, get_unpaywall_pdf_url


def looks_like_pdf_url(url: str | None) -> bool:
    if not url:
        return False
    path = urlparse(url).path.lower()
    return path.endswith(".pdf") or "/pdf/" in path


def arxiv_abs_to_pdf_url(url: str | None) -> str | None:
    if not url:
        return None

    parsed = urlparse(url)
    if parsed.netloc not in {"arxiv.org", "www.arxiv.org"}:
        return None
    if not parsed.path.startswith("/abs/"):
        return None

    arxiv_id = parsed.path.removeprefix("/abs/")
    if not arxiv_id:
        return None
    return f"https://arxiv.org/pdf/{arxiv_id}"


async def resolve_pdf_url(paper: Paper) -> str | None:
    if looks_like_pdf_url(paper.pdf_url):
        return paper.pdf_url

    arxiv_pdf_url = arxiv_abs_to_pdf_url(paper.pdf_url)
    if arxiv_pdf_url:
        return arxiv_pdf_url

    if paper.doi:
        email = get_unpaywall_email()
        return await get_unpaywall_pdf_url(paper.doi, email)

    return None
