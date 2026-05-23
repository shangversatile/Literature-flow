import re
import string
from datetime import datetime

from app.schemas.search import PaperSearchResult
from app.services.search.venue_classifier import (
    classify_publication_venue,
    normalize_venue_name,
)


def clamp_score(score: float) -> float:
    return min(max(score, 0.0), 1.0)


def round_score(score: float) -> float:
    return round(clamp_score(score), 4)


def normalize_text(text: str | None) -> str:
    if not text:
        return ""

    translator = str.maketrans("", "", string.punctuation)
    value = text.lower().translate(translator)
    return re.sub(r"\s+", " ", value).strip()


def query_tokens(query: str) -> list[str]:
    return [token for token in normalize_text(query).split() if token]


def token_hit_ratio(tokens: list[str], text: str) -> float:
    if not tokens:
        return 0.0
    hits = sum(1 for token in tokens if token in text)
    return hits / len(tokens)


def token_overlap_ratio(query_tokens_value: list[str], text_tokens_value: list[str]) -> float:
    if not query_tokens_value:
        return 0.0
    text_tokens_set = set(text_tokens_value)
    hits = sum(1 for token in query_tokens_value if token in text_tokens_set)
    return hits / len(query_tokens_value)


def keyword_score(text: str, keywords: list[str], weight: float, max_score: float) -> float:
    hits = sum(1 for keyword in keywords if keyword in text)
    return min(hits * weight, max_score)


def compute_relevance_score(
    query: str,
    title: str | None,
    abstract: str | None,
    venue: str | None,
) -> float:
    normalized_query = normalize_text(query)
    title_text = normalize_text(title)
    abstract_text = normalize_text(abstract)
    venue_text = normalize_text(venue)
    tokens = query_tokens(query)
    title_tokens = [token for token in title_text.split() if token]
    title_overlap = token_overlap_ratio(tokens, title_tokens)

    score = 0.0
    if normalized_query and normalized_query in title_text:
        score += 0.60
    if normalized_query and normalized_query in abstract_text:
        score += 0.25

    if title_overlap >= 0.90:
        score += 0.25
    elif title_overlap >= 0.75:
        score += 0.18
    elif title_overlap >= 0.50:
        score += 0.10

    score += min(token_hit_ratio(tokens, title_text) * 0.15, 0.15)
    score += min(token_hit_ratio(tokens, abstract_text) * 0.08, 0.08)
    score += min(token_hit_ratio(tokens, venue_text) * 0.02, 0.02)
    return round_score(score)


def has_external_id(external_ids: dict | None, names: set[str]) -> bool:
    if not external_ids:
        return False
    normalized_names = {name.lower() for name in names}
    return any(str(key).lower() in normalized_names for key in external_ids)


def is_open_access_like(
    doi: str | None,
    url: str | None,
    open_access_pdf_url: str | None,
    external_ids: dict | None,
) -> bool:
    if open_access_pdf_url:
        return True

    values = [doi or "", url or ""]
    if external_ids:
        values.extend(str(key) for key in external_ids)
        values.extend(str(value) for value in external_ids.values())

    normalized = " ".join(values).lower()
    return any(
        marker in normalized
        for marker in [
            "arxiv",
            "arxiv.org",
            "10.48550/arxiv",
            "dblp:journals/corr",
            "corr abs",
        ]
    )


def compute_authority_score(
    venue: str | None,
    rank_value: str | None,
    citation_count: int | None,
    year: int | None,
    sources: list[str],
    external_ids: dict | None,
) -> float:
    score = 0.0
    citations = citation_count or 0

    if rank_value == "A*":
        score += 0.40
    elif rank_value == "A":
        score += 0.28
    elif rank_value == "B":
        score += 0.18
    elif rank_value == "C":
        score += 0.10
    elif rank_value == "Q1":
        score += 0.30
    elif rank_value == "Q2":
        score += 0.20
    elif rank_value == "Q3":
        score += 0.10
    elif rank_value == "Q4":
        score += 0.05
    elif rank_value == "Q-Unknown":
        score += 0.08
    elif rank_value in {"Unpublished", "Unranked"}:
        score += 0.03

    if citations >= 3000:
        score += 0.30
    elif citations >= 1000:
        score += 0.25
    elif citations >= 300:
        score += 0.20
    elif citations >= 100:
        score += 0.15
    elif citations >= 30:
        score += 0.08

    if year:
        current_year = datetime.now().year
        paper_age = max(1, current_year - year + 1)
        citation_velocity = citations / paper_age
        if citation_velocity >= 100:
            score += 0.15
        elif citation_velocity >= 30:
            score += 0.10
        elif citation_velocity >= 10:
            score += 0.05

    unique_sources = {source for source in sources if source}
    if len(unique_sources) >= 3:
        score += 0.15
    elif len(unique_sources) == 2:
        score += 0.10
    elif len(unique_sources) == 1:
        score += 0.03

    if has_external_id(external_ids, {"DOI", "ArXiv"}):
        score += 0.05

    return round_score(score)


def compute_foundation_score(result: PaperSearchResult) -> float:
    score = 0.0
    citations = result.citation_count or 0
    current_year = datetime.now().year
    rank_value = result.rank_value
    title_text = normalize_text(result.title)

    if citations >= 3000:
        score += 0.45
    elif citations >= 1000:
        score += 0.35
    elif citations >= 300:
        score += 0.25

    if rank_value in {"A*", "Q1"}:
        score += 0.25
    elif rank_value in {"A", "Q2"}:
        score += 0.18

    if result.year and current_year - result.year >= 2 and citations >= 500:
        score += 0.15

    if any(
        keyword in title_text
        for keyword in [
            "attention",
            "transformer",
            "flashattention",
            "operator",
            "diffusion",
            "world model",
        ]
    ):
        score += 0.05
    return round_score(score)


def compute_implementation_score(result: PaperSearchResult) -> float:
    score = 0.0
    title_text = normalize_text(result.title)
    abstract_text = normalize_text(result.abstract)
    combined_text = f"{title_text} {abstract_text}"
    venue = normalize_venue_name(result.venue) or result.venue or ""
    systems_venues = {
        "OSDI",
        "SOSP",
        "ASPLOS",
        "MLSys",
        "EuroSys",
        "NSDI",
        "USENIX ATC",
        "SIGMOD",
        "VLDB",
        "ISCA",
        "NeurIPS",
        "ICML",
        "ICLR",
    }
    strong_keywords = [
        "flashattention",
        "attention kernel",
        "ioaware",
        "io aware",
        "ioawareness",
        "hbm",
        "sram",
        "gpu",
        "memoryefficient",
        "memory efficient",
        "tiling",
        "kernel",
        "runtime",
        "serving",
        "inference",
        "kv cache",
        "cache",
        "batching",
        "scheduler",
        "throughput",
        "latency",
        "triton",
        "cuda",
        "parallelism",
        "work partitioning",
    ]

    title_hits = sum(1 for keyword in strong_keywords if keyword in title_text)
    abstract_hits = sum(1 for keyword in strong_keywords if keyword in abstract_text)
    score += min(title_hits * 0.15, 0.45)
    score += min(abstract_hits * 0.06, 0.30)

    has_systems_keyword = any(keyword in combined_text for keyword in strong_keywords)
    if venue in systems_venues and has_systems_keyword:
        score += 0.10
    if (result.citation_count or 0) >= 500:
        score += 0.10
    if is_open_access_like(result.doi, result.url, result.open_access_pdf_url, result.external_ids):
        score += 0.05

    return round_score(score)


def compute_survey_value_score(result: PaperSearchResult) -> float:
    score = 0.0
    title = normalize_text(result.title)
    abstract = normalize_text(result.abstract)
    title_terms = [
        "survey",
        "review",
        "benchmark",
        "taxonomy",
        "leaderboard",
        "evaluation suite",
        "dataset",
    ]

    has_title_signal = any(keyword in title for keyword in title_terms)
    if has_title_signal:
        score += 0.35
        if any(keyword in abstract for keyword in ["survey", "benchmark", "leaderboard", "dataset", "taxonomy"]):
            score += 0.25
        if (result.citation_count or 0) >= 300:
            score += 0.20
        if result.rank_value in {"A*", "A", "Q1"}:
            score += 0.15
    elif any(keyword in abstract for keyword in ["survey", "benchmark", "leaderboard", "dataset", "taxonomy"]):
        score += 0.10

    return round_score(score)


def compute_frontier_score(
    year: int | None,
    citation_count: int | None,
    venue: str | None,
    sources: list[str],
) -> float:
    if not year:
        return 0.0

    current_year = datetime.now().year
    citations = citation_count or 0
    age = current_year - year
    source_names = {source.lower() for source in sources}
    score = 0.0

    if year == current_year:
        score += 0.35
    elif year == current_year - 1:
        score += 0.30
    elif year == current_year - 2:
        score += 0.20
    elif year >= current_year - 4:
        score += 0.10

    if age <= 1 and citations >= 50:
        score += 0.20
    elif age <= 1 and citations >= 10:
        score += 0.10

    if "arxiv" in source_names and age <= 1:
        score += 0.10
    if normalize_text(venue) == "arxiv" and age <= 1:
        score += 0.05

    return round_score(score)


def compute_accessibility_score(
    doi: str | None,
    url: str | None,
    open_access_pdf_url: str | None,
    external_ids: dict | None,
) -> float:
    if open_access_pdf_url or is_open_access_like(doi, url, open_access_pdf_url, external_ids):
        return 0.85
    if doi:
        return 0.55
    if url:
        return 0.45
    if has_external_id(external_ids, {"SemanticScholar", "CorpusId", "OpenAlex"}):
        return 0.25
    return 0.10


def score_paper_result(result: PaperSearchResult, query: str) -> PaperSearchResult:
    classification = classify_publication_venue(
        result.venue,
        external_ids=result.external_ids,
        sources=result.sources,
    )
    result.venue_normalized = classification["venue_normalized"]
    result.venue_type = classification["venue_type"]
    result.publication_type = classification["publication_type"]
    result.publication_status = classification["publication_status"]
    result.rank_source = classification["rank_source"]
    result.rank_value = classification["rank_value"]
    result.rank_note = classification["rank_note"]
    result.venue_rank = classification["venue_rank"]
    result.venue_rank_source = classification["venue_rank_source"]
    result.venue_rank_note = classification["venue_rank_note"]

    normalized_venue = normalize_venue_name(result.venue)
    if normalized_venue:
        result.venue = normalized_venue

    result.relevance_score = compute_relevance_score(
        query=query,
        title=result.title,
        abstract=result.abstract,
        venue=result.venue,
    )
    result.authority_score = compute_authority_score(
        venue=result.venue,
        rank_value=result.rank_value,
        citation_count=result.citation_count,
        year=result.year,
        sources=result.sources,
        external_ids=result.external_ids,
    )
    result.foundation_score = compute_foundation_score(result)
    result.implementation_score = compute_implementation_score(result)
    result.survey_value_score = compute_survey_value_score(result)
    result.frontier_score = compute_frontier_score(
        year=result.year,
        citation_count=result.citation_count,
        venue=result.venue,
        sources=result.sources,
    )
    result.accessibility_score = compute_accessibility_score(
        doi=result.doi,
        url=result.url,
        open_access_pdf_url=result.open_access_pdf_url,
        external_ids=result.external_ids,
    )

    final_score = (
        0.25 * result.relevance_score
        + 0.25 * result.authority_score
        + 0.20 * result.foundation_score
        + 0.20 * result.implementation_score
        + 0.05 * result.frontier_score
        + 0.05 * result.accessibility_score
    )
    result.final_score = round_score(final_score)
    result.quality_score = result.final_score
    return result
