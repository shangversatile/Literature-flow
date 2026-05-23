import re
import unicodedata
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.db.session import get_session
from app.models.extraction import Extraction
from app.models.paper import Paper
from app.models.paper_asset import PaperAsset
from app.models.paper_chunk import PaperChunk
from app.models.paper_text import PaperText
from app.schemas.batch import (
    BatchPaperResult,
    BatchProcessRequest,
    BatchProcessResponse,
)
from app.schemas.extraction import ExtractRequest, ExtractResponse, ExtractionRead
from app.schemas.paper import PaperCreate, PaperEnrichedRead, PaperRead, PaperUpdate
from app.schemas.paper_asset import ExtractAssetsResponse, PaperAssetRead
from app.schemas.paper_text import PaperChunkRead, PaperTextRead, ParsePdfResponse
from app.schemas.rag import AskPaperRequest, AskPaperResponse
from app.schemas.workspace import WorkspaceInfoResponse, WorkspaceSaveResponse
from app.schemas.workflow import (
    ProcessPaperRequest,
    ProcessPaperResponse,
    ProcessStepResult,
)
from app.services.authors import get_paper_author_names
from app.services.download.downloader import PdfDownloadError, download_pdf
from app.services.download.resolver import resolve_pdf_url
from app.services.download.unpaywall import (
    UnpaywallEmailMissingError,
    UnpaywallLookupError,
)
from app.services.extraction.llm_extractor import (
    PROMPT_VERSION,
    extract_with_openai,
    mock_extract,
)
from app.services.extraction.pdf_parser import extract_text_from_pdf
from app.services.extraction.pdf_assets import extract_pdf_assets
from app.services.extraction.rag_qa import (
    answer_with_openai,
    mock_answer_question,
    retrieve_relevant_chunks,
)
from app.services.extraction.text_chunker import chunk_text_pages
from app.services.export.bibtex_exporter import export_paper_to_bibtex
from app.services.export.filename_utils import build_export_filename
from app.services.export.markdown_exporter import export_paper_to_markdown
from app.services.export.workspace_exporter import save_paper_workspace, workspace_info
from app.services.paper_enrichment import enrich_paper_for_display
from app.services.topics import get_paper_topics
from app.services.workflow import process_single_paper, save_parsed_pdf


router = APIRouter(prefix="/papers", tags=["papers"])


def normalize_title(title: str) -> str:
    text = title.lower()
    text = "".join(
        char for char in text if not unicodedata.category(char).startswith("P")
    )
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def latest_extraction_for_paper(
    paper_id: int,
    session: Session,
) -> Extraction | None:
    return session.exec(
        select(Extraction)
        .where(Extraction.paper_id == paper_id)
        .order_by(Extraction.created_at.desc())
    ).first()


def assets_for_paper(paper_id: int, session: Session) -> list[PaperAsset]:
    return session.exec(
        select(PaperAsset)
        .where(PaperAsset.paper_id == paper_id)
        .order_by(PaperAsset.asset_type, PaperAsset.page_number, PaperAsset.asset_index)
    ).all()


def get_paper_topic_names(session: Session, paper_id: int) -> list[str]:
    return [topic.name for topic in get_paper_topics(session, paper_id)]


@router.post("", response_model=PaperRead)
def create_paper(
    paper_create: PaperCreate,
    session: Session = Depends(get_session),
) -> Paper:
    paper = Paper.model_validate(paper_create)
    paper.normalized_title = normalize_title(paper.title)

    session.add(paper)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail="Paper DOI already exists") from exc
    session.refresh(paper)
    return paper


@router.get("", response_model=list[PaperRead])
def read_papers(session: Session = Depends(get_session)) -> list[Paper]:
    return session.exec(select(Paper)).all()


@router.get("/enriched", response_model=list[PaperEnrichedRead])
def read_enriched_papers(
    query: str | None = None,
    session: Session = Depends(get_session),
) -> list[PaperEnrichedRead]:
    papers = session.exec(select(Paper)).all()
    enriched = [
        enrich_paper_for_display(
            paper,
            query,
            get_paper_author_names(session, paper.id) if paper.id is not None else [],
            get_paper_topic_names(session, paper.id) if paper.id is not None else [],
        )
        for paper in papers
    ]
    enriched.sort(key=lambda paper: paper.final_score or 0.0, reverse=True)
    return enriched


@router.get("/{paper_id}/enriched", response_model=PaperEnrichedRead)
def read_enriched_paper(
    paper_id: int,
    query: str | None = None,
    session: Session = Depends(get_session),
) -> PaperEnrichedRead:
    paper = session.get(Paper, paper_id)
    if paper is None:
        raise HTTPException(status_code=404, detail="Paper not found")
    return enrich_paper_for_display(
        paper,
        query,
        get_paper_author_names(session, paper_id),
        get_paper_topic_names(session, paper_id),
    )


@router.get("/{paper_id}/export/markdown")
def export_markdown(
    paper_id: int,
    session: Session = Depends(get_session),
) -> PlainTextResponse:
    paper = session.get(Paper, paper_id)
    if paper is None:
        raise HTTPException(status_code=404, detail="Paper not found")

    authors = get_paper_author_names(session, paper_id)
    enriched = enrich_paper_for_display(
        paper,
        authors=authors,
        topics=get_paper_topic_names(session, paper_id),
    )
    latest_extraction = latest_extraction_for_paper(paper_id, session)
    assets = assets_for_paper(paper_id, session)
    content = export_paper_to_markdown(paper, latest_extraction, enriched, assets, authors)
    filename = build_export_filename(paper, enriched, "md")
    return PlainTextResponse(
        content,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{paper_id}/save-workspace", response_model=WorkspaceSaveResponse)
def save_paper_to_workspace(
    paper_id: int,
    session: Session = Depends(get_session),
) -> WorkspaceSaveResponse:
    paper = session.get(Paper, paper_id)
    if paper is None:
        raise HTTPException(status_code=404, detail="Paper not found")

    authors = get_paper_author_names(session, paper_id)
    enriched = enrich_paper_for_display(
        paper,
        authors=authors,
        topics=get_paper_topic_names(session, paper_id),
    )
    latest_extraction = latest_extraction_for_paper(paper_id, session)
    markdown_text = export_paper_to_markdown(
        paper,
        latest_extraction,
        enriched,
        assets_for_paper(paper_id, session),
        authors,
    )
    bibtex_text = export_paper_to_bibtex(paper, authors)
    return WorkspaceSaveResponse.model_validate(
        save_paper_workspace(paper, markdown_text, bibtex_text, enriched)
    )


@router.get("/{paper_id}/workspace", response_model=WorkspaceInfoResponse)
def read_paper_workspace(
    paper_id: int,
    session: Session = Depends(get_session),
) -> WorkspaceInfoResponse:
    paper = session.get(Paper, paper_id)
    if paper is None:
        raise HTTPException(status_code=404, detail="Paper not found")

    authors = get_paper_author_names(session, paper_id)
    enriched = enrich_paper_for_display(
        paper,
        authors=authors,
        topics=get_paper_topic_names(session, paper_id),
    )
    return WorkspaceInfoResponse.model_validate(workspace_info(paper, enriched))


@router.get("/{paper_id}/export/bibtex")
def export_bibtex(
    paper_id: int,
    session: Session = Depends(get_session),
) -> PlainTextResponse:
    paper = session.get(Paper, paper_id)
    if paper is None:
        raise HTTPException(status_code=404, detail="Paper not found")

    authors = get_paper_author_names(session, paper_id)
    enriched = enrich_paper_for_display(
        paper,
        authors=authors,
        topics=get_paper_topic_names(session, paper_id),
    )
    content = export_paper_to_bibtex(paper, authors)
    filename = build_export_filename(paper, enriched, "bib")
    return PlainTextResponse(
        content,
        media_type="application/x-bibtex; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{paper_id}/extract-assets", response_model=ExtractAssetsResponse)
def extract_paper_assets(
    paper_id: int,
    session: Session = Depends(get_session),
) -> ExtractAssetsResponse:
    paper = session.get(Paper, paper_id)
    if paper is None:
        raise HTTPException(status_code=404, detail="Paper not found")
    if not paper.local_pdf_path:
        raise HTTPException(
            status_code=400,
            detail="No local PDF found. Please call download-pdf first.",
        )

    try:
        asset_data = extract_pdf_assets(paper.local_pdf_path, paper_id)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    old_assets = session.exec(
        select(PaperAsset).where(PaperAsset.paper_id == paper_id)
    ).all()
    for old_asset in old_assets:
        session.delete(old_asset)

    new_assets = [PaperAsset(paper_id=paper_id, **asset) for asset in asset_data]
    for asset in new_assets:
        session.add(asset)

    session.commit()

    return ExtractAssetsResponse(
        paper_id=paper_id,
        asset_count=len(new_assets),
        page_image_count=sum(1 for asset in new_assets if asset.asset_type == "page_image"),
        figure_caption_count=sum(
            1 for asset in new_assets if asset.asset_type == "figure_caption"
        ),
        table_caption_count=sum(
            1 for asset in new_assets if asset.asset_type == "table_caption"
        ),
        status="assets_extracted",
    )


@router.get("/{paper_id}/assets", response_model=list[PaperAssetRead])
def read_paper_assets(
    paper_id: int,
    session: Session = Depends(get_session),
) -> list[PaperAsset]:
    paper = session.get(Paper, paper_id)
    if paper is None:
        raise HTTPException(status_code=404, detail="Paper not found")

    return session.exec(
        select(PaperAsset)
        .where(PaperAsset.paper_id == paper_id)
        .order_by(PaperAsset.asset_type, PaperAsset.page_number, PaperAsset.asset_index)
    ).all()


@router.post(
    "/process-batch",
    response_model=BatchProcessResponse,
    summary="Batch Process Selected Papers",
)
async def process_papers_batch(
    request: BatchProcessRequest,
    session: Session = Depends(get_session),
) -> BatchProcessResponse:
    paper_ids: list[int] = []
    seen: set[int] = set()
    for paper_id in request.paper_ids:
        if paper_id not in seen:
            paper_ids.append(paper_id)
            seen.add(paper_id)

    if not paper_ids:
        raise HTTPException(status_code=400, detail="paper_ids must not be empty.")
    if len(paper_ids) > 20:
        raise HTTPException(status_code=400, detail="Batch process supports at most 20 papers.")
    if request.extract_mode not in {"mock", "openai"}:
        raise HTTPException(
            status_code=400,
            detail="extract_mode must be 'mock' or 'openai'.",
        )
    if not 1 <= request.max_chunks <= 20:
        raise HTTPException(status_code=400, detail="max_chunks must be between 1 and 20.")

    results: list[BatchPaperResult] = []
    for paper_id in paper_ids:
        paper = session.get(Paper, paper_id)
        if paper is None:
            results.append(
                BatchPaperResult(
                    paper_id=paper_id,
                    title=None,
                    status="failed",
                    final_status=None,
                    steps=[
                        ProcessStepResult(
                            name="load_paper",
                            status="failed",
                            message="Paper not found",
                        )
                    ],
                    error="Paper not found",
                )
            )
            continue

        try:
            response = await process_single_paper(session, paper, request)
            step_statuses = [step.status for step in response.steps]
            if any(status == "failed" for status in step_statuses):
                status = "failed"
            elif step_statuses and all(status == "skipped" for status in step_statuses):
                status = "skipped"
            else:
                status = "succeeded"
            results.append(
                BatchPaperResult(
                    paper_id=paper_id,
                    title=paper.title,
                    status=status,
                    final_status=response.final_status,
                    steps=response.steps,
                    error=None if status != "failed" else "One or more steps failed.",
                )
            )
        except Exception as exc:
            session.rollback()
            results.append(
                BatchPaperResult(
                    paper_id=paper_id,
                    title=paper.title,
                    status="failed",
                    final_status=None,
                    steps=[
                        ProcessStepResult(
                            name="process",
                            status="failed",
                            message=str(exc),
                        )
                    ],
                    error=str(exc),
                )
            )

    succeeded = sum(1 for result in results if result.status == "succeeded")
    failed = sum(1 for result in results if result.status == "failed")
    skipped = sum(1 for result in results if result.status == "skipped")
    return BatchProcessResponse(
        total=len(results),
        succeeded=succeeded,
        failed=failed,
        skipped=skipped,
        results=results,
    )


@router.get("/{paper_id}", response_model=PaperRead)
def read_paper(
    paper_id: int,
    session: Session = Depends(get_session),
) -> Paper:
    paper = session.get(Paper, paper_id)
    if paper is None:
        raise HTTPException(status_code=404, detail="Paper not found")
    return paper


@router.post(
    "/{paper_id}/process",
    response_model=ProcessPaperResponse,
    summary="Process Paper",
)
async def process_paper(
    paper_id: int,
    request: ProcessPaperRequest,
    session: Session = Depends(get_session),
) -> ProcessPaperResponse:
    paper = session.get(Paper, paper_id)
    if paper is None:
        raise HTTPException(status_code=404, detail="Paper not found")

    if request.extract_mode not in {"mock", "openai"}:
        raise HTTPException(
            status_code=400,
            detail="extract_mode must be 'mock' or 'openai'.",
        )
    if not 1 <= request.max_chunks <= 20:
        raise HTTPException(status_code=400, detail="max_chunks must be between 1 and 20.")

    return await process_single_paper(session, paper, request)


@router.post("/{paper_id}/resolve-pdf", response_model=PaperRead)
async def resolve_paper_pdf(
    paper_id: int,
    session: Session = Depends(get_session),
) -> Paper:
    paper = session.get(Paper, paper_id)
    if paper is None:
        raise HTTPException(status_code=404, detail="Paper not found")

    try:
        pdf_url = await resolve_pdf_url(paper)
    except UnpaywallEmailMissingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except UnpaywallLookupError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if not pdf_url:
        raise HTTPException(status_code=404, detail="No legal open-access PDF found")

    paper.pdf_url = pdf_url
    if paper.status == "DISCOVERED":
        paper.status = "PDF_RESOLVED"
    paper.updated_at = datetime.utcnow()

    session.add(paper)
    session.commit()
    session.refresh(paper)
    return paper


@router.post("/{paper_id}/download-pdf", response_model=PaperRead)
async def download_paper_pdf(
    paper_id: int,
    session: Session = Depends(get_session),
) -> Paper:
    paper = session.get(Paper, paper_id)
    if paper is None:
        raise HTTPException(status_code=404, detail="Paper not found")

    try:
        pdf_url = await resolve_pdf_url(paper)
    except UnpaywallEmailMissingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except UnpaywallLookupError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if not pdf_url:
        raise HTTPException(status_code=404, detail="No legal open-access PDF found")

    try:
        enriched = enrich_paper_for_display(paper)
        pdf_filename = build_export_filename(paper, enriched, "pdf")
        local_pdf_path = await download_pdf(pdf_url, paper_id, filename=pdf_filename)
    except PdfDownloadError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    paper.pdf_url = pdf_url
    paper.local_pdf_path = local_pdf_path
    paper.status = "PDF_DOWNLOADED"
    paper.updated_at = datetime.utcnow()

    session.add(paper)
    session.commit()
    session.refresh(paper)
    return paper


@router.post("/{paper_id}/parse-pdf", response_model=ParsePdfResponse)
def parse_paper_pdf(
    paper_id: int,
    session: Session = Depends(get_session),
) -> ParsePdfResponse:
    paper = session.get(Paper, paper_id)
    if paper is None:
        raise HTTPException(status_code=404, detail="Paper not found")

    if not paper.local_pdf_path:
        raise HTTPException(
            status_code=400,
            detail="No local PDF found. Please call download-pdf first.",
        )

    try:
        page_count, extracted_pages, char_count, chunk_count = save_parsed_pdf(
            paper,
            paper_id,
            session,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    session.commit()
    return ParsePdfResponse(
        paper_id=paper_id,
        page_count=page_count,
        extracted_pages=extracted_pages,
        char_count=char_count,
        chunk_count=chunk_count,
        status=paper.status,
    )


@router.get("/{paper_id}/pdf-text", response_model=PaperTextRead)
def read_paper_text(
    paper_id: int,
    session: Session = Depends(get_session),
) -> PaperText:
    paper_text = session.exec(
        select(PaperText).where(PaperText.paper_id == paper_id)
    ).first()
    if paper_text is None:
        raise HTTPException(
            status_code=404,
            detail="PDF text not found. Please call parse-pdf first.",
        )
    return paper_text


@router.get("/{paper_id}/chunks", response_model=list[PaperChunkRead])
def read_paper_chunks(
    paper_id: int,
    session: Session = Depends(get_session),
) -> list[PaperChunk]:
    return session.exec(
        select(PaperChunk)
        .where(PaperChunk.paper_id == paper_id)
        .order_by(PaperChunk.chunk_index)
    ).all()


@router.post("/{paper_id}/ask", response_model=AskPaperResponse)
async def ask_paper_question(
    paper_id: int,
    request: AskPaperRequest,
    session: Session = Depends(get_session),
) -> AskPaperResponse:
    paper = session.get(Paper, paper_id)
    if paper is None:
        raise HTTPException(status_code=404, detail="Paper not found")

    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question must not be empty.")

    if request.mode not in {"mock", "openai"}:
        raise HTTPException(status_code=400, detail="Mode must be 'mock' or 'openai'.")

    chunks = session.exec(
        select(PaperChunk)
        .where(PaperChunk.paper_id == paper_id)
        .order_by(PaperChunk.chunk_index)
    ).all()
    if not chunks:
        raise HTTPException(
            status_code=400,
            detail="No paper chunks found. Please call parse-pdf first.",
        )

    top_k = max(1, min(request.top_k, 10))
    evidence_chunks = retrieve_relevant_chunks(question, chunks, top_k)

    if request.mode == "mock":
        data = mock_answer_question(paper, question, evidence_chunks)
    else:
        try:
            answer, evidence_chunk_indices, _raw_llm_output = await answer_with_openai(
                paper,
                question,
                evidence_chunks,
            )
            data = {
                "answer": answer,
                "evidence_chunk_indices": evidence_chunk_indices,
            }
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail=f"OpenAI RAG question answering failed: {exc}",
            ) from exc

    return AskPaperResponse(
        paper_id=paper_id,
        question=question,
        mode=request.mode,
        answer=data["answer"],
        evidence_chunks=evidence_chunks,
        evidence_chunk_indices=data["evidence_chunk_indices"],
    )


@router.post("/{paper_id}/extract", response_model=ExtractResponse)
async def extract_paper_information(
    paper_id: int,
    request: ExtractRequest,
    session: Session = Depends(get_session),
) -> ExtractResponse:
    paper = session.get(Paper, paper_id)
    if paper is None:
        raise HTTPException(status_code=404, detail="Paper not found")

    chunks = session.exec(
        select(PaperChunk)
        .where(PaperChunk.paper_id == paper_id)
        .order_by(PaperChunk.chunk_index)
    ).all()
    if not chunks:
        raise HTTPException(
            status_code=400,
            detail="No paper chunks found. Please call parse-pdf first.",
        )

    selected_chunks = chunks[: request.max_chunks]
    raw_llm_output = None

    if request.mode == "mock":
        data = mock_extract(paper, selected_chunks, request.user_topic)
        model_name = "mock"
    else:
        try:
            data, raw_llm_output, model_name = await extract_with_openai(
                paper,
                selected_chunks,
                request.user_topic,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail=f"OpenAI extraction failed: {exc}",
            ) from exc

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
    session.refresh(extraction)

    return ExtractResponse(
        paper_id=paper_id,
        extraction_id=extraction.id,
        model_name=model_name,
        prompt_version=extraction.prompt_version,
        data=data,
    )


@router.get("/{paper_id}/extractions", response_model=list[ExtractionRead])
def read_paper_extractions(
    paper_id: int,
    session: Session = Depends(get_session),
) -> list[Extraction]:
    return session.exec(
        select(Extraction)
        .where(Extraction.paper_id == paper_id)
        .order_by(Extraction.created_at.desc())
    ).all()


@router.get("/{paper_id}/latest-extraction", response_model=ExtractionRead)
def read_latest_paper_extraction(
    paper_id: int,
    session: Session = Depends(get_session),
) -> Extraction:
    extraction = session.exec(
        select(Extraction)
        .where(Extraction.paper_id == paper_id)
        .order_by(Extraction.created_at.desc())
    ).first()
    if extraction is None:
        raise HTTPException(status_code=404, detail="No extraction found")
    return extraction


@router.patch("/{paper_id}", response_model=PaperRead)
def update_paper(
    paper_id: int,
    paper_update: PaperUpdate,
    session: Session = Depends(get_session),
) -> Paper:
    paper = session.get(Paper, paper_id)
    if paper is None:
        raise HTTPException(status_code=404, detail="Paper not found")

    update_data = paper_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(paper, field, value)

    if "title" in update_data and paper.title is not None:
        paper.normalized_title = normalize_title(paper.title)

    paper.updated_at = datetime.utcnow()

    session.add(paper)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail="Paper DOI already exists") from exc
    session.refresh(paper)
    return paper


@router.delete("/{paper_id}")
def delete_paper(
    paper_id: int,
    session: Session = Depends(get_session),
) -> dict[str, str]:
    paper = session.get(Paper, paper_id)
    if paper is None:
        raise HTTPException(status_code=404, detail="Paper not found")

    session.delete(paper)
    session.commit()
    return {"message": "Paper deleted"}
