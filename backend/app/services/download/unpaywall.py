import os
from pathlib import Path
from urllib.parse import quote

import httpx
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[4]
BACKEND_ROOT = PROJECT_ROOT / "backend"
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(BACKEND_ROOT / ".env")


class UnpaywallEmailMissingError(Exception):
    pass


class UnpaywallLookupError(Exception):
    pass


def get_unpaywall_email() -> str:
    email = os.getenv("UNPAYWALL_EMAIL", "").strip()
    if not email:
        raise UnpaywallEmailMissingError(
            "UNPAYWALL_EMAIL is required to resolve PDF URLs by DOI."
        )
    return email


async def get_unpaywall_pdf_url(doi: str, email: str) -> str | None:
    if not doi:
        return None

    url = f"https://api.unpaywall.org/v2/{quote(doi.strip(), safe='')}"
    params = {"email": email}
    headers = {
        "Accept": "application/json",
        "User-Agent": "LitFlow/0.1",
    }

    async with httpx.AsyncClient(timeout=10.0, headers=headers) as client:
        try:
            response = await client.get(url, params=params)
        except httpx.TimeoutException as exc:
            raise UnpaywallLookupError(
                "Unpaywall request timed out. Please try again later."
            ) from exc
        except httpx.HTTPError as exc:
            raise UnpaywallLookupError(
                "Unpaywall request failed. Please try again later."
            ) from exc

    if response.status_code == 404:
        return None
    if response.status_code != 200:
        raise UnpaywallLookupError(
            f"Unpaywall API returned an error: {response.status_code}."
        )

    payload = response.json()
    best_location = payload.get("best_oa_location") or {}
    return best_location.get("url_for_pdf")
