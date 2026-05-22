import json
import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import ValidationError

from app.models.paper import Paper
from app.models.paper_chunk import PaperChunk
from app.schemas.extraction import LiteratureExtraction


PROJECT_ROOT = Path(__file__).resolve().parents[4]
BACKEND_ROOT = PROJECT_ROOT / "backend"
PROMPT_VERSION = "litflow_extraction_v1"

load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(BACKEND_ROOT / ".env")


def build_extraction_prompt(
    paper: Paper,
    chunks: list[PaperChunk],
    user_topic: str | None = None,
) -> str:
    authors = getattr(paper, "authors", None) or "Not available"
    chunk_text = "\n\n".join(
        f"CHUNK {chunk.chunk_index}:\n{chunk.text}" for chunk in chunks
    )

    return f"""
You are extracting structured information from an academic paper.
Return only valid JSON. Do not wrap the JSON in markdown.
Do not invent information. If the provided text does not contain an answer, write "Not specified in the provided text".
The evidence_chunk_indices field must only contain chunk_index values shown below.

Paper metadata:
- title: {paper.title}
- authors: {authors}
- venue: {paper.venue}
- year: {paper.year}
- doi: {paper.doi}
- abstract: {paper.abstract}

User topic:
{user_topic or "Not specified"}

Required JSON shape:
{{
  "title": string or null,
  "authors": array of strings,
  "venue": string or null,
  "year": integer or null,
  "research_background": string,
  "research_problem": string,
  "methodology": string,
  "main_contributions": array of strings,
  "experiments_or_evaluation": string,
  "main_conclusions": string,
  "limitations": array of strings,
  "keywords": array of strings,
  "relevance_to_user_topic": string,
  "possible_followup_questions": array of strings,
  "evidence_chunk_indices": array of integers
}}

Paper chunks:
{chunk_text}
""".strip()


def parse_extraction_json(raw_text: str) -> LiteratureExtraction:
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM output is not valid JSON: {exc}") from exc

    try:
        return LiteratureExtraction.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"LLM JSON does not match LiteratureExtraction schema: {exc}") from exc


def mock_extract(
    paper: Paper,
    chunks: list[PaperChunk],
    user_topic: str | None = None,
) -> LiteratureExtraction:
    evidence = [chunk.chunk_index for chunk in chunks[:2]]
    return LiteratureExtraction(
        title=paper.title,
        authors=[],
        venue=paper.venue,
        year=paper.year,
        research_background=paper.abstract or "Not specified in the provided text",
        research_problem="Mock extraction: research problem will be extracted by an LLM in openai mode.",
        methodology="Mock extraction based on available chunks. Use openai mode for real methodology extraction.",
        main_contributions=[
            "Mock contribution generated to test the database extraction flow."
        ],
        experiments_or_evaluation="Mock extraction: experiments or evaluation are not analyzed in mock mode.",
        main_conclusions="Mock extraction created successfully from saved PaperChunk records.",
        limitations=["Not specified in the provided text"],
        keywords=[word for word in paper.title.split()[:5]],
        relevance_to_user_topic=(
            f"Mock relevance note for topic: {user_topic}"
            if user_topic
            else "Not specified in the provided text"
        ),
        possible_followup_questions=[
            "Which chunks contain the main method details?",
            "What evidence supports the paper's central claims?",
        ],
        evidence_chunk_indices=evidence,
    )


async def extract_with_openai(
    paper: Paper,
    chunks: list[PaperChunk],
    user_topic: str | None = None,
) -> tuple[LiteratureExtraction, str, str]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set. Add it to .env or your environment.")

    model_name = os.getenv("LLM_MODEL", "gpt-4.1-mini")

    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=api_key)
    prompt = build_extraction_prompt(paper, chunks, user_topic)
    response = await client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )

    raw_output = response.choices[0].message.content or ""
    extraction = parse_extraction_json(raw_output)
    return extraction, raw_output, model_name
