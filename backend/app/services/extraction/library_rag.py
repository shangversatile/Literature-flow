import json
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlmodel import Session, select

from app.models.paper import Paper
from app.models.paper_chunk import PaperChunk
from app.models.topic import PaperTopic, ResearchTopic
from app.services.extraction.rag_qa import (
    chunk_tokens,
    compute_chunk_score,
    compute_idf,
    matched_terms_for_chunk,
    tokenize_query,
)
from app.services.topics import normalize_topic_name


PROJECT_ROOT = Path(__file__).resolve().parents[4]
BACKEND_ROOT = PROJECT_ROOT / "backend"

load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(BACKEND_ROOT / ".env")


def retrieve_library_chunks(
    session: Session,
    question: str,
    top_k: int = 10,
    topic: str | None = None,
) -> list[dict]:
    limit = max(1, min(top_k, 30))
    query_tokens = tokenize_query(question)

    statement = select(PaperChunk, Paper).join(Paper, Paper.id == PaperChunk.paper_id)
    if topic and topic.strip():
        normalized_topic = normalize_topic_name(topic)
        statement = (
            statement.join(PaperTopic, PaperTopic.paper_id == Paper.id)
            .join(ResearchTopic, ResearchTopic.id == PaperTopic.topic_id)
            .where(ResearchTopic.normalized_name == normalized_topic)
        )

    rows = session.exec(statement).all()
    if not rows:
        return []

    chunks = [row[0] for row in rows]
    tokenized_chunks = [chunk_tokens(chunk) for chunk in chunks]
    avg_chunk_len = sum(len(tokens) for tokens in tokenized_chunks) / len(tokenized_chunks)
    idf = compute_idf(query_tokens, chunks)
    scored_chunks: list[dict] = []

    for chunk, paper in rows:
        raw_score = compute_chunk_score(question, query_tokens, chunk, avg_chunk_len, idf)
        scored_chunks.append(
            {
                "paper_id": paper.id,
                "paper_title": paper.title,
                "paper_year": paper.year,
                "paper_venue": paper.venue,
                "chunk_index": chunk.chunk_index,
                "text": chunk.text or "",
                "score": raw_score,
                "page_start": chunk.page_start,
                "page_end": chunk.page_end,
                "section_title": chunk.section_title,
                "matched_terms": matched_terms_for_chunk(query_tokens, chunk),
                "retrieval_method": "library_bm25_like_v3",
            }
        )

    max_score = max((chunk["score"] for chunk in scored_chunks), default=0.0)
    if max_score > 0:
        for chunk in scored_chunks:
            chunk["score"] = round(chunk["score"] / max_score, 4)
        scored_chunks.sort(
            key=lambda item: (-item["score"], item["paper_id"], item["chunk_index"])
        )
    else:
        for chunk in scored_chunks:
            chunk["score"] = 0.0
        scored_chunks.sort(key=lambda item: (item["paper_id"], item["chunk_index"]))

    return scored_chunks[:limit]


def build_library_rag_prompt(
    question: str,
    evidence_chunks: list[dict],
    topic: str | None = None,
) -> str:
    topic_text = topic or "All topics"
    chunk_text = "\n\n".join(
        (
            f"EVIDENCE:\n"
            f"paper_id: {chunk.get('paper_id')}\n"
            f"paper_title: {chunk.get('paper_title')}\n"
            f"paper_year: {chunk.get('paper_year')}\n"
            f"paper_venue: {chunk.get('paper_venue')}\n"
            f"chunk_index: {chunk.get('chunk_index')}\n"
            f"score: {chunk.get('score')}\n"
            f"matched_terms: {chunk.get('matched_terms', [])}\n"
            f"page_start: {chunk.get('page_start')}\n"
            f"page_end: {chunk.get('page_end')}\n"
            f"section_title: {chunk.get('section_title')}\n"
            f"text: {chunk.get('text', '')}"
        )
        for chunk in evidence_chunks
    )

    return f"""
You are answering a question across an academic paper library.
Return only valid JSON. Do not wrap the JSON in markdown.
Answer only from the evidence chunks below. Cite relevant paper_id and chunk_index pairs in the answer when useful.
If the evidence does not contain enough information, answer exactly:
"The provided library evidence does not contain enough information to answer this question."
Do not invent facts, methods, results, datasets, or conclusions that are not present in the evidence.
The evidence field must only contain paper_id and chunk_index pairs shown below.

Topic filter:
{topic_text}

Question:
{question}

Required JSON shape:
{{
  "answer": "...",
  "evidence": [
    {{"paper_id": 1, "chunk_index": 5}}
  ]
}}

Evidence chunks:
{chunk_text}
""".strip()


def mock_answer_library_question(
    question: str,
    evidence_chunks: list[dict],
    topic: str | None = None,
) -> dict:
    top_evidence = [
        {
            "paper_id": chunk["paper_id"],
            "chunk_index": chunk["chunk_index"],
            "score": chunk["score"],
        }
        for chunk in evidence_chunks[:5]
    ]
    methods = sorted({chunk.get("retrieval_method", "unknown") for chunk in evidence_chunks})
    method_text = ", ".join(methods) if methods else "unknown"
    topic_text = topic or "All topics"
    return {
        "answer": (
            "Mock library RAG answer: no external API was called. "
            f"Topic filter: {topic_text}. retrieval_method={method_text}. "
            f"Top evidence paper/chunk pairs: {top_evidence}. "
            f"Question: {question}"
        )
    }


def parse_library_rag_json(raw_text: str) -> dict:
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
    if "answer" not in data or not isinstance(data["answer"], str):
        raise ValueError("LLM JSON field 'answer' must be a string.")
    evidence = data.get("evidence", [])
    if not isinstance(evidence, list):
        raise ValueError("LLM JSON field 'evidence' must be a list.")
    return data


async def answer_library_with_openai(
    question: str,
    evidence_chunks: list[dict],
    topic: str | None = None,
) -> tuple[str, str]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set. Add it to .env or your environment.")

    model_name = os.getenv("LLM_MODEL", "gpt-4.1-mini")

    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=api_key)
    prompt = build_library_rag_prompt(question, evidence_chunks, topic)
    response = await client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )

    raw_output = response.choices[0].message.content or ""
    data = parse_library_rag_json(raw_output)
    return data["answer"], raw_output
