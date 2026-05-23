import re
import unicodedata

from sqlmodel import Session, select

from app.models.topic import PaperTopic, ResearchTopic


DEFAULT_TOPICS = [
    "Trustworthy AI Systems",
    "AI Systems / Inference Systems",
    "Scientific ML / AI for Science",
    "Embodied AI / World Models",
    "Mechanistic Interpretability",
    "General Foundation",
    "Survey / Benchmark",
    "Systems Optimization",
    "Evaluation / Red Teaming",
    "Interpretability / Circuits",
]


def normalize_topic_name(name: str) -> str:
    text = name.lower()
    text = "".join(
        char for char in text if not unicodedata.category(char).startswith("P")
    )
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def get_or_create_topic(
    session: Session,
    name: str,
    description: str | None = None,
) -> ResearchTopic:
    clean_name = name.strip()
    normalized_name = normalize_topic_name(clean_name)
    if not clean_name or not normalized_name:
        raise ValueError("Topic name must not be empty")
    topic = session.exec(
        select(ResearchTopic).where(ResearchTopic.normalized_name == normalized_name)
    ).first()
    if topic is not None:
        return topic

    topic = ResearchTopic(
        name=clean_name,
        normalized_name=normalized_name,
        description=description,
    )
    session.add(topic)
    session.commit()
    session.refresh(topic)
    return topic


def get_paper_topics(session: Session, paper_id: int) -> list[ResearchTopic]:
    return session.exec(
        select(ResearchTopic)
        .join(PaperTopic, PaperTopic.topic_id == ResearchTopic.id)
        .where(PaperTopic.paper_id == paper_id)
        .order_by(ResearchTopic.name)
    ).all()


def unique_topic_names(topic_names: list[str]) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for name in topic_names:
        clean_name = name.strip()
        normalized_name = normalize_topic_name(clean_name)
        if not clean_name or not normalized_name or normalized_name in seen:
            continue
        names.append(clean_name)
        seen.add(normalized_name)
    return names


def set_paper_topics(
    session: Session,
    paper_id: int,
    topic_names: list[str],
) -> list[ResearchTopic]:
    old_links = session.exec(
        select(PaperTopic).where(PaperTopic.paper_id == paper_id)
    ).all()
    for old_link in old_links:
        session.delete(old_link)
    session.commit()

    topics = [get_or_create_topic(session, name) for name in unique_topic_names(topic_names)]
    for topic in topics:
        if topic.id is not None:
            session.add(PaperTopic(paper_id=paper_id, topic_id=topic.id))
    session.commit()
    return get_paper_topics(session, paper_id)


def add_topic_to_paper(
    session: Session,
    paper_id: int,
    topic_name: str,
) -> list[ResearchTopic]:
    clean_name = topic_name.strip()
    if not clean_name or not normalize_topic_name(clean_name):
        return get_paper_topics(session, paper_id)

    topic = get_or_create_topic(session, clean_name)
    if topic.id is None:
        return get_paper_topics(session, paper_id)

    existing = session.exec(
        select(PaperTopic).where(
            PaperTopic.paper_id == paper_id,
            PaperTopic.topic_id == topic.id,
        )
    ).first()
    if existing is None:
        session.add(PaperTopic(paper_id=paper_id, topic_id=topic.id))
        session.commit()
    return get_paper_topics(session, paper_id)


def remove_topic_from_paper(
    session: Session,
    paper_id: int,
    topic_name: str,
) -> list[ResearchTopic]:
    normalized_name = normalize_topic_name(topic_name)
    if not normalized_name:
        return get_paper_topics(session, paper_id)

    topic = session.exec(
        select(ResearchTopic).where(ResearchTopic.normalized_name == normalized_name)
    ).first()
    if topic is None or topic.id is None:
        return get_paper_topics(session, paper_id)

    links = session.exec(
        select(PaperTopic).where(
            PaperTopic.paper_id == paper_id,
            PaperTopic.topic_id == topic.id,
        )
    ).all()
    for link in links:
        session.delete(link)
    session.commit()
    return get_paper_topics(session, paper_id)
