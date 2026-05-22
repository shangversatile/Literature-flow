import re
import string
from datetime import datetime

from app.schemas.search import PaperSearchResult


TOP_VENUES = {
    "NeurIPS",
    "ICML",
    "ICLR",
    "ACL",
    "EMNLP",
    "CVPR",
    "KDD",
    "OSDI",
    "SOSP",
    "ASPLOS",
    "ISCA",
    "MLSys",
    "EuroSys",
    "VLDB",
    "SIGMOD",
}

VENUE_ALIASES = {
    "advances in neural information processing systems": "NeurIPS",
    "neurips": "NeurIPS",
    "international conference on machine learning": "ICML",
    "icml": "ICML",
    "international conference on learning representations": "ICLR",
    "iclr": "ICLR",
    "association for computational linguistics": "ACL",
    "acl": "ACL",
    "emnlp": "EMNLP",
    "conference on empirical methods in natural language processing": "EMNLP",
    "computer vision and pattern recognition": "CVPR",
    "cvpr": "CVPR",
    "knowledge discovery and data mining": "KDD",
    "kdd": "KDD",
    "operating systems design and implementation": "OSDI",
    "osdi": "OSDI",
    "symposium on operating systems principles": "SOSP",
    "sosp": "SOSP",
    "architectural support for programming languages and operating systems": "ASPLOS",
    "asplos": "ASPLOS",
    "international symposium on computer architecture": "ISCA",
    "isca": "ISCA",
    "mlsys": "MLSys",
    "european conference on computer systems": "EuroSys",
    "eurosys": "EuroSys",
    "vldb": "VLDB",
    "sigmod": "SIGMOD",
}


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


def normalize_venue(venue: str | None) -> str | None:
    if not venue:
        return None

    normalized = normalize_text(venue)
    return VENUE_ALIASES.get(normalized, venue)


def query_tokens(query: str) -> list[str]:
    return [token for token in normalize_text(query).split() if token]


def token_hit_ratio(tokens: list[str], text: str) -> float:
    if not tokens:
        return 0.0
    hits = sum(1 for token in tokens if token in text)
    return hits / len(tokens)


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

    score = 0.0
    if normalized_query and normalized_query in title_text:
        score += 0.45
    if normalized_query and normalized_query in abstract_text:
        score += 0.25

    score += min(token_hit_ratio(tokens, title_text) * 0.20, 0.20)
    score += min(token_hit_ratio(tokens, abstract_text) * 0.08, 0.08)
    score += min(token_hit_ratio(tokens, venue_text) * 0.02, 0.02)
    return round_score(score)


def has_external_id(external_ids: dict | None, names: set[str]) -> bool:
    if not external_ids:
        return False
    normalized_names = {name.lower() for name in names}
    return any(str(key).lower() in normalized_names for key in external_ids)


def compute_authority_score(
    venue: str | None,
    citation_count: int | None,
    year: int | None,
    sources: list[str],
    external_ids: dict | None,
) -> float:
    score = 0.0
    normalized_venue = normalize_venue(venue)
    citations = citation_count or 0

    if normalized_venue in TOP_VENUES:
        score += 0.35

    if citations >= 1000:
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
    score = 0.0
    if open_access_pdf_url:
        score += 0.45
    if doi:
        score += 0.20
    if url:
        score += 0.10
    if has_external_id(external_ids, {"ArXiv"}):
        score += 0.20
    if has_external_id(external_ids, {"SemanticScholar", "CorpusId", "OpenAlex"}):
        score += 0.05
    return round_score(score)


def score_paper_result(result: PaperSearchResult, query: str) -> PaperSearchResult:
    normalized_venue = normalize_venue(result.venue)
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
        citation_count=result.citation_count,
        year=result.year,
        sources=result.sources,
        external_ids=result.external_ids,
    )
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
        0.40 * result.relevance_score
        + 0.30 * result.authority_score
        + 0.20 * result.frontier_score
        + 0.10 * result.accessibility_score
    )
    result.final_score = round_score(final_score)
    result.quality_score = result.final_score
    return result
