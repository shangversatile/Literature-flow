import re

from app.models.paper import Paper
from app.services.search.venue_classifier import classify_publication_venue


def clean_bibtex_value(value: str | None) -> str:
    if not value:
        return ""
    return value.replace("{", "\\{").replace("}", "\\}").strip()


def short_title_key(title: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", title.lower())[:5]
    return "".join(word.capitalize() for word in words)


def bibtex_key(paper: Paper) -> str:
    if paper.id is None:
        return "litflowPaper"
    return f"litflow{paper.id}{short_title_key(paper.title)}"


def bibtex_entry_type(paper: Paper) -> str:
    classification = classify_publication_venue(paper.venue)
    venue_type = classification["venue_type"]
    if venue_type == "conference":
        return "inproceedings"
    if venue_type == "journal":
        return "article"
    return "misc"


def export_paper_to_bibtex(paper: Paper) -> str:
    entry_type = bibtex_entry_type(paper)
    venue_field = "journal" if entry_type == "article" else "booktitle"
    if entry_type == "misc":
        venue_field = "howpublished"

    fields: list[tuple[str, str]] = [
        ("title", clean_bibtex_value(paper.title)),
        ("author", "Unknown"),
    ]
    if paper.year:
        fields.append(("year", str(paper.year)))
    if paper.venue:
        fields.append((venue_field, clean_bibtex_value(paper.venue)))
    if paper.doi:
        fields.append(("doi", clean_bibtex_value(paper.doi)))
    if paper.pdf_url:
        fields.append(("url", clean_bibtex_value(paper.pdf_url)))
    fields.append(("note", f"LitFlow status: {clean_bibtex_value(paper.status)}"))

    body = ",\n".join(f"  {key} = {{{value}}}" for key, value in fields if value)
    return f"@{entry_type}{{{bibtex_key(paper)},\n{body}\n}}\n"
