import re
import unicodedata
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.db.session import get_session
from app.models.paper import Paper
from app.schemas.paper import PaperCreate, PaperRead, PaperUpdate
from app.services.download.downloader import PdfDownloadError, download_pdf
from app.services.download.resolver import resolve_pdf_url
from app.services.download.unpaywall import (
    UnpaywallEmailMissingError,
    UnpaywallLookupError,
)


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
