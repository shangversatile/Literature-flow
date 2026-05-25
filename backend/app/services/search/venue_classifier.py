import re
import string

from app.services.ranking.ranking_loader import (
    lookup_core_conference_rank,
    lookup_journal_rank,
    lookup_manual_paper_override,
)


FALLBACK_NOTE = "Fallback built-in ranking; import CORE CSV for authoritative local mapping."
FALLBACK_UNRANKED_NOTE = (
    "Fallback built-in ranking; conference is not ranked in the local fallback. "
    "Import CORE CSV for authoritative local mapping."
)
JOURNAL_NOTE = (
    "Journal detected but not found in local journal ranking CSV."
)
PREPRINT_NOTE = "Preprint-only record; no peer-reviewed venue detected."

A_STAR_CONFERENCES = {
    "NeurIPS",
    "ICML",
    "ICLR",
    "ACL",
    "CVPR",
    "ICCV",
    "ECCV",
    "OSDI",
    "SOSP",
    "ASPLOS",
    "ISCA",
    "SIGMOD",
    "VLDB",
    "FOCS",
    "STOC",
}
A_CONFERENCES = {
    "AAAI",
    "IJCAI",
    "EMNLP",
    "NAACL",
    "KDD",
    "WWW",
    "MLSys",
    "EuroSys",
    "USENIX ATC",
    "NSDI",
    "PLDI",
    "POPL",
    "COLT",
    "AISTATS",
    "UAI",
    "CoRL",
    "RSS",
}
B_CONFERENCES = {
    "EACL",
    "COLING",
    "WACV",
    "ICRA",
    "IROS",
    "CIKM",
    "ICDM",
    "PODS",
    "EDBT",
    "ICDE",
    "HPCA",
    "MICRO",
    "SC",
    "PACT",
}
CONFERENCE_VENUES = A_STAR_CONFERENCES | A_CONFERENCES | B_CONFERENCES

VENUE_ALIASES = {
    "advances in neural information processing systems": "NeurIPS",
    "conference on neural information processing systems": "NeurIPS",
    "neural information processing systems": "NeurIPS",
    "neurips": "NeurIPS",
    "nips": "NeurIPS",
    "international conference on machine learning": "ICML",
    "icml": "ICML",
    "international conference on learning representations": "ICLR",
    "iclr": "ICLR",
    "aaai": "AAAI",
    "aaai conference on artificial intelligence": "AAAI",
    "association for the advancement of artificial intelligence": "AAAI",
    "ijcai": "IJCAI",
    "international joint conference on artificial intelligence": "IJCAI",
    "acl": "ACL",
    "association for computational linguistics": "ACL",
    "annual meeting of the association for computational linguistics": "ACL",
    "emnlp": "EMNLP",
    "empirical methods in natural language processing": "EMNLP",
    "conference on empirical methods in natural language processing": "EMNLP",
    "naacl": "NAACL",
    "north american chapter of the association for computational linguistics": "NAACL",
    "cvpr": "CVPR",
    "ieeecvf conference on computer vision and pattern recognition": "CVPR",
    "computer vision and pattern recognition": "CVPR",
    "iccv": "ICCV",
    "international conference on computer vision": "ICCV",
    "eccv": "ECCV",
    "european conference on computer vision": "ECCV",
    "kdd": "KDD",
    "sigkdd": "KDD",
    "acm sigkdd conference on knowledge discovery and data mining": "KDD",
    "knowledge discovery and data mining": "KDD",
    "the web conference": "WWW",
    "international world wide web conference": "WWW",
    "world wide web conference": "WWW",
    "www": "WWW",
    "mlsys": "MLSys",
    "conference on machine learning and systems": "MLSys",
    "machine learning and systems": "MLSys",
    "osdi": "OSDI",
    "usenix symposium on operating systems design and implementation": "OSDI",
    "operating systems design and implementation": "OSDI",
    "sosp": "SOSP",
    "acm symposium on operating systems principles": "SOSP",
    "acm sigops symposium on operating systems principles": "SOSP",
    "symposium on operating systems principles": "SOSP",
    "asplos": "ASPLOS",
    "acm international conference on architectural support for programming languages and operating systems": "ASPLOS",
    "international conference on architectural support for programming languages and operating systems": "ASPLOS",
    "architectural support for programming languages and operating systems": "ASPLOS",
    "isca": "ISCA",
    "international symposium on computer architecture": "ISCA",
    "acmieee international symposium on computer architecture": "ISCA",
    "sigmod": "SIGMOD",
    "acm sigmod international conference on management of data": "SIGMOD",
    "international conference on management of data": "SIGMOD",
    "vldb": "VLDB",
    "international conference on very large data bases": "VLDB",
    "proceedings of the vldb endowment": "VLDB",
    "very large data bases": "VLDB",
    "usenix atc": "USENIX ATC",
    "usenix annual technical conference": "USENIX ATC",
    "annual technical conference": "USENIX ATC",
    "nsdi": "NSDI",
    "usenix symposium on networked systems design and implementation": "NSDI",
    "networked systems design and implementation": "NSDI",
    "pldi": "PLDI",
    "acm sigplan conference on programming language design and implementation": "PLDI",
    "programming language design and implementation": "PLDI",
    "popl": "POPL",
    "acm sigplan symposium on principles of programming languages": "POPL",
    "principles of programming languages": "POPL",
    "colt": "COLT",
    "aistats": "AISTATS",
    "uai": "UAI",
    "eurosys": "EuroSys",
    "european conference on computer systems": "EuroSys",
    "acm european conference on computer systems": "EuroSys",
    "arxiv": "arXiv",
    "nature": "Nature",
    "science": "Science",
    "nature machine intelligence": "Nature Machine Intelligence",
    "nature methods": "Nature Methods",
    "nature biotechnology": "Nature Biotechnology",
    "jmlr": "Journal of Machine Learning Research",
    "journal of machine learning research": "Journal of Machine Learning Research",
    "tmlr": "Transactions on Machine Learning Research",
    "transactions on machine learning research": "Transactions on Machine Learning Research",
    "pnas": "Proceedings of the National Academy of Sciences",
    "proceedings of the national academy of sciences": "Proceedings of the National Academy of Sciences",
    "scientific reports": "Scientific Reports",
    "patterns": "Patterns",
    "focs": "FOCS",
    "stoc": "STOC",
    "eacl": "EACL",
    "coling": "COLING",
    "wacv": "WACV",
    "icra": "ICRA",
    "iros": "IROS",
    "cikm": "CIKM",
    "icdm": "ICDM",
    "pods": "PODS",
    "edbt": "EDBT",
    "icde": "ICDE",
    "hpca": "HPCA",
    "ieee international symposium on highperformance computer architecture": "HPCA",
    "international symposium on highperformance computer architecture": "HPCA",
    "micro": "MICRO",
    "ieeeacm international symposium on microarchitecture": "MICRO",
    "international symposium on microarchitecture": "MICRO",
    "sc": "SC",
    "international conference for high performance computing networking storage and analysis": "SC",
    "supercomputing conference": "SC",
    "pact": "PACT",
    "corl": "CoRL",
    "rss": "RSS",
}


def _normalize_lookup_text(text: str | None) -> str:
    if not text:
        return ""
    translator = str.maketrans("", "", string.punctuation)
    value = text.lower().translate(translator)
    return re.sub(r"\s+", " ", value).strip()


def normalize_venue_name(venue: str | None) -> str | None:
    if not venue:
        return None

    stripped = venue.strip()
    if not stripped:
        return None

    key = _normalize_lookup_text(stripped)
    if re.search(r"\b(?:nips|neurips)\b", key):
        return "NeurIPS"
    if "neural information processing systems" in key:
        return "NeurIPS"
    alias_match = VENUE_ALIASES.get(key)
    if alias_match:
        return alias_match
    csv_rank = lookup_core_conference_rank(stripped)
    if csv_rank:
        acronym = csv_rank["acronym"]
        return "NeurIPS" if _normalize_lookup_text(acronym) == "nips" else acronym
    return stripped


def _classification(
    venue_normalized: str | None,
    venue_type: str,
    publication_status: str,
    rank_source: str | None,
    rank_value: str,
    rank_note: str,
    publication_type: str | None = None,
    impact_label: str | None = None,
) -> dict:
    return {
        "venue_normalized": venue_normalized,
        "venue_type": venue_type,
        "publication_type": publication_type or venue_type,
        "publication_status": publication_status,
        "rank_source": rank_source,
        "rank_value": rank_value,
        "rank_note": rank_note,
        "venue_rank": rank_value,
        "venue_rank_source": rank_source,
        "venue_rank_note": rank_note,
        "impact_label": impact_label,
    }


def _conference_rank(venue_normalized: str) -> str:
    if venue_normalized in A_STAR_CONFERENCES:
        return "A*"
    if venue_normalized in A_CONFERENCES:
        return "A"
    if venue_normalized in B_CONFERENCES:
        return "B"
    return "Unranked"


def _normalize_conference_acronym(value: str | None) -> str | None:
    normalized = normalize_venue_name(value)
    if normalized == "NeurIPS":
        return "NeurIPS"
    return normalized or value


def _looks_like_journal(venue: str | None) -> bool:
    value = _normalize_lookup_text(venue)
    journal_terms = [
        "journal",
        "transactions",
        "nature",
        "science",
        "jmlr",
        "tmlr",
        "proceedings of the national academy of sciences",
        "pnas",
        "patterns",
        "cell",
        "communications of the acm",
    ]
    return any(term in value for term in journal_terms)


def _looks_like_preprint(venue: str | None) -> bool:
    value = _normalize_lookup_text(venue)
    return any(
        term in value
        for term in ["arxiv", "biorxiv", "medrxiv", "preprint", "openreview"]
    )


def _looks_like_conference(venue: str | None) -> bool:
    value = _normalize_lookup_text(venue)
    return any(term in value for term in ["conference", "symposium", "workshop"])


def classify_publication_venue(
    venue: str | None,
    title: str | None = None,
    doi: str | None = None,
    external_ids: dict | None = None,
    sources: list[str] | None = None,
) -> dict:
    del external_ids, sources

    manual_override = lookup_manual_paper_override(title, doi)
    if manual_override:
        return _classification(
            manual_override["venue_normalized"] or venue,
            manual_override["venue_type"] or "unknown",
            manual_override["publication_status"] or "unknown",
            manual_override["rank_source"] or "manual-override",
            manual_override["rank_value"] or "Influential",
            manual_override["note"],
            publication_type=manual_override["publication_type"] or None,
            impact_label=manual_override["impact_label"] or None,
        )

    venue_normalized = normalize_venue_name(venue)
    if not venue_normalized:
        return _classification(
            None,
            "unknown",
            "unknown",
            None,
            "Unknown",
            "No venue detected.",
        )

    if _looks_like_preprint(venue_normalized):
        return _classification(
            "arXiv" if _normalize_lookup_text(venue_normalized) == "arxiv" else venue_normalized,
            "preprint",
            "unpublished",
            None,
            "Unpublished",
            PREPRINT_NOTE,
        )

    csv_rank = lookup_core_conference_rank(venue) or lookup_core_conference_rank(
        venue_normalized
    )
    if csv_rank:
        rank_source = csv_rank["source"]
        if rank_source:
            rank_source = f"{rank_source}-local-csv"
        normalized_acronym = _normalize_conference_acronym(
            csv_rank["acronym"] or venue_normalized
        )
        rank_note = csv_rank["note"]
        if normalized_acronym == "NeurIPS" and _normalize_lookup_text(venue) in {
            "nips",
            "neural information processing systems",
            "advances in neural information processing systems",
        }:
            rank_note = f"{rank_note} Alias matched NeurIPS/NIPS.".strip()
        return _classification(
            normalized_acronym or venue_normalized,
            "conference",
            "published",
            rank_source or "CORE-local-csv",
            csv_rank["rank"] or "Unknown",
            rank_note,
        )

    if venue_normalized in CONFERENCE_VENUES:
        return _classification(
            venue_normalized,
            "conference",
            "published",
            "LitFlow-fallback",
            _conference_rank(venue_normalized),
            FALLBACK_NOTE,
        )

    journal_rank = lookup_journal_rank(venue) or lookup_journal_rank(venue_normalized)
    if journal_rank:
        rank_source = journal_rank["rank_source"]
        if rank_source:
            rank_source = f"{rank_source}-local-csv"
        return _classification(
            journal_rank["journal_title"] or venue_normalized,
            "journal",
            "published",
            rank_source or "Journal-local-csv",
            journal_rank["quartile"] or "Unknown",
            journal_rank["note"],
        )

    if _looks_like_journal(venue_normalized):
        return _classification(
            venue_normalized,
            "journal",
            "published",
            "SCImago/JCR-ready",
            "Unknown",
            JOURNAL_NOTE,
        )

    if _looks_like_conference(venue_normalized):
        return _classification(
            venue_normalized,
            "conference",
            "published",
            "LitFlow-fallback",
            "Unranked",
            FALLBACK_UNRANKED_NOTE,
        )

    return _classification(
        venue_normalized,
        "unknown",
        "unknown",
        None,
        "Unknown",
        "Venue type could not be inferred from the current local mapping.",
    )
