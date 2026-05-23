from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.db.session import get_session
from app.models.paper import Paper
from app.models.topic import ResearchTopic
from app.schemas.topic import (
    PaperTopicName,
    PaperTopicsResponse,
    PaperTopicUpdate,
    ResearchTopicCreate,
    ResearchTopicRead,
)
from app.services.topics import (
    DEFAULT_TOPICS,
    add_topic_to_paper,
    get_or_create_topic,
    get_paper_topics,
    remove_topic_from_paper,
    set_paper_topics,
)


router = APIRouter(tags=["topics"])


def ensure_paper(session: Session, paper_id: int) -> None:
    if session.get(Paper, paper_id) is None:
        raise HTTPException(status_code=404, detail="Paper not found")


@router.get("/topics", response_model=list[ResearchTopicRead])
def read_topics(session: Session = Depends(get_session)) -> list[ResearchTopic]:
    return session.exec(select(ResearchTopic).order_by(ResearchTopic.name)).all()


@router.post("/topics", response_model=ResearchTopicRead)
def create_topic(
    topic_create: ResearchTopicCreate,
    session: Session = Depends(get_session),
) -> ResearchTopic:
    if not topic_create.name.strip():
        raise HTTPException(status_code=400, detail="Topic name must not be empty")
    try:
        return get_or_create_topic(session, topic_create.name, topic_create.description)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail="Topic already exists") from exc


@router.post("/topics/seed-defaults", response_model=list[ResearchTopicRead])
def seed_default_topics(session: Session = Depends(get_session)) -> list[ResearchTopic]:
    for name in DEFAULT_TOPICS:
        get_or_create_topic(session, name)
    return session.exec(select(ResearchTopic).order_by(ResearchTopic.name)).all()


@router.get("/papers/{paper_id}/topics", response_model=PaperTopicsResponse)
def read_paper_topics(
    paper_id: int,
    session: Session = Depends(get_session),
) -> PaperTopicsResponse:
    ensure_paper(session, paper_id)
    return PaperTopicsResponse(paper_id=paper_id, topics=get_paper_topics(session, paper_id))


@router.put("/papers/{paper_id}/topics", response_model=PaperTopicsResponse)
def update_paper_topics(
    paper_id: int,
    topic_update: PaperTopicUpdate,
    session: Session = Depends(get_session),
) -> PaperTopicsResponse:
    ensure_paper(session, paper_id)
    topics = set_paper_topics(session, paper_id, topic_update.topic_names)
    return PaperTopicsResponse(paper_id=paper_id, topics=topics)


@router.post("/papers/{paper_id}/topics", response_model=PaperTopicsResponse)
def add_paper_topic(
    paper_id: int,
    topic: PaperTopicName,
    session: Session = Depends(get_session),
) -> PaperTopicsResponse:
    ensure_paper(session, paper_id)
    topics = add_topic_to_paper(session, paper_id, topic.topic_name)
    return PaperTopicsResponse(paper_id=paper_id, topics=topics)


@router.post("/papers/{paper_id}/topics/remove", response_model=PaperTopicsResponse)
def remove_paper_topic(
    paper_id: int,
    topic: PaperTopicName,
    session: Session = Depends(get_session),
) -> PaperTopicsResponse:
    ensure_paper(session, paper_id)
    topics = remove_topic_from_paper(session, paper_id, topic.topic_name)
    return PaperTopicsResponse(paper_id=paper_id, topics=topics)
