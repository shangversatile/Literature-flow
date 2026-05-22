import re
from pathlib import Path

import fitz


PROJECT_ROOT = Path(__file__).resolve().parents[4]
ASSET_STORAGE_DIR = PROJECT_ROOT / "storage" / "assets"

CAPTION_START_RE = re.compile(r"^(Figure|Fig\.|Table)\s+\d+", re.IGNORECASE)
TABLE_START_RE = re.compile(r"^Table\s+\d+", re.IGNORECASE)


def storage_path_for_display(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def clean_caption_line(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip()


def collect_caption(lines: list[str], start_index: int) -> tuple[str, int]:
    caption_lines = [clean_caption_line(lines[start_index])]
    index = start_index + 1

    while index < len(lines) and len(caption_lines) < 4:
        line = clean_caption_line(lines[index])
        if not line:
            break
        if CAPTION_START_RE.match(line):
            break
        caption_lines.append(line)
        index += 1

    return " ".join(caption_lines).strip(), index


def collect_table_text(lines: list[str], start_index: int) -> str:
    table_lines: list[str] = []
    index = start_index

    while index < len(lines) and len(table_lines) < 12:
        line = clean_caption_line(lines[index])
        if not line:
            if table_lines:
                break
            index += 1
            continue
        if table_lines and CAPTION_START_RE.match(line):
            break
        table_lines.append(line)
        index += 1

    return "\n".join(table_lines).strip()


def caption_assets_from_page(text: str, page_number: int, start_index: int) -> list[dict]:
    lines = text.splitlines()
    assets: list[dict] = []
    asset_index = start_index
    index = 0

    while index < len(lines):
        line = clean_caption_line(lines[index])
        if not CAPTION_START_RE.match(line):
            index += 1
            continue

        caption, next_index = collect_caption(lines, index)
        is_table = TABLE_START_RE.match(line) is not None
        assets.append(
            {
                "asset_type": "table_caption" if is_table else "figure_caption",
                "asset_index": asset_index,
                "page_number": page_number,
                "caption": caption,
                "local_path": None,
                "text_content": caption,
            }
        )
        asset_index += 1

        if is_table:
            table_text = collect_table_text(lines, next_index)
            if table_text:
                assets.append(
                    {
                        "asset_type": "table_text",
                        "asset_index": asset_index,
                        "page_number": page_number,
                        "caption": caption,
                        "local_path": None,
                        "text_content": table_text,
                    }
                )
                asset_index += 1

        index = max(next_index, index + 1)

    return assets


def extract_pdf_assets(pdf_path: str, paper_id: int) -> list[dict]:
    source_path = Path(pdf_path)
    if not source_path.is_absolute():
        source_path = PROJECT_ROOT / source_path
    if not source_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    try:
        document = fitz.open(source_path)
    except Exception as exc:
        raise ValueError(f"Could not open PDF file: {pdf_path}") from exc

    paper_asset_dir = ASSET_STORAGE_DIR / str(paper_id)
    paper_asset_dir.mkdir(parents=True, exist_ok=True)
    assets: list[dict] = []
    asset_index = 1

    try:
        for page_offset, page in enumerate(document):
            page_number = page_offset + 1
            image_path = paper_asset_dir / f"page-{page_number:03d}.png"
            pixmap = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
            pixmap.save(image_path)

            assets.append(
                {
                    "asset_type": "page_image",
                    "asset_index": asset_index,
                    "page_number": page_number,
                    "caption": None,
                    "local_path": storage_path_for_display(image_path),
                    "text_content": None,
                }
            )
            asset_index += 1

            page_text = page.get_text("text") or ""
            caption_assets = caption_assets_from_page(page_text, page_number, asset_index)
            assets.extend(caption_assets)
            asset_index += len(caption_assets)
    finally:
        document.close()

    return assets
