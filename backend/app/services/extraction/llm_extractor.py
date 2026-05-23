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

EMPTY_MARKERS = {
    "",
    "n/a",
    "none",
    "not specified",
    "not specified in the provided text",
    "unknown",
}

LIST_STRING_FIELDS = {
    "authors",
    "main_contributions",
    "limitations",
    "keywords",
    "possible_followup_questions",
}

LIST_INT_FIELDS = {"evidence_chunk_indices"}

STRING_FIELDS = {
    "research_background",
    "research_problem",
    "methodology",
    "experiments_or_evaluation",
    "main_conclusions",
    "relevance_to_user_topic",
}


def is_empty_marker(value: str) -> bool:
    return value.strip().lower() in EMPTY_MARKERS


def normalize_string_list(value: object) -> list[str]:
    if isinstance(value, list):
        normalized = []
        for item in value:
            if item is None:
                continue
            if isinstance(item, str):
                if not is_empty_marker(item):
                    normalized.append(item.strip())
                continue
            if isinstance(item, dict):
                normalized.append(json.dumps(item, ensure_ascii=False))
                continue
            normalized.append(str(item))
        return normalized

    if value is None:
        return []
    if isinstance(value, str):
        stripped = value.strip()
        return [] if is_empty_marker(stripped) else [stripped]
    if isinstance(value, dict):
        return [json.dumps(value, ensure_ascii=False)]
    return []


def normalize_int_list(value: object) -> list[int]:
    if not isinstance(value, list):
        return []

    normalized = []
    for item in value:
        if isinstance(item, bool):
            continue
        if isinstance(item, int):
            normalized.append(item)
            continue
        if isinstance(item, str):
            try:
                normalized.append(int(item))
            except ValueError:
                continue
    return normalized


def normalize_string(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return "" if is_empty_marker(value) else value
    if isinstance(value, list):
        parts = []
        for item in value:
            if item is None:
                continue
            if isinstance(item, str):
                if not is_empty_marker(item):
                    parts.append(item.strip())
                continue
            if isinstance(item, dict):
                parts.append(json.dumps(item, ensure_ascii=False))
                continue
            parts.append(str(item))
        return "\n".join(parts)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def normalize_extraction_payload(payload: dict) -> dict:
    normalized = dict(payload)

    for field in LIST_STRING_FIELDS:
        normalized[field] = normalize_string_list(normalized.get(field))

    for field in LIST_INT_FIELDS:
        normalized[field] = normalize_int_list(normalized.get(field))

    for field in STRING_FIELDS:
        normalized[field] = normalize_string(normalized.get(field))

    return normalized


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
Do not invent information. If the provided text does not contain a string answer, write "Not specified in the provided text".
For list fields, return a JSON array of strings. If a list field is not specified, use [].
All list fields must be JSON arrays, not strings.
limitations must be an array of strings, not a string. If limitations are not specified, use [].
keywords, authors, main_contributions, limitations, and possible_followup_questions must be JSON arrays.
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
    if not isinstance(data, dict):
        raise ValueError("LLM output JSON must be an object")

    normalized_data = normalize_extraction_payload(data)

    try:
        return LiteratureExtraction.model_validate(normalized_data)
    except ValidationError as exc:
        fields = sorted(
            {
                ".".join(str(part) for part in error.get("loc", ()))
                for error in exc.errors()
            }
        )
        raw_preview = json.dumps(data, ensure_ascii=False)[:1000]
        raise ValueError(
            "LLM JSON does not match LiteratureExtraction schema. "
            f"fields={fields}; raw_json_preview={raw_preview}; validation_error={exc}"
        ) from exc


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
