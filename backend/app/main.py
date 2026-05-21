from fastapi import FastAPI

from app.api.papers import router as papers_router
from app.db.session import init_db

app = FastAPI(title="LitFlow Backend")


@app.on_event("startup")
def on_startup() -> None:
    init_db()


app.include_router(papers_router)


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "LitFlow backend is running"}


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
