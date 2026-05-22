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
- `venue_normalized`
- `venue_type`
- `publication_type`
- `publication_status`
- `rank_source`
- `rank_value`
- `rank_note`
- `venue_rank`

`final_score` is computed as:

```text
0.40 * relevance_score
+ 0.30 * authority_score
+ 0.20 * frontier_score
+ 0.10 * accessibility_score
```

`quality_score` is still returned for compatibility and is set to `final_score`.
`venue_rank` is also kept for compatibility and is set to `rank_value`.

Conference rank uses CORE-style `A*`, `A`, `B`, `C`, `Unranked`, and `Unknown`
categories. LitFlow first checks the local CSV file:

```text
storage/rankings/core_conference_rankings.csv
```

The CSV columns are:

```text
acronym,name,rank,source,year,note
```

The checked-in file is a small development seed, not a complete official list.
You can replace it with a complete CSV prepared from the CORE / ICORE portal.
When a venue is not found in the CSV, LitFlow falls back to its small built-in
mapping with `rank_source = LitFlow-fallback`. Journal quartile support is
SCImago/JCR-ready, but requires imported data, so journals are currently marked
`Unknown` unless local quartile data is added later. Preprint-only papers are
marked `Unpublished`. The system no longer uses `S` or `Journal` as rank values.

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

Downloaded PDFs are saved with readable filenames when enough metadata is
available:

```text
{year}-{short-title}-{venue}-{rank}-id{paper_id}.pdf
```

Older files such as `storage/pdfs/1.pdf` remain valid and are not migrated.

Enriched paper display API:

These endpoints read saved database papers and compute display-only score and
venue rank fields at request time. They do not modify the database.

```bash
curl "http://127.0.0.1:8000/papers/enriched"
curl "http://127.0.0.1:8000/papers/1/enriched"
```

The enriched responses include `final_score`, `venue_normalized`, `venue_type`,
`publication_type`, `publication_status`, `rank_source`, `rank_value`,
`rank_note`, and compatibility fields such as `venue_rank`. These fields are
computed at read time for Dashboard display.

Single-paper export:

```bash
curl "http://127.0.0.1:8000/papers/1/export/markdown"
curl "http://127.0.0.1:8000/papers/1/export/bibtex"
```

Markdown export includes frontmatter metadata, venue rank fields, abstract, and
the latest LLM extraction when available. If no extraction exists yet, LitFlow
still exports a basic literature-note template with "No extraction available
yet." in the structured summary sections. BibTeX export produces a simple
`@inproceedings`, `@article`, or `@misc` entry based on the detected venue type.
The Dashboard also provides `Export Markdown` and `Export BibTeX` buttons in the
paper detail panel.

In the paper detail panel, `Preview Markdown` fetches the Markdown export and
shows the Markdown text inside the page without downloading a file. `Export
Markdown` downloads the `.md` file and uses the filename from the backend
`Content-Disposition` header.

Exported filenames use readable metadata:

```text
{year}-{short-title}-{venue}-{rank}-id{paper_id}.md
{year}-{short-title}-{venue}-{rank}-id{paper_id}.bib
```

Example:

```text
2023-flashattention-2-iclr-a-star-id1.md
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

PDF figures, tables, and unstructured assets MVP:

Run `download-pdf` first so `Paper.local_pdf_path` points to a local PDF file,
then extract page images and simple captions.

```bash
curl -X POST "http://127.0.0.1:8000/papers/1/extract-assets"
curl "http://127.0.0.1:8000/papers/1/assets"
```

Extracted assets are saved under:

```text
storage/assets/{paper_id}/
```

Page images are served from:

```text
http://127.0.0.1:8000/static/assets/{paper_id}/page-001.png
```

This is an MVP. It supports page image rendering and simple `Figure`, `Fig.`,
and `Table` caption detection. It does not support OCR, precise figure/table
cropping, or multimodal chart understanding. Markdown export includes a
`Figures and Tables` section with extracted page images, figure captions, table
captions, and raw table text when available.

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

You can search papers directly from the Dashboard with the top Search panel.
For example:

- query: `flashattention`
- limit: `10`

The frontend first calls `/search/all` and shows results without saving them.
Select the papers you want, then click `Save Selected` to call
`/search/save-selected`. `Save All Results` is still available as a secondary
action and calls `/search/all/save`. Successful saves refresh the Dashboard
automatically.

You can also call the backend endpoint manually:

```bash
curl -X POST "http://127.0.0.1:8000/search/all/save" ^
  -H "Content-Type: application/json" ^
  -d "{\"query\":\"flashattention\",\"limit\":10}"
```

The dashboard supports Search Only, Select Results, Save Selected, Save All
Results, paper filtering, PDF resolve/download/parse, mock extraction, one-click
Process Paper, loading the latest extraction, and mock RAG ask.

The paper detail Actions area includes an Extraction Mode selector with `openai`
and `mock`. `Run Extraction` and `Process Paper` use the currently selected mode.

The paper detail panel also provides a structured reading workspace:

- latest extraction displayed as structured summary sections
- PDF preview for downloaded files under `/static/pdfs/{file}`
- Markdown preview without downloading
- Markdown and BibTeX export buttons
