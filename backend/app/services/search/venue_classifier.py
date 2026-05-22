import re
import string


RANK_SOURCE = "LitFlow-default-venue-rank-v1"
RANK_NOTE = "Default configurable LitFlow ranking; not a universal official ranking."

S_RANK_VENUES = {
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
A_RANK_VENUES = {
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
B_RANK_VENUES = {
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
CONFERENCE_VENUES = S_RANK_VENUES | A_RANK_VENUES | B_RANK_VENUES

VENUE_ALIASES = {
    "advances in neural information processing systems": "NeurIPS",
    "neurips": "NeurIPS",
    "international conference on machine learning": "ICML",
    "icml": "ICML",
    "international conference on learning representations": "ICLR",
    "iclr": "ICLR",
    "aaai": "AAAI",
    "aaai conference on artificial intelligence": "AAAI",
    "ijcai": "IJCAI",
    "acl": "ACL",
    "association for computational linguistics": "ACL",
    "emnlp": "EMNLP",
    "naacl": "NAACL",
    "cvpr": "CVPR",
    "iccv": "ICCV",
    "eccv": "ECCV",
    "kdd": "KDD",
    "sigkdd": "KDD",
    "knowledge discovery and data mining": "KDD",
    "the web conference": "WWW",
    "www": "WWW",
    "osdi": "OSDI",
    "sosp": "SOSP",
    "asplos": "ASPLOS",
    "isca": "ISCA",
    "mlsys": "MLSys",
    "eurosys": "EuroSys",
    "vldb": "VLDB",
    "sigmod": "SIGMOD",
    "usenix atc": "USENIX ATC",
    "nsdi": "NSDI",
    "pldi": "PLDI",
    "popl": "POPL",
    "colt": "COLT",
    "aistats": "AISTATS",
    "uai": "UAI",
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
    "micro": "MICRO",
    "sc": "SC",
    "pact": "PACT",
    "corl": "CoRL",
    "rss": "RSS",
    "arxiv": "arXiv",
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
    return VENUE_ALIASES.get(key, stripped)


def _rank_for_conference(venue_normalized: str) -> str:
    if venue_normalized in S_RANK_VENUES:
        return "S"
    if venue_normalized in A_RANK_VENUES:
        return "A"
    if venue_normalized in B_RANK_VENUES:
        return "B"
    return "Unknown"


def _looks_like_journal(venue: str) -> bool:
    value = _normalize_lookup_text(venue)
    journal_terms = [
        "journal",
        "transactions",
        "proceedings of the",
        "nature",
        "science",
        "jmlr",
        "pmlr",
    ]
    return any(term in value for term in journal_terms)


def classify_publication_venue(
    venue: str | None,
    external_ids: dict | None = None,
    sources: list[str] | None = None,
) -> dict:
    del external_ids, sources

    venue_normalized = normalize_venue_name(venue)
    if not venue_normalized:
        return {
            "venue_normalized": None,
            "publication_type": "unknown",
            "publication_status": "unknown",
            "venue_rank": "Unknown",
            "venue_rank_source": RANK_SOURCE,
            "venue_rank_note": RANK_NOTE,
        }

    venue_text = _normalize_lookup_text(venue_normalized)
    original_text = _normalize_lookup_text(venue)
    if venue_normalized == "arXiv" or "arxiv" in original_text or "preprint" in original_text:
        return {
            "venue_normalized": "arXiv",
            "publication_type": "preprint",
            "publication_status": "unpublished",
            "venue_rank": "Unpublished",
            "venue_rank_source": RANK_SOURCE,
            "venue_rank_note": RANK_NOTE,
        }

    if venue_normalized in CONFERENCE_VENUES:
        return {
            "venue_normalized": venue_normalized,
            "publication_type": "conference",
            "publication_status": "published",
            "venue_rank": _rank_for_conference(venue_normalized),
            "venue_rank_source": RANK_SOURCE,
            "venue_rank_note": RANK_NOTE,
        }

    if _looks_like_journal(venue_normalized) or _looks_like_journal(venue_text):
        return {
            "venue_normalized": venue_normalized,
            "publication_type": "journal",
            "publication_status": "published",
            "venue_rank": "Journal",
            "venue_rank_source": RANK_SOURCE,
            "venue_rank_note": RANK_NOTE,
        }

    return {
        "venue_normalized": venue_normalized,
        "publication_type": "unknown",
        "publication_status": "unknown",
        "venue_rank": "Unknown",
        "venue_rank_source": RANK_SOURCE,
        "venue_rank_note": RANK_NOTE,
    }
