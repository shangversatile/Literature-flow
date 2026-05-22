import json

from app.models.extraction import Extraction
from app.models.paper import Paper
from app.models.paper_asset import PaperAsset
from app.schemas.paper import PaperEnrichedRead


def yaml_string(value: str | None) -> str:
    if value is None:
        return '""'
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def markdown_value(value: object) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, list):
        if not value:
            return ""
        return "\n".join(f"- {item}" for item in value)
    return str(value)


def extraction_data(latest_extraction: Extraction | None) -> dict | None:
    if latest_extraction is None:
        return None

    try:
        data = json.loads(latest_extraction.extracted_json)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def section(title: str, value: object) -> str:
    content = markdown_value(value).strip()
    return f"### {title}\n\n{content or 'No extraction available yet.'}\n"


def yaml_list(values: list[str]) -> list[str]:
    if not values:
        return ["authors: []"]
    lines = ["authors:"]
    lines.extend(f"  - {yaml_string(value)}" for value in values)
    return lines


def markdown_asset_path(asset: PaperAsset) -> str:
    path = asset.local_path or ""
    normalized = path.replace("\\", "/")
    if normalized.startswith("storage/assets/"):
        return "../assets/" + normalized.removeprefix("storage/assets/")
    return normalized


def figures_and_tables_section(assets: list[PaperAsset]) -> list[str]:
    page_images = [asset for asset in assets if asset.asset_type == "page_image"]
    figure_captions = [
        asset for asset in assets if asset.asset_type == "figure_caption"
    ]
    table_captions = [asset for asset in assets if asset.asset_type == "table_caption"]
    table_texts = [asset for asset in assets if asset.asset_type == "table_text"]

    lines = [
        "## Figures and Tables",
        "",
        "### Page Images",
        "",
    ]

    if page_images:
        for asset in page_images:
            page_label = asset.page_number or asset.asset_index
            lines.append(f"![Page {page_label}]({markdown_asset_path(asset)})")
            lines.append("")
    else:
        lines.extend(["No page images extracted yet.", ""])

    lines.extend(["### Figure Captions", ""])
    if figure_captions:
        for asset in figure_captions:
            lines.append(f"- Page {asset.page_number or '-'}: {asset.caption or asset.text_content or ''}")
    else:
        lines.append("No figure captions extracted yet.")
    lines.append("")

    lines.extend(["### Table Captions and Raw Table Text", ""])
    if table_captions:
        for asset in table_captions:
            lines.append(f"- Page {asset.page_number or '-'}: {asset.caption or asset.text_content or ''}")
    else:
        lines.append("No table captions extracted yet.")
    lines.append("")

    if table_texts:
        for asset in table_texts:
            lines.extend(
                [
                    f"Page {asset.page_number or '-'} raw table text:",
                    "",
                    "```text",
                    asset.text_content or "",
                    "```",
                    "",
                ]
            )
    else:
        lines.extend(["No raw table text extracted yet.", ""])

    return lines


def export_paper_to_markdown(
    paper: Paper,
    latest_extraction: Extraction | None,
    enriched: PaperEnrichedRead | None = None,
    assets: list[PaperAsset] | None = None,
    authors: list[str] | None = None,
) -> str:
    data = extraction_data(latest_extraction)
    title = paper.title
    author_names = authors or (enriched.authors if enriched else []) or []
    author_text = ", ".join(author_names) if author_names else "Unknown"

    venue_normalized = enriched.venue_normalized if enriched else None
    publication_status = enriched.publication_status if enriched else None
    rank_source = enriched.rank_source if enriched else None
    rank_value = enriched.rank_value if enriched else None

    lines = [
        "---",
        f"title: {yaml_string(title)}",
        *yaml_list(author_names),
        f"year: {paper.year if paper.year is not None else ''}",
        f"venue: {yaml_string(paper.venue)}",
        f"venue_normalized: {yaml_string(venue_normalized)}",
        f"publication_status: {yaml_string(publication_status)}",
        f"rank_source: {yaml_string(rank_source)}",
        f"rank_value: {yaml_string(rank_value)}",
        f"doi: {yaml_string(paper.doi)}",
        f"citation_count: {paper.citation_count}",
        f"pdf_url: {yaml_string(paper.pdf_url)}",
        f"local_pdf_path: {yaml_string(paper.local_pdf_path)}",
        f"status: {yaml_string(paper.status)}",
        "---",
        "",
        f"# {title}",
        "",
        "## Metadata",
        f"- Authors: {author_text}",
        f"- Year: {paper.year or ''}",
        f"- Venue: {paper.venue or ''}",
        f"- DOI: {paper.doi or ''}",
        f"- Citation Count: {paper.citation_count}",
        f"- Rank: {rank_value or ''}",
        f"- PDF: {paper.pdf_url or paper.local_pdf_path or ''}",
        "",
        "## Abstract",
        "",
        paper.abstract or "",
        "",
        "## LLM Structured Summary",
        "",
    ]

    if data is None:
        lines.extend(
            [
                "No extraction available yet.",
                "",
                "### Research Background",
                "",
                "No extraction available yet.",
                "",
                "### Research Problem",
                "",
                "No extraction available yet.",
                "",
                "### Methodology",
                "",
                "No extraction available yet.",
                "",
                "### Main Contributions",
                "",
                "No extraction available yet.",
                "",
                "### Experiments / Evaluation",
                "",
                "No extraction available yet.",
                "",
                "### Main Conclusions",
                "",
                "No extraction available yet.",
                "",
                "### Limitations",
                "",
                "No extraction available yet.",
                "",
                "### Keywords",
                "",
                "No extraction available yet.",
                "",
                "### Relevance to My Topic",
                "",
                "No extraction available yet.",
                "",
                "### Possible Follow-up Questions",
                "",
                "No extraction available yet.",
                "",
            ]
        )
    else:
        lines.extend(
            [
                section("Research Background", data.get("research_background")),
                section("Research Problem", data.get("research_problem")),
                section("Methodology", data.get("methodology")),
                section("Main Contributions", data.get("main_contributions")),
                section("Experiments / Evaluation", data.get("experiments_or_evaluation")),
                section("Main Conclusions", data.get("main_conclusions")),
                section("Limitations", data.get("limitations")),
                section("Keywords", data.get("keywords")),
                section("Relevance to My Topic", data.get("relevance_to_user_topic")),
                section(
                    "Possible Follow-up Questions",
                    data.get("possible_followup_questions"),
                ),
            ]
        )

    evidence = data.get("evidence_chunk_indices") if data else None
    evidence_text = markdown_value(evidence).strip() if evidence else ""
    lines.extend(
        [
            "## My Notes",
            "",
            "",
            "## Evidence Chunks",
            "",
            evidence_text or "No evidence chunks available yet.",
            "",
        ]
    )

    lines.extend(figures_and_tables_section(assets or []))

    return "\n".join(lines)
