from fastapi import FastAPI

app = FastAPI(title="LitFlow Backend")


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "LitFlow backend is running"}


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
