import re
import string

from sqlmodel import Session, select

from app.models.author import Author, PaperAuthor


def normalize_author_name(name: str) -> str:
    value = name.lower()
    value = value.translate(str.maketrans("", "", string.punctuation))
    return re.sub(r"\s+", " ", value).strip()


def save_paper_authors(
    session: Session,
    paper_id: int,
    author_names: list[str],
) -> None:
    if not author_names:
        return

    old_links = session.exec(
        select(PaperAuthor).where(PaperAuthor.paper_id == paper_id)
    ).all()
    for old_link in old_links:
        session.delete(old_link)

    seen: set[str] = set()
    author_order = 1
    for raw_name in author_names:
        name = raw_name.strip()
        if not name:
            continue

        normalized_name = normalize_author_name(name)
        if not normalized_name or normalized_name in seen:
            continue
        seen.add(normalized_name)

        author = session.exec(
            select(Author).where(Author.normalized_name == normalized_name)
        ).first()
        if author is None:
            author = Author(name=name, normalized_name=normalized_name)
            session.add(author)
            session.flush()

        session.add(
            PaperAuthor(
                paper_id=paper_id,
                author_id=author.id,
                author_order=author_order,
            )
        )
        author_order += 1


def get_paper_author_names(session: Session, paper_id: int) -> list[str]:
    links = session.exec(
        select(PaperAuthor)
        .where(PaperAuthor.paper_id == paper_id)
        .order_by(PaperAuthor.author_order)
    ).all()

    names: list[str] = []
    for link in links:
        author = session.get(Author, link.author_id)
        if author is not None:
            names.append(author.name)
    return names
