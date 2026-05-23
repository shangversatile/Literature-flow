from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.db.session import get_session
from app.schemas.library_rag import LibraryAskRequest, LibraryAskResponse
from app.services.extraction.library_rag import (
    answer_library_with_openai,
    mock_answer_library_question,
    retrieve_library_chunks,
)


router = APIRouter(prefix="/ask", tags=["library-rag"])


@router.post("/library", response_model=LibraryAskResponse)
async def ask_library(
    request: LibraryAskRequest,
    session: Session = Depends(get_session),
) -> LibraryAskResponse:
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question must not be empty.")
    if request.mode not in {"mock", "openai"}:
        raise HTTPException(status_code=400, detail="Mode must be 'mock' or 'openai'.")

    top_k = max(1, min(request.top_k, 30))
    topic = request.topic.strip() if request.topic else None
    evidence_chunks = retrieve_library_chunks(session, question, top_k, topic)

    if not evidence_chunks:
        return LibraryAskResponse(
            question=question,
            mode=request.mode,
            topic=topic,
            answer="No matching library evidence was found for this question.",
            evidence_chunks=[],
            evidence_count=0,
        )

    if request.mode == "mock":
        data = mock_answer_library_question(question, evidence_chunks, topic)
        answer = data["answer"]
    else:
        try:
            answer, _raw_output = await answer_library_with_openai(
                question,
                evidence_chunks,
                topic,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail=f"OpenAI library RAG question answering failed: {exc}",
            ) from exc

    return LibraryAskResponse(
        question=question,
        mode=request.mode,
        topic=topic,
        answer=answer,
        evidence_chunks=evidence_chunks,
        evidence_count=len(evidence_chunks),
    )
