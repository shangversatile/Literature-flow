from datetime import datetime

from sqlmodel import Session, select

from app.models.extraction import Extraction
from app.models.paper import Paper
from app.models.paper_asset import PaperAsset
from app.models.paper_chunk import PaperChunk
from app.models.paper_text import PaperText
from app.schemas.workflow import (
    ProcessPaperRequest,
    ProcessPaperResponse,
    ProcessStepResult,
)
from app.services.authors import get_paper_author_names
from app.services.download.downloader import download_pdf
from app.services.download.resolver import resolve_pdf_url
from app.services.extraction.llm_extractor import (
    PROMPT_VERSION,
    extract_with_openai,
    mock_extract,
)
from app.services.extraction.pdf_assets import extract_pdf_assets
from app.services.extraction.pdf_parser import extract_text_from_pdf
from app.services.extraction.text_chunker import chunk_text_pages
from app.services.export.bibtex_exporter import export_paper_to_bibtex
from app.services.export.filename_utils import build_export_filename
from app.services.export.markdown_exporter import export_paper_to_markdown
from app.services.export.workspace_exporter import save_paper_workspace
from app.services.paper_enrichment import enrich_paper_for_display
from app.services.topics import get_paper_topics


def step_result(name: str, status: str, message: str) -> ProcessStepResult:
    return ProcessStepResult(name=name, status=status, message=message)


def skip_step(name: str, message: str) -> ProcessStepResult:
    return step_result(name, "skipped", message)


def fail_step(name: str, message: str) -> ProcessStepResult:
    return step_result(name, "failed", message)


def success_step(name: str, message: str) -> ProcessStepResult:
    return step_result(name, "success", message)


def get_paper_topic_names(session: Session, paper_id: int) -> list[str]:
    return [topic.name for topic in get_paper_topics(session, paper_id)]


def save_parsed_pdf(
    paper: Paper,
    paper_id: int,
    session: Session,
) -> tuple[int, int, int, int]:
    if not paper.local_pdf_path:
        raise ValueError("No local PDF found. Please download the PDF first.")

    try:
        parsed = extract_text_from_pdf(paper.local_pdf_path)
    except FileNotFoundError as exc:
        raise ValueError(str(exc)) from exc

    full_text = parsed["full_text"].strip()
    if not full_text:
        raise ValueError(
            parsed.get("error") or "No extractable text found. The PDF may be scanned."
        )

    old_texts = session.exec(
        select(PaperText).where(PaperText.paper_id == paper_id)
    ).all()
    for old_text in old_texts:
        session.delete(old_text)

    old_chunks = session.exec(
        select(PaperChunk).where(PaperChunk.paper_id == paper_id)
    ).all()
    for old_chunk in old_chunks:
        session.delete(old_chunk)

    paper_text = PaperText(
        paper_id=paper_id,
        full_text=full_text,
        page_count=parsed["page_count"],
        extracted_pages=parsed["extracted_pages"],
        char_count=len(full_text),
    )
    session.add(paper_text)

    chunk_data = chunk_text_pages(parsed["pages"])
    for chunk in chunk_data:
        session.add(PaperChunk(paper_id=paper_id, **chunk))

    paper.status = "TEXT_EXTRACTED"
    paper.updated_at = datetime.utcnow()
    session.add(paper)

    return parsed["page_count"], parsed["extracted_pages"], len(full_text), len(chunk_data)


def save_extracted_assets(
    paper: Paper,
    paper_id: int,
    session: Session,
) -> int:
    if not paper.local_pdf_path:
        raise ValueError("No local PDF found. Please download the PDF first.")

    try:
        asset_data = extract_pdf_assets(paper.local_pdf_path, paper_id)
    except (FileNotFoundError, ValueError) as exc:
        raise ValueError(str(exc)) from exc

    old_assets = session.exec(
        select(PaperAsset).where(PaperAsset.paper_id == paper_id)
    ).all()
    for old_asset in old_assets:
        session.delete(old_asset)

    new_assets = [PaperAsset(paper_id=paper_id, **asset) for asset in asset_data]
    for asset in new_assets:
        session.add(asset)

    return len(new_assets)


def save_workspace_for_paper(
    paper: Paper,
    paper_id: int,
    session: Session,
) -> str:
    authors = get_paper_author_names(session, paper_id)
    enriched = enrich_paper_for_display(
        paper,
        authors=authors,
        topics=get_paper_topic_names(session, paper_id),
    )
    latest_extraction = session.exec(
        select(Extraction)
        .where(Extraction.paper_id == paper_id)
        .order_by(Extraction.created_at.desc())
    ).first()
    markdown_text = export_paper_to_markdown(
        paper,
        latest_extraction,
        enriched,
        session.exec(
            select(PaperAsset)
            .where(PaperAsset.paper_id == paper_id)
            .order_by(PaperAsset.asset_type, PaperAsset.page_number, PaperAsset.asset_index)
        ).all(),
        authors,
        asset_base_path="assets",
    )
    bibtex_text = export_paper_to_bibtex(paper, authors)
    workspace = save_paper_workspace(paper, markdown_text, bibtex_text, enriched)
    return workspace["workspace_path"]


async def process_single_paper(
    session: Session,
    paper: Paper,
    request: ProcessPaperRequest,
) -> ProcessPaperResponse:
    paper_id = paper.id
    if paper_id is None:
        raise ValueError("Paper has no id.")

    steps: list[ProcessStepResult] = []
    resolve_failed = False
    download_failed = False
    parse_failed = False

    if not request.resolve_pdf:
        steps.append(skip_step("resolve_pdf", "resolve_pdf disabled by request."))
    elif paper.pdf_url:
        steps.append(success_step("resolve_pdf", "PDF URL already exists."))
    else:
        try:
            pdf_url = await resolve_pdf_url(paper)
            if not pdf_url:
                raise ValueError("No legal open-access PDF found.")
            paper.pdf_url = pdf_url
            paper.status = "PDF_RESOLVED"
            paper.updated_at = datetime.utcnow()
            session.add(paper)
            session.commit()
            session.refresh(paper)
            steps.append(success_step("resolve_pdf", "PDF URL resolved."))
        except Exception as exc:
            session.rollback()
            resolve_failed = True
            steps.append(fail_step("resolve_pdf", str(exc)))

    if not request.download_pdf:
        steps.append(skip_step("download_pdf", "download_pdf disabled by request."))
    elif resolve_failed:
        download_failed = True
        steps.append(skip_step("download_pdf", "Skipped because resolve_pdf failed."))
    elif paper.local_pdf_path:
        steps.append(success_step("download_pdf", "PDF already downloaded."))
    else:
        try:
            pdf_url = paper.pdf_url or await resolve_pdf_url(paper)
            if not pdf_url:
                raise ValueError("No legal open-access PDF found.")
            enriched = enrich_paper_for_display(paper)
            pdf_filename = build_export_filename(paper, enriched, "pdf")
            local_pdf_path = await download_pdf(pdf_url, paper_id, filename=pdf_filename)
            paper.pdf_url = pdf_url
            paper.local_pdf_path = local_pdf_path
            paper.status = "PDF_DOWNLOADED"
            paper.updated_at = datetime.utcnow()
            session.add(paper)
            session.commit()
            session.refresh(paper)
            steps.append(success_step("download_pdf", "PDF downloaded."))
        except Exception as exc:
            session.rollback()
            download_failed = True
            steps.append(fail_step("download_pdf", str(exc)))

    if not request.parse_pdf:
        steps.append(skip_step("parse_pdf", "parse_pdf disabled by request."))
    elif download_failed:
        parse_failed = True
        steps.append(skip_step("parse_pdf", "Skipped because download_pdf failed."))
    elif not paper.local_pdf_path:
        parse_failed = True
        steps.append(fail_step("parse_pdf", "No local PDF found. Please download the PDF first."))
    else:
        try:
            page_count, extracted_pages, char_count, chunk_count = save_parsed_pdf(
                paper,
                paper_id,
                session,
            )
            session.commit()
            session.refresh(paper)
            steps.append(
                success_step(
                    "parse_pdf",
                    (
                        "PDF parsed. "
                        f"pages={page_count}, extracted_pages={extracted_pages}, "
                        f"chars={char_count}, "
                        f"chunks={chunk_count}."
                    ),
                )
            )
        except Exception as exc:
            session.rollback()
            parse_failed = True
            steps.append(fail_step("parse_pdf", str(exc)))

    if not request.extract:
        steps.append(skip_step("extract", "extract disabled by request."))
    elif parse_failed:
        steps.append(skip_step("extract", "Skipped because parse_pdf failed."))
    else:
        chunks = session.exec(
            select(PaperChunk)
            .where(PaperChunk.paper_id == paper_id)
            .order_by(PaperChunk.chunk_index)
        ).all()
        if not chunks:
            steps.append(fail_step("extract", "No paper chunks found. Please call parse-pdf first."))
        else:
            selected_chunks = chunks[: request.max_chunks]
            raw_llm_output = None
            try:
                if request.extract_mode == "mock":
                    data = mock_extract(paper, selected_chunks, request.user_topic)
                    model_name = "mock"
                else:
                    data, raw_llm_output, model_name = await extract_with_openai(
                        paper,
                        selected_chunks,
                        request.user_topic,
                    )

                extraction = Extraction(
                    paper_id=paper_id,
                    model_name=model_name,
                    prompt_version=PROMPT_VERSION,
                    extracted_json=data.model_dump_json(),
                    raw_llm_output=raw_llm_output,
                )
                session.add(extraction)
                paper.status = "LLM_EXTRACTED"
                paper.updated_at = datetime.utcnow()
                session.add(paper)
                session.commit()
                session.refresh(paper)
                steps.append(success_step("extract", f"Extraction saved with {model_name}."))
            except Exception as exc:
                session.rollback()
                steps.append(fail_step("extract", str(exc)))

    if not getattr(request, "extract_assets", False):
        steps.append(skip_step("extract_assets", "extract_assets disabled by request."))
    elif not paper.local_pdf_path:
        steps.append(fail_step("extract_assets", "No local PDF found. Please download the PDF first."))
    else:
        try:
            asset_count = save_extracted_assets(paper, paper_id, session)
            session.commit()
            steps.append(success_step("extract_assets", f"Extracted {asset_count} assets."))
        except Exception as exc:
            session.rollback()
            steps.append(fail_step("extract_assets", str(exc)))

    if not getattr(request, "save_workspace", False):
        steps.append(skip_step("save_workspace", "save_workspace disabled by request."))
    else:
        try:
            workspace_path = save_workspace_for_paper(paper, paper_id, session)
            steps.append(success_step("save_workspace", f"Workspace saved to {workspace_path}."))
        except Exception as exc:
            steps.append(fail_step("save_workspace", str(exc)))

    final_status = "failed" if any(step.status == "failed" for step in steps) else "success"
    return ProcessPaperResponse(
        paper_id=paper_id,
        steps=steps,
        final_status=final_status,
    )
