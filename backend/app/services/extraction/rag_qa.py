import json
import os
import re
import string
from pathlib import Path

from dotenv import load_dotenv

from app.models.paper import Paper
from app.models.paper_chunk import PaperChunk


PROJECT_ROOT = Path(__file__).resolve().parents[4]
BACKEND_ROOT = PROJECT_ROOT / "backend"

load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(BACKEND_ROOT / ".env")

STOP_WORDS = {
    "the",
    "a",
    "an",
    "of",
    "in",
    "to",
    "and",
    "is",
    "are",
    "what",
    "how",
    "why",
}


def _normalize_question(question: str) -> list[str]:
    text = question.lower()
    text = text.translate(str.maketrans("", "", string.punctuation))
    return [word for word in text.split() if word and word not in STOP_WORDS]


def retrieve_relevant_chunks(
    question: str,
    chunks: list[PaperChunk],
    top_k: int = 5,
) -> list[dict]:
    keywords = _normalize_question(question)
    scored_chunks = []

    for chunk in chunks:
        text = chunk.text or ""
        lower_text = text.lower()
        early_text = lower_text[:500]
        raw_score = 0.0

        for keyword in keywords:
            matches = len(re.findall(rf"\b{re.escape(keyword)}\b", lower_text))
            raw_score += matches
            if keyword in early_text:
                raw_score += 0.5

        scored_chunks.append(
            {
                "chunk_index": chunk.chunk_index,
                "text": text,
                "score": raw_score,
                "page_start": chunk.page_start,
                "page_end": chunk.page_end,
                "section_title": chunk.section_title,
            }
        )

    max_score = max((chunk["score"] for chunk in scored_chunks), default=0.0)
    if max_score > 0:
        for chunk in scored_chunks:
            chunk["score"] = round(chunk["score"] / max_score, 4)
        scored_chunks.sort(key=lambda item: (-item["score"], item["chunk_index"]))
    else:
        for chunk in scored_chunks:
            chunk["score"] = 0.0
        scored_chunks.sort(key=lambda item: item["chunk_index"])

    return scored_chunks[:top_k]


def build_rag_prompt(
    paper: Paper,
    question: str,
    evidence_chunks: list[dict],
) -> str:
    chunk_text = "\n\n".join(
        (
            f"CHUNK {chunk['chunk_index']}:\n"
            f"page_start: {chunk.get('page_start')}\n"
            f"page_end: {chunk.get('page_end')}\n"
            f"section_title: {chunk.get('section_title')}\n"
            f"text: {chunk.get('text', '')}"
        )
        for chunk in evidence_chunks
    )

    return f"""
You are answering a question about one academic paper.
Return only valid JSON. Do not wrap the JSON in markdown.
Answer only from the evidence chunks below.
If the evidence chunks do not contain enough evidence, answer exactly:
"The provided chunks do not contain enough evidence to answer this question."
Do not invent facts, methods, results, datasets, or conclusions that are not present in the chunks.
The evidence_chunk_indices field must only contain chunk_index values shown below.

Paper metadata:
- title: {paper.title}
- year: {paper.year}
- venue: {paper.venue}
- doi: {paper.doi}

Question:
{question}

Required JSON shape:
{{
  "answer": "...",
  "evidence_chunk_indices": [0, 2]
}}

Evidence chunks:
{chunk_text}
""".strip()


def mock_answer_question(
    paper: Paper,
    question: str,
    evidence_chunks: list[dict],
) -> dict:
    indices = [chunk["chunk_index"] for chunk in evidence_chunks]
    return {
        "answer": (
            "Mock RAG answer: no external API was called. "
            f"For paper '{paper.title}', the keyword retriever selected chunks "
            f"{indices} for the question: {question}"
        ),
        "evidence_chunk_indices": indices,
    }


def parse_rag_json(raw_text: str) -> dict:
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
        raise ValueError("LLM JSON must be an object.")
    if "answer" not in data:
        raise ValueError("LLM JSON is missing required field: answer.")
    if "evidence_chunk_indices" not in data:
        raise ValueError(
            "LLM JSON is missing required field: evidence_chunk_indices."
        )
    if not isinstance(data["answer"], str):
        raise ValueError("LLM JSON field 'answer' must be a string.")
    if not isinstance(data["evidence_chunk_indices"], list) or not all(
        isinstance(index, int) for index in data["evidence_chunk_indices"]
    ):
        raise ValueError("LLM JSON field 'evidence_chunk_indices' must be list[int].")

    return data


async def answer_with_openai(
    paper: Paper,
    question: str,
    evidence_chunks: list[dict],
) -> tuple[str, list[int], str]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set. Add it to .env or your environment.")

    model_name = os.getenv("LLM_MODEL", "gpt-4.1-mini")

    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=api_key)
    prompt = build_rag_prompt(paper, question, evidence_chunks)
    response = await client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )

    raw_output = response.choices[0].message.content or ""
    data = parse_rag_json(raw_output)
    return data["answer"], data["evidence_chunk_indices"], raw_output
