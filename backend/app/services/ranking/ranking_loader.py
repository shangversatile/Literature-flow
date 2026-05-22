import csv
import re
import string
from functools import lru_cache
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[4]
CORE_RANKING_CSV = PROJECT_ROOT / "storage" / "rankings" / "core_conference_rankings.csv"


def normalize_key(text: str | None) -> str:
    if not text:
        return ""

    translator = str.maketrans("", "", string.punctuation)
    value = text.lower().translate(translator)
    return re.sub(r"\s+", " ", value).strip()


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
                "rank": (row.get("rank") or "").strip(),
                "source": (row.get("source") or "").strip(),
                "year": (row.get("year") or "").strip(),
                "note": (row.get("note") or "").strip(),
            }

            for value in (ranking["acronym"], ranking["name"]):
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

    for key, row in rankings.items():
        if key and key in venue_key:
            return row

    return None
