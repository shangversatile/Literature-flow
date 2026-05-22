from pathlib import Path

import fitz


def extract_text_from_pdf(pdf_path: str, max_pages: int | None = None) -> dict:
    path = Path(pdf_path)
    if not path.is_absolute():
        project_root = Path(__file__).resolve().parents[4]
        path = project_root / path

    if not path.exists():
        raise FileNotFoundError(f"PDF file not found: {path}")

    pages: list[dict] = []
    full_text_parts: list[str] = []

    with fitz.open(path) as document:
        page_count = document.page_count
        limit = page_count if max_pages is None else min(max_pages, page_count)

        for index in range(limit):
            page = document.load_page(index)
            text = page.get_text("text").strip()
            page_number = index + 1
            pages.append({"page_number": page_number, "text": text})
            if text:
                full_text_parts.append(f"\n\n[Page {page_number}]\n{text}")

    full_text = "".join(full_text_parts).strip()
    extracted_pages = sum(1 for page in pages if page["text"].strip())

    return {
        "full_text": full_text,
        "page_count": page_count,
        "extracted_pages": extracted_pages,
        "pages": pages,
        "error": (
            "No extractable text found. The PDF may be scanned or image-only."
            if not full_text
            else None
        ),
    }
