import re
import unicodedata
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.db.session import get_session
from app.models.paper import Paper
from app.models.paper_chunk import PaperChunk
from app.models.paper_text import PaperText
from app.schemas.paper import PaperCreate, PaperRead, PaperUpdate
from app.schemas.paper_text import PaperChunkRead, PaperTextRead, ParsePdfResponse
from app.services.download.downloader import PdfDownloadError, download_pdf
from app.services.download.resolver import resolve_pdf_url
from app.services.download.unpaywall import (
    UnpaywallEmailMissingError,
    UnpaywallLookupError,
)
from app.services.extraction.pdf_parser import extract_text_from_pdf
from app.services.extraction.text_chunker import chunk_text_pages


router = APIRouter(prefix="/papers", tags=["papers"])


def normalize_title(title: str) -> str:
    text = title.lower()
    text = "".join(
        char for char in text if not unicodedata.category(char).startswith("P")
    )
    text = re.sub(r"\s+", " ", text)
    return text.strip()


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


@router.get("/{paper_id}", response_model=PaperRead)
def read_paper(
    paper_id: int,
    session: Session = Depends(get_session),
) -> Paper:
    paper = session.get(Paper, paper_id)
    if paper is None:
        raise HTTPException(status_code=404, detail="Paper not found")
    return paper


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
        local_pdf_path = await download_pdf(pdf_url, paper_id)
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
        parsed = extract_text_from_pdf(paper.local_pdf_path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    full_text = parsed["full_text"].strip()
    if not full_text:
        raise HTTPException(
            status_code=400,
            detail=parsed.get("error") or "No extractable text found. The PDF may be scanned.",
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

    session.commit()
    return ParsePdfResponse(
        paper_id=paper_id,
        page_count=parsed["page_count"],
        extracted_pages=parsed["extracted_pages"],
        char_count=len(full_text),
        chunk_count=len(chunk_data),
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
