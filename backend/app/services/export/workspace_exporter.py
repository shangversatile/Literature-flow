import json
import re
import shutil
from pathlib import Path

from app.models.paper import Paper
from app.schemas.paper import PaperEnrichedRead


PROJECT_ROOT = Path(__file__).resolve().parents[4]
LIBRARY_STORAGE_DIR = PROJECT_ROOT / "storage" / "library"
ASSET_STORAGE_DIR = PROJECT_ROOT / "storage" / "assets"


def safe_slug(value: str | None, fallback: str, max_length: int = 80) -> str:
    if not value:
        return fallback
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower())
    slug = re.sub(r"-+", "-", slug).strip("-")
    if not slug:
        return fallback
    return slug[:max_length].strip("-") or fallback


def build_workspace_dir_name(
    paper: Paper,
    enriched: PaperEnrichedRead | None = None,
) -> str:
    del enriched
    paper_id = paper.id if paper.id is not None else "unknown"
    year = str(paper.year) if paper.year else "unknown-year"
    title = safe_slug(paper.title, "untitled", 60)
    return f"{paper_id}-{year}-{title}"


def relative_storage_path(path: Path | None) -> str | None:
    if path is None:
        return None
    return path.relative_to(PROJECT_ROOT).as_posix()


def local_pdf_source(paper: Paper) -> Path | None:
    if not paper.local_pdf_path:
        return None
    source = Path(paper.local_pdf_path)
    if not source.is_absolute():
        source = PROJECT_ROOT / source
    return source if source.exists() else None


def workspace_paths(
    paper: Paper,
    enriched: PaperEnrichedRead | None = None,
) -> dict[str, Path | None]:
    workspace_dir = LIBRARY_STORAGE_DIR / build_workspace_dir_name(paper, enriched)
    return {
        "workspace_path": workspace_dir,
        "pdf_path": workspace_dir / "paper.pdf",
        "markdown_path": workspace_dir / "note.md",
        "bibtex_path": workspace_dir / "citation.bib",
        "metadata_path": workspace_dir / "metadata.json",
        "assets_path": workspace_dir / "assets",
    }


def workspace_response(
    paper: Paper,
    enriched: PaperEnrichedRead | None = None,
) -> dict:
    paths = workspace_paths(paper, enriched)
    workspace_path = paths["workspace_path"]
    pdf_path = paths["pdf_path"]
    markdown_path = paths["markdown_path"]
    bibtex_path = paths["bibtex_path"]
    metadata_path = paths["metadata_path"]
    assets_path = paths["assets_path"]

    return {
        "paper_id": paper.id,
        "workspace_path": relative_storage_path(workspace_path),
        "pdf_path": relative_storage_path(pdf_path),
        "markdown_path": relative_storage_path(markdown_path),
        "bibtex_path": relative_storage_path(bibtex_path),
        "metadata_path": relative_storage_path(metadata_path),
        "assets_path": relative_storage_path(assets_path),
    }


def workspace_info(
    paper: Paper,
    enriched: PaperEnrichedRead | None = None,
) -> dict:
    response = workspace_response(paper, enriched)
    workspace_path = PROJECT_ROOT / response["workspace_path"]
    markdown_path = PROJECT_ROOT / response["markdown_path"]
    bibtex_path = PROJECT_ROOT / response["bibtex_path"]
    metadata_path = PROJECT_ROOT / response["metadata_path"]
    pdf_path = PROJECT_ROOT / response["pdf_path"] if response["pdf_path"] else None
    assets_path = PROJECT_ROOT / response["assets_path"] if response["assets_path"] else None

    response.update(
        {
            "exists": workspace_path.exists(),
            "pdf_exists": pdf_path.exists() if pdf_path else False,
            "markdown_exists": markdown_path.exists(),
            "bibtex_exists": bibtex_path.exists(),
            "metadata_exists": metadata_path.exists(),
            "assets_exists": assets_path.exists() if assets_path else False,
        }
    )
    return response


def metadata_payload(
    paper: Paper,
    enriched: PaperEnrichedRead | None,
    response: dict,
) -> dict:
    return {
        "paper": {
            "id": paper.id,
            "title": paper.title,
            "authors": enriched.authors if enriched else [],
            "doi": paper.doi,
            "year": paper.year,
            "venue": paper.venue,
            "abstract": paper.abstract,
            "citation_count": paper.citation_count,
            "pdf_url": paper.pdf_url,
            "local_pdf_path": paper.local_pdf_path,
            "status": paper.status,
        },
        "rank": {
            "venue_normalized": enriched.venue_normalized if enriched else None,
            "publication_status": enriched.publication_status if enriched else None,
            "rank_source": enriched.rank_source if enriched else None,
            "rank_value": enriched.rank_value if enriched else None,
            "rank_note": enriched.rank_note if enriched else None,
        },
        "paths": response,
    }


def save_paper_workspace(
    paper: Paper,
    markdown_text: str,
    bibtex_text: str,
    enriched: PaperEnrichedRead | None = None,
) -> dict:
    paths = workspace_paths(paper, enriched)
    workspace_dir = paths["workspace_path"]
    pdf_path = paths["pdf_path"]
    markdown_path = paths["markdown_path"]
    bibtex_path = paths["bibtex_path"]
    metadata_path = paths["metadata_path"]
    assets_path = paths["assets_path"]

    workspace_dir.mkdir(parents=True, exist_ok=True)

    pdf_source = local_pdf_source(paper)
    if pdf_source and pdf_path:
        shutil.copy2(pdf_source, pdf_path)

    markdown_path.write_text(markdown_text, encoding="utf-8")
    bibtex_path.write_text(bibtex_text, encoding="utf-8")

    assets_source = ASSET_STORAGE_DIR / str(paper.id)
    if assets_source.exists() and assets_path:
        shutil.copytree(assets_source, assets_path, dirs_exist_ok=True)

    response = workspace_response(paper, enriched)
    metadata_path.write_text(
        json.dumps(metadata_payload(paper, enriched, response), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return workspace_response(paper, enriched)
