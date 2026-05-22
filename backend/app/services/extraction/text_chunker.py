def chunk_text_pages(
    pages: list[dict],
    chunk_size: int = 1800,
    overlap: int = 200,
) -> list[dict]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be greater than or equal to 0 and less than chunk_size")

    text_parts: list[dict] = []
    cursor = 0

    for page in pages:
        page_text = page.get("text", "").strip()
        if not page_text:
            continue

        # Keep page spans so chunks can later point back to source pages.
        page_number = page.get("page_number")
        text = f"\n\n[Page {page_number}]\n{page_text}"
        start = cursor
        end = cursor + len(text)
        text_parts.append(
            {
                "start": start,
                "end": end,
                "page_number": page_number,
                "text": text,
            }
        )
        cursor = end

    full_text = "".join(part["text"] for part in text_parts).strip()
    if not full_text:
        return []

    chunks: list[dict] = []
    start = 0
    chunk_index = 0

    while start < len(full_text):
        end = min(start + chunk_size, len(full_text))
        chunk_text = full_text[start:end].strip()
        if not chunk_text:
            break

        page_numbers = [
            part["page_number"]
            for part in text_parts
            if part["page_number"] is not None
            and part["end"] > start
            and part["start"] < end
        ]

        chunks.append(
            {
                "chunk_index": chunk_index,
                "text": chunk_text,
                "char_count": len(chunk_text),
                "token_estimate": len(chunk_text) // 4,
                "page_start": min(page_numbers) if page_numbers else None,
                "page_end": max(page_numbers) if page_numbers else None,
                "section_title": None,
            }
        )

        if end >= len(full_text):
            break
        start = end - overlap
        chunk_index += 1

    return chunks
