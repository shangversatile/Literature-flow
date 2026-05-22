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
