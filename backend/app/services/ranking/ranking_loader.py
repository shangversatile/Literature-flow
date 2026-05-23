import csv
import re
import string
from functools import lru_cache
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[4]
CORE_RANKING_CSV = PROJECT_ROOT / "storage" / "rankings" / "core_conference_rankings.csv"
JOURNAL_RANKING_CSV = PROJECT_ROOT / "storage" / "rankings" / "journal_rankings.csv"


def normalize_key(text: str | None) -> str:
    if not text:
        return ""

    translator = str.maketrans("", "", string.punctuation)
    value = text.lower().translate(translator)
    return re.sub(r"\s+", " ", value).strip()


def alias_keys(venue_key: str) -> list[str]:
    if not venue_key:
        return []
    if (
        re.search(r"\b(?:nips|neurips)\b", venue_key)
        or "neural information processing systems" in venue_key
    ):
        return [
            "neurips",
            "nips",
            "advances in neural information processing systems",
            "neural information processing systems",
        ]
    return []


def is_safe_partial_key(key: str) -> bool:
    if len(key) < 6:
        return False
    short_exact_only = {"sc", "www"}
    return key not in short_exact_only


@lru_cache(maxsize=1)
def load_core_conference_rankings() -> dict:
    if not CORE_RANKING_CSV.exists():
        return {}

    rankings: dict[str, dict[str, str]] = {}
    with CORE_RANKING_CSV.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            ranking = {
                "acronym": (row.get("acronym") or "").strip(),
                "name": (row.get("name") or "").strip(),
                "aliases": (row.get("aliases") or "").strip(),
                "rank": (row.get("rank") or "").strip(),
                "source": (row.get("source") or "").strip(),
                "year": (row.get("year") or "").strip(),
                "note": (row.get("note") or "").strip(),
            }

            values = [ranking["acronym"], ranking["name"]]
            values.extend(
                alias.strip()
                for alias in ranking["aliases"].split(";")
                if alias.strip()
            )
            for value in values:
                key = normalize_key(value)
                if key:
                    rankings[key] = ranking

    return rankings


def lookup_core_conference_rank(venue: str | None) -> dict | None:
    venue_key = normalize_key(venue)
    if not venue_key:
        return None

    rankings = load_core_conference_rankings()
    direct_match = rankings.get(venue_key)
    if direct_match:
        return direct_match

    for alias_key in alias_keys(venue_key):
        alias_match = rankings.get(alias_key)
        if alias_match:
            return alias_match

    for key, row in rankings.items():
        if key and is_safe_partial_key(key) and key in venue_key:
            return row

    for alias_key in alias_keys(venue_key):
        for key, row in rankings.items():
            if (
                key
                and is_safe_partial_key(key)
                and (key in alias_key or alias_key in key)
            ):
                return row

    if is_safe_partial_key(venue_key):
        for key, row in rankings.items():
            if key and is_safe_partial_key(key) and venue_key in key:
                return row

    return None


@lru_cache(maxsize=1)
def load_journal_rankings() -> dict:
    if not JOURNAL_RANKING_CSV.exists():
        return {}

    rankings: dict[str, dict[str, str]] = {}
    with JOURNAL_RANKING_CSV.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            ranking = {
                "journal_title": (row.get("journal_title") or "").strip(),
                "aliases": (row.get("aliases") or "").strip(),
                "rank_source": (row.get("rank_source") or "").strip(),
                "quartile": (row.get("quartile") or "").strip(),
                "year": (row.get("year") or "").strip(),
                "category": (row.get("category") or "").strip(),
                "note": (row.get("note") or "").strip(),
            }

            values = [ranking["journal_title"]]
            values.extend(
                alias.strip()
                for alias in ranking["aliases"].split(";")
                if alias.strip()
            )
            for value in values:
                key = normalize_key(value)
                if key:
                    rankings[key] = ranking

    return rankings


def lookup_journal_rank(venue: str | None) -> dict | None:
    venue_key = normalize_key(venue)
    if not venue_key:
        return None

    rankings = load_journal_rankings()
    direct_match = rankings.get(venue_key)
    if direct_match:
        return direct_match

    for key, row in rankings.items():
        if key and key in venue_key:
            return row

    return None
