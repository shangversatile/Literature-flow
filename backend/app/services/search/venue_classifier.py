import re
import string


CORE_NOTE = (
    "Built-in CORE-style conference mapping is incomplete and configurable; "
    "full CORE data can be imported later."
)
CORE_UNRANKED_NOTE = (
    "Conference not found in the current built-in CORE-style mapping; "
    "full CORE list can be imported later."
)
JOURNAL_NOTE = (
    "Journal quartile requires imported SCImago or JCR data; not available "
    "in current local mapping."
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
    "the web conference": "WWW",
    "www": "WWW",
    "mlsys": "MLSys",
    "osdi": "OSDI",
    "sosp": "SOSP",
    "asplos": "ASPLOS",
    "isca": "ISCA",
    "sigmod": "SIGMOD",
    "vldb": "VLDB",
    "usenix atc": "USENIX ATC",
    "nsdi": "NSDI",
    "pldi": "PLDI",
    "popl": "POPL",
    "colt": "COLT",
    "aistats": "AISTATS",
    "uai": "UAI",
    "eurosys": "EuroSys",
    "arxiv": "arXiv",
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


def _classification(
    venue_normalized: str | None,
    venue_type: str,
    publication_status: str,
    rank_source: str | None,
    rank_value: str,
    rank_note: str,
) -> dict:
    return {
        "venue_normalized": venue_normalized,
        "venue_type": venue_type,
        "publication_type": venue_type,
        "publication_status": publication_status,
        "rank_source": rank_source,
        "rank_value": rank_value,
        "rank_note": rank_note,
        "venue_rank": rank_value,
        "venue_rank_source": rank_source,
        "venue_rank_note": rank_note,
    }


def _conference_rank(venue_normalized: str) -> str:
    if venue_normalized in A_STAR_CONFERENCES:
        return "A*"
    if venue_normalized in A_CONFERENCES:
        return "A"
    if venue_normalized in B_CONFERENCES:
        return "B"
    return "Unranked"


def _looks_like_journal(venue: str | None) -> bool:
    value = _normalize_lookup_text(venue)
    journal_terms = [
        "journal",
        "transactions",
        "nature",
        "science",
        "jmlr",
        "proceedings of the national academy of sciences",
        "pnas",
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
    external_ids: dict | None = None,
    sources: list[str] | None = None,
) -> dict:
    del external_ids, sources

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

    if venue_normalized in CONFERENCE_VENUES:
        return _classification(
            venue_normalized,
            "conference",
            "published",
            "CORE",
            _conference_rank(venue_normalized),
            CORE_NOTE,
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
            "CORE",
            "Unranked",
            CORE_UNRANKED_NOTE,
        )

    return _classification(
        venue_normalized,
        "unknown",
        "unknown",
        None,
        "Unknown",
        "Venue type could not be inferred from the current local mapping.",
    )
