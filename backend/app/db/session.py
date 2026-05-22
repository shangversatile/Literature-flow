from collections.abc import Generator
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

from app.models.extraction import Extraction
from app.models.paper import Paper
from app.models.paper_chunk import PaperChunk
from app.models.paper_text import PaperText


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATABASE_DIR = PROJECT_ROOT / "storage"
DATABASE_PATH = DATABASE_DIR / "litflow.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


def init_db() -> None:
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)
    SQLModel.metadata.create_all(engine)
