# LitFlow

LitFlow is a minimal project skeleton for automated literature extraction and knowledge management.

## Project Structure

```text
.
├── backend/
│   ├── app/
│   │   └── main.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.vue
│   │   ├── main.ts
│   │   └── style.css
│   ├── index.html
│   ├── package.json
│   ├── postcss.config.js
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   └── vite.config.ts
├── storage/
├── docs/
├── CODEX.md
├── README.md
└── .gitignore
```

## Start Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Backend URLs:

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/health`

Semantic Scholar API key:

Create a `.env` file in the project root and add:

```bash
S2_API_KEY=your_semantic_scholar_api_key
UNPAYWALL_EMAIL=your_email@example.com
```

Do not commit `.env`. It is already listed in `.gitignore`.

Semantic Scholar search API:

```bash
curl "http://127.0.0.1:8000/search/semantic-scholar?query=flashattention&limit=5"
```

OpenAlex search API:

```bash
curl "http://127.0.0.1:8000/search/openalex?query=flashattention&limit=5"
```

arXiv search API:

```bash
curl "http://127.0.0.1:8000/search/arxiv?query=flashattention&limit=5"
```

All sources search API:

```bash
curl "http://127.0.0.1:8000/search/all?query=flashattention&limit=10"
```

Unified search results include scoring v2 fields:

- `relevance_score`
- `authority_score`
- `frontier_score`
- `accessibility_score`
- `final_score`

`final_score` is computed as:

```text
0.40 * relevance_score
+ 0.30 * authority_score
+ 0.20 * frontier_score
+ 0.10 * accessibility_score
```

`quality_score` is still returned for compatibility and is set to `final_score`.

Search all sources and save results:

```bash
curl -X POST "http://127.0.0.1:8000/search/all/save" ^
  -H "Content-Type: application/json" ^
  -d "{\"query\":\"flashattention\",\"limit\":10}"
```

Legal open-access PDF resolver and downloader:

The system only resolves and downloads legal open-access PDF URLs from existing
paper PDF URLs, arXiv PDF links, or Unpaywall. It does not bypass paywalls,
logins, or CAPTCHA.

```bash
curl -X POST "http://127.0.0.1:8000/papers/1/resolve-pdf"
curl -X POST "http://127.0.0.1:8000/papers/1/download-pdf"
```

PDF text parsing and RAG-ready chunks:

Run `download-pdf` first so `Paper.local_pdf_path` points to a local PDF file,
then parse the PDF and inspect the saved text/chunks.

```bash
curl -X POST "http://127.0.0.1:8000/papers/1/download-pdf"
curl -X POST "http://127.0.0.1:8000/papers/1/parse-pdf"
curl "http://127.0.0.1:8000/papers/1/pdf-text"
curl "http://127.0.0.1:8000/papers/1/chunks"
```

LLM structured extraction:

Run `download-pdf` and `parse-pdf` first so the paper has saved chunks. Use
`mock` mode to test the database flow without calling an external API.

```bash
curl -X POST "http://127.0.0.1:8000/papers/1/extract" ^
  -H "Content-Type: application/json" ^
  -d "{\"mode\":\"mock\",\"user_topic\":\"LLM inference systems\",\"max_chunks\":8}"

curl "http://127.0.0.1:8000/papers/1/extractions"
curl "http://127.0.0.1:8000/papers/1/latest-extraction"
```

For OpenAI extraction, set `OPENAI_API_KEY` in `.env`. You can optionally set
`LLM_MODEL`; it defaults to `gpt-4.1-mini`.

```bash
OPENAI_API_KEY=your_openai_api_key
LLM_MODEL=gpt-4.1-mini
```

```bash
curl -X POST "http://127.0.0.1:8000/papers/1/extract" ^
  -H "Content-Type: application/json" ^
  -d "{\"mode\":\"openai\",\"user_topic\":\"LLM inference systems\",\"max_chunks\":8}"
```

Single-paper RAG question answering:

Run `parse-pdf` first so the paper has saved `PaperChunk` records. The RAG
endpoint uses simple keyword retrieval only; it does not use embeddings or a
vector database.

Mock mode does not call any external API:

```bash
curl -X POST "http://127.0.0.1:8000/papers/1/ask" ^
  -H "Content-Type: application/json" ^
  -d "{\"question\":\"What is the main systems optimization in this paper?\",\"mode\":\"mock\",\"top_k\":5}"
```

OpenAI mode uses `OPENAI_API_KEY` and optional `LLM_MODEL` from `.env`:

```bash
curl -X POST "http://127.0.0.1:8000/papers/1/ask" ^
  -H "Content-Type: application/json" ^
  -d "{\"question\":\"What is the main systems optimization in this paper?\",\"mode\":\"openai\",\"top_k\":5}"
```

One-click paper processing workflow:

The workflow endpoint can resolve, download, parse, and extract a paper in one
request. Mock extraction is useful when OpenAI quota is unavailable.

Endpoint:

- `POST /papers/{paper_id}/process`

```bash
curl -X POST "http://127.0.0.1:8000/papers/1/process" ^
  -H "Content-Type: application/json" ^
  -d "{\"resolve_pdf\":true,\"download_pdf\":true,\"parse_pdf\":true,\"extract\":true,\"extract_mode\":\"mock\",\"user_topic\":\"LLM inference systems\",\"max_chunks\":8}"
```

If you want to use OpenAI extraction, set `extract_mode` to `openai`. If OpenAI
quota or API access is unavailable, keep `extract_mode` as `mock`.

Open API docs:

- `http://127.0.0.1:8000/docs`

## Start Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend URL:

- `http://127.0.0.1:5173/`

## Paper Dashboard

Start the backend first:

```bash
cd backend
.venv\Scripts\activate
uvicorn app.main:app --reload
```

Then start the frontend:

```bash
cd frontend
npm install
npm run dev
```

Open:

- `http://localhost:5173`

Before using the dashboard, save papers through the backend search endpoint:

```bash
curl -X POST "http://127.0.0.1:8000/search/all/save" ^
  -H "Content-Type: application/json" ^
  -d "{\"query\":\"flashattention\",\"limit\":10}"
```

The dashboard supports paper filtering, PDF resolve/download/parse, mock
extraction, one-click Process Paper, loading the latest extraction, and mock RAG
ask.
