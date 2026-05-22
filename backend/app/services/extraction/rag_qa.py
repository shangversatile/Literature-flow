import json
import math
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
    "or",
    "is",
    "are",
    "was",
    "were",
    "what",
    "how",
    "why",
    "does",
    "do",
    "did",
    "this",
    "that",
    "paper",
    "method",
    "approach",
}


def normalize_text(text: str | None) -> str:
    if not text:
        return ""

    value = text.lower()
    value = value.translate(str.maketrans("", "", string.punctuation))
    return re.sub(r"\s+", " ", value).strip()


def tokenize_query(question: str) -> list[str]:
    seen: set[str] = set()
    tokens: list[str] = []
    for token in normalize_text(question).split():
        if len(token) < 2 or token in STOP_WORDS or token in seen:
            continue
        tokens.append(token)
        seen.add(token)
    return tokens


def important_phrases(question: str, query_tokens: list[str]) -> list[str]:
    normalized = normalize_text(question)
    phrases: list[str] = []
    if len(normalized.split()) >= 3:
        phrases.append(normalized)

    for index in range(len(query_tokens) - 1):
        phrases.append(f"{query_tokens[index]} {query_tokens[index + 1]}")
    return phrases


def count_term(text: str, token: str) -> int:
    return len(re.findall(rf"\b{re.escape(token)}\b", text))


def chunk_tokens(chunk: PaperChunk) -> list[str]:
    return normalize_text(chunk.text).split()


def compute_idf(query_tokens: list[str], chunks: list[PaperChunk]) -> dict[str, float]:
    total_docs = max(len(chunks), 1)
    idf: dict[str, float] = {}
    normalized_chunks = [normalize_text(chunk.text) for chunk in chunks]

    for token in query_tokens:
        doc_freq = sum(1 for text in normalized_chunks if count_term(text, token) > 0)
        idf[token] = math.log(1 + (total_docs - doc_freq + 0.5) / (doc_freq + 0.5))
    return idf


def compute_chunk_score(
    question: str,
    query_tokens: list[str],
    chunk: PaperChunk,
    avg_chunk_len: float,
    idf: dict[str, float] | None = None,
) -> float:
    del question

    text = normalize_text(chunk.text)
    section = normalize_text(chunk.section_title)
    terms = text.split()
    chunk_len = max(len(terms), 1)
    avg_len = max(avg_chunk_len, 1.0)
    idf_values = idf or {token: 1.0 for token in query_tokens}
    score = 0.0
    k1 = 1.5
    b = 0.75

    for token in query_tokens:
        tf = count_term(text, token)
        if tf <= 0:
            continue

        denominator = tf + k1 * (1 - b + b * (chunk_len / avg_len))
        score += idf_values.get(token, 1.0) * ((tf * (k1 + 1)) / denominator)

        if token in text[:500]:
            score += 0.15
        if section and token in section:
            score += 0.25

    for phrase in important_phrases(" ".join(query_tokens), query_tokens):
        if phrase and phrase in text:
            score += 0.35

    intro_terms = {"introduction", "background", "motivation", "overview", "problem"}
    if set(query_tokens) & intro_terms and (chunk.page_start or 999) <= 2:
        score += 0.20

    return score


def matched_terms_for_chunk(query_tokens: list[str], chunk: PaperChunk) -> list[str]:
    text = normalize_text(chunk.text)
    section = normalize_text(chunk.section_title)
    return [
        token
        for token in query_tokens
        if count_term(text, token) > 0 or (section and token in section)
    ]


def retrieve_relevant_chunks(
    question: str,
    chunks: list[PaperChunk],
    top_k: int = 5,
) -> list[dict]:
    query_tokens = tokenize_query(question)
    if not chunks:
        return []

    tokenized_chunks = [chunk_tokens(chunk) for chunk in chunks]
    avg_chunk_len = sum(len(tokens) for tokens in tokenized_chunks) / len(tokenized_chunks)
    idf = compute_idf(query_tokens, chunks)
    scored_chunks: list[dict] = []

    for chunk in chunks:
        text = chunk.text or ""
        raw_score = compute_chunk_score(question, query_tokens, chunk, avg_chunk_len, idf)
        matched_terms = matched_terms_for_chunk(query_tokens, chunk)

        scored_chunks.append(
            {
                "chunk_index": chunk.chunk_index,
                "text": text,
                "score": raw_score,
                "page_start": chunk.page_start,
                "page_end": chunk.page_end,
                "section_title": chunk.section_title,
                "matched_terms": matched_terms,
                "retrieval_method": "bm25_like_v2",
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
            f"retrieval_score: {chunk.get('score')}\n"
            f"matched_terms: {chunk.get('matched_terms', [])}\n"
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
Answer only from the evidence chunks below. Cite relevant chunk_index values in the answer when possible.
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
    methods = sorted({chunk.get("retrieval_method", "unknown") for chunk in evidence_chunks})
    method_text = ", ".join(methods) if methods else "unknown"
    matched_terms = {
        chunk["chunk_index"]: chunk.get("matched_terms", []) for chunk in evidence_chunks
    }
    return {
        "answer": (
            "Mock RAG answer: no external API was called. "
            f"For paper '{paper.title}', retrieval_method={method_text}. "
            f"Top evidence chunk indices: {indices}. "
            f"Matched terms by chunk: {matched_terms}. "
            f"Question: {question}"
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
