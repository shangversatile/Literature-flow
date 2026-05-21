# LitFlow Development Notes

## Tech Stack

- Backend: Python 3.11, FastAPI, SQLModel, SQLite
- Frontend: Vue 3, Vite, TypeScript, TailwindCSS
- Storage: local `storage/` directory for future generated or downloaded files
- Docs: project documentation in `docs/`

## Directory Rules

- Backend code lives in `backend/app/`.
- Frontend code lives in `frontend/src/`.
- Runtime files and future PDFs belong under `storage/`.
- Documentation belongs under `docs/`.

## Development Rules

- Keep code simple and readable for beginners.
- Implement one small feature at a time.
- Do not hard-code API keys or secrets.
- Use environment variables for configuration.
- Only download open-access PDFs.
- Do not implement Sci-Hub or any illegal download logic.
- Do not add literature search, database tables, PDF download, or LLM extraction until those features are requested.
