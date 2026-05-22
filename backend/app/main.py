from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.papers import router as papers_router
from app.api.search import router as search_router
from app.db.session import init_db

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PDF_STORAGE_DIR = PROJECT_ROOT / "storage" / "pdfs"
PDF_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="LitFlow Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


app.include_router(papers_router)
app.include_router(search_router)
app.mount("/static/pdfs", StaticFiles(directory=PDF_STORAGE_DIR), name="pdfs")


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "LitFlow backend is running"}


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
