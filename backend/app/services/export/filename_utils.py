import re

from app.models.paper import Paper
from app.schemas.paper import PaperEnrichedRead


def safe_slug(text: str | None, fallback: str) -> str:
    if not text:
        return fallback

    tokens = re.findall(r"[a-z0-9]+", text.lower())
    if not tokens:
        return fallback
    slug = "-".join(tokens)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or fallback


def short_title_slug(title: str | None) -> str:
    if not title:
        return "untitled"

    tokens = re.findall(r"[a-z0-9]+", title.lower())
    if tokens:
        return "-".join(tokens[:8])[:60].strip("-") or "untitled"
    return safe_slug(title, "untitled")[:60].strip("-") or "untitled"


def rank_slug(rank: str | None) -> str:
    if not rank or rank == "Unknown":
        return "unknown-rank"
    if rank == "A*":
        return "a-star"
    return safe_slug(rank, "unknown-rank")


def build_export_filename(
    paper: Paper,
    enriched: PaperEnrichedRead | None = None,
    extension: str = "md",
) -> str:
    year = str(paper.year) if paper.year else "unknown-year"
    title = short_title_slug(paper.title)
    venue_value = (enriched.venue_normalized if enriched else None) or paper.venue
    venue = safe_slug(venue_value, "unknown-venue")
    rank_value = (enriched.rank_value or enriched.venue_rank) if enriched else None
    rank = rank_slug(rank_value)
    paper_id = paper.id if paper.id is not None else "unknown"
    safe_extension = safe_slug(extension.lstrip("."), "md")
    filename = f"{year}-{title}-{venue}-{rank}-id{paper_id}.{safe_extension}"
    return re.sub(r"-+", "-", filename).lower()
