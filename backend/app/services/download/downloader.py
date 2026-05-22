import asyncio
from pathlib import Path

import httpx


PROJECT_ROOT = Path(__file__).resolve().parents[4]
PDF_DIR = PROJECT_ROOT / "storage" / "pdfs"
MAX_RETRIES = 3
RETRY_DELAYS = [1.0, 3.0, 5.0]


class PdfDownloadError(Exception):
    pass


def is_pdf_response(response: httpx.Response) -> bool:
    content_type = response.headers.get("content-type", "").lower()
    return "application/pdf" in content_type or response.content.startswith(b"%PDF")


def safe_pdf_filename(filename: str | None, paper_id: int) -> str:
    if not filename:
        return f"{paper_id}.pdf"

    name = Path(filename).name
    if not name.lower().endswith(".pdf"):
        name = f"{name}.pdf"
    return name


async def download_pdf(url: str, paper_id: int, filename: str | None = None) -> str:
    if not url:
        raise PdfDownloadError("PDF URL is required.")

    headers = {
        "Accept": "application/pdf,*/*",
        "User-Agent": "LitFlow/0.1",
    }

    async with httpx.AsyncClient(timeout=30.0, headers=headers, follow_redirects=True) as client:
        response: httpx.Response | None = None
        for attempt in range(MAX_RETRIES):
            try:
                response = await client.get(url)
            except httpx.TimeoutException as exc:
                if attempt == MAX_RETRIES - 1:
                    raise PdfDownloadError(
                        "PDF download timed out. Please try again later."
                    ) from exc
                await asyncio.sleep(RETRY_DELAYS[attempt])
                continue
            except httpx.HTTPError as exc:
                raise PdfDownloadError("PDF download failed. Please try again later.") from exc

            if response.status_code in {429} or 500 <= response.status_code < 600:
                if attempt == MAX_RETRIES - 1:
                    raise PdfDownloadError(
                        f"PDF download server returned an error: {response.status_code}."
                    )
                await asyncio.sleep(RETRY_DELAYS[attempt])
                continue

            break

    if response is None:
        raise PdfDownloadError("PDF download failed. Please try again later.")
    if response.status_code != 200:
        raise PdfDownloadError(f"PDF download returned an error: {response.status_code}.")
    if not is_pdf_response(response):
        raise PdfDownloadError("Downloaded content is not a PDF.")

    PDF_DIR.mkdir(parents=True, exist_ok=True)
    pdf_filename = safe_pdf_filename(filename, paper_id)
    pdf_path = PDF_DIR / pdf_filename
    pdf_path.write_bytes(response.content)
    return f"storage/pdfs/{pdf_filename}"
