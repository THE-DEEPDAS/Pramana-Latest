from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pymupdf as fitz
from pdf2image import convert_from_path
from pdf2image.exceptions import PDFInfoNotInstalledError


@dataclass(frozen=True)
class PageText:
    page_number: int
    text: str


def document_id_for(path: Path) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "_", path.stem).strip("_")


def render_pdf_pages(pdf_path: Path, output_dir: Path, dpi: int = 200) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    existing = sorted(output_dir.glob("page_*.png"))
    try:
        page_count = fitz.open(pdf_path).page_count
    except Exception:
        page_count = 0
    if page_count and len(existing) == page_count:
        return existing
    image_paths: list[Path] = []
    try:
        images = convert_from_path(str(pdf_path), dpi=dpi)
        for index, image in enumerate(images, start=1):
            out = output_dir / f"page_{index:04d}.png"
            image.save(out)
            image_paths.append(out)
        return image_paths
    except (PDFInfoNotInstalledError, FileNotFoundError, Exception):
        doc = fitz.open(pdf_path)
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        for index, page in enumerate(doc, start=1):
            out = output_dir / f"page_{index:04d}.png"
            if out.exists():
                image_paths.append(out)
                continue
            pix = page.get_pixmap(matrix=mat, alpha=False)
            pix.save(str(out))
            image_paths.append(out)
        return image_paths


def extract_pdf_text(pdf_path: Path) -> list[PageText]:
    doc = fitz.open(pdf_path)
    pages: list[PageText] = []
    for index, page in enumerate(doc, start=1):
        text_parts = [page.get_text("text").strip()]
        native_tables = _native_table_markdown(page)
        if native_tables:
            text_parts.append(native_tables)
        layout_summary = _layout_numeric_groups(page)
        if layout_summary:
            text_parts.append(layout_summary)
        pages.append(PageText(page_number=index, text="\n\n".join(part for part in text_parts if part)))
    return pages


def _native_table_markdown(page: fitz.Page) -> str:
    try:
        tables = page.find_tables()
    except Exception:
        return ""
    markdown_tables: list[str] = []
    for table_index, table in enumerate(tables, start=1):
        try:
            rows = table.extract()
        except Exception:
            continue
        normalized = _normalize_table_rows(rows)
        if len(normalized) < 2:
            continue
        header = _dedupe_headers(normalized[0])
        body = normalized[1:]
        if not header or not any(any(cell for cell in row) for row in body):
            continue
        width = len(header)
        lines = [
            f"### Native PDF Table {table_index}",
            "| " + " | ".join(header) + " |",
            "| " + " | ".join(["---"] * width) + " |",
        ]
        for row in body:
            padded = (row + [""] * width)[:width]
            lines.append("| " + " | ".join(_escape_markdown_cell(cell) for cell in padded) + " |")
        markdown_tables.append("\n".join(lines))
    if not markdown_tables:
        return ""
    return "## Native PDF Tables\n" + "\n\n".join(markdown_tables)


def _normalize_table_rows(rows: list[list[Any]]) -> list[list[str]]:
    normalized: list[list[str]] = []
    max_width = 0
    for row in rows:
        cells = [re.sub(r"\s+", " ", str(cell or "")).strip() for cell in row]
        if not any(cells):
            continue
        max_width = max(max_width, len(cells))
        normalized.append(cells)
    if max_width == 0:
        return []
    return [(row + [""] * max_width)[:max_width] for row in normalized]


def _dedupe_headers(row: list[str]) -> list[str]:
    headers: list[str] = []
    seen: dict[str, int] = {}
    for index, cell in enumerate(row, start=1):
        header = cell.strip() or f"Column {index}"
        key = header.lower()
        count = seen.get(key, 0) + 1
        seen[key] = count
        if count > 1:
            header = f"{header} {count}"
        headers.append(_escape_markdown_cell(header))
    return headers


def _escape_markdown_cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ").strip()


def _layout_numeric_groups(page: fitz.Page) -> str:
    lines = _page_text_lines(page)
    period_groups = _period_groups(lines)
    if not period_groups:
        return ""

    numeric_lines = [line for line in lines if _looks_like_number(line["text"])]
    if len(numeric_lines) < 4:
        return ""

    unit = _page_unit(lines)
    category_labels = _category_labels(lines)
    groups: list[str] = []
    seen_groups: set[str] = set()
    for period_group in period_groups:
        period_items = period_group["items"]
        min_x = min(item["cx"] for item in period_items) - 40
        max_x = max(item["cx"] for item in period_items) + 40
        top_y = _nearest_heading_bottom(lines, min_x, max_x, period_group["y0"])
        metric = _nearest_metric_heading(lines, min_x, max_x, period_group["y0"])
        if not metric:
            continue

        values = [
            line
            for line in numeric_lines
            if min_x <= line["cx"] <= max_x and top_y <= line["cy"] <= period_group["cy"] - 5
        ]
        if len(values) < len(period_items) * 2:
            continue

        rows = _numeric_rows(values, period_items)
        if not rows:
            continue

        row_parts = []
        for idx, row in enumerate(rows):
            label = category_labels[idx] if idx < len(category_labels) else f"Row {idx + 1}"
            if label.startswith("Row ") and idx == len(rows) - 1 and len(rows) > 1:
                label = "Total"
            cells = []
            for item in period_items:
                value = row.get(item["label"])
                if value:
                    cells.append(f"{item['label']} {value}")
            if cells:
                row_parts.append(f"{label}: {'; '.join(cells)}")
        if row_parts:
            unit_text = f" ({unit})" if unit else ""
            group = f"Layout numeric group{unit_text} - {metric}: " + ". ".join(row_parts) + "."
            key = re.sub(r"\W+", " ", group.lower()).strip()
            if key not in seen_groups:
                groups.append(group)
                seen_groups.add(key)

    if not groups:
        return ""
    return "## Layout Numeric Groups\n" + "\n".join(f"- {group}" for group in groups)


def _page_text_lines(page: fitz.Page) -> list[dict]:
    items: list[dict] = []
    for block in page.get_text("dict").get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            text = "".join(span.get("text", "") for span in line.get("spans", [])).strip()
            if not text:
                continue
            x0, y0, x1, y1 = line["bbox"]
            items.append(
                {
                    "text": re.sub(r"\s+", " ", text).strip(),
                    "x0": x0,
                    "y0": y0,
                    "x1": x1,
                    "y1": y1,
                    "cx": (x0 + x1) / 2,
                    "cy": (y0 + y1) / 2,
                }
            )
    return items


def _period_tokens(text: str) -> list[str]:
    patterns = [
        r"\b(?:Q[1-4]|H[12]|FY)[-\s]?\d{2,4}\b",
        r"\b(?:Q[1-4]|H[12])\s*FY\s*\d{2,4}\b",
        r"\bFY\s*\d{2,4}[-/]\d{2,4}\b",
        r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[-\s]?\d{2,4}\b",
    ]
    tokens: list[str] = []
    for pattern in patterns:
        tokens.extend(re.findall(pattern, text, flags=re.IGNORECASE))
    return [re.sub(r"\s+", " ", token).strip() for token in tokens]


def _period_items(line: dict, tokens: list[str]) -> list[dict]:
    if len(tokens) == 1:
        return [{"label": tokens[0], "cx": line["cx"]}]
    width = max(1.0, line["x1"] - line["x0"])
    items = []
    for idx, token in enumerate(tokens):
        cx = line["x0"] + (idx / max(1, len(tokens) - 1)) * width
        items.append({"label": token, "cx": cx})
    return items


def _period_groups(lines: list[dict]) -> list[dict]:
    period_lines = []
    for line in lines:
        tokens = _period_tokens(line["text"])
        if not tokens:
            continue
        clean = re.sub(r"\s+", " ", line["text"]).strip()
        if len(tokens) == 1 and clean.upper() != tokens[0].upper() and len(clean) > len(tokens[0]) + 4:
            continue
        period_lines.append(line)

    groups: list[dict] = []
    used: set[int] = set()
    for idx, line in enumerate(period_lines):
        if idx in used:
            continue
        tokens = _period_tokens(line["text"])
        if len(tokens) >= 2:
            groups.append(
                {
                    "items": _period_items(line, tokens),
                    "y0": line["y0"],
                    "cy": line["cy"],
                }
            )
            used.add(idx)
            continue

        siblings = [
            (other_idx, other)
            for other_idx, other in enumerate(period_lines)
            if other_idx not in used
            and abs(other["cy"] - line["cy"]) <= 12
            and _period_tokens(other["text"])
        ]
        if len(siblings) < 2:
            continue
        siblings = sorted(siblings, key=lambda item: item[1]["cx"])
        labels = [_period_tokens(other["text"])[0].upper() for _, other in siblings]
        first_repeat_at = next(
            (pos for pos in range(1, len(labels)) if labels[pos] == labels[0]),
            len(siblings),
        )
        group_size = max(2, first_repeat_at)
        for start in range(0, len(siblings), group_size):
            group_siblings = siblings[start : start + group_size]
            if len(group_siblings) < 2:
                continue
            used.update(other_idx for other_idx, _ in group_siblings)
            groups.append(
                {
                    "items": [
                        {"label": _period_tokens(other["text"])[0], "cx": other["cx"]}
                        for _, other in group_siblings
                    ],
                    "y0": min(other["y0"] for _, other in group_siblings),
                    "cy": sum(other["cy"] for _, other in group_siblings) / len(group_siblings),
                }
            )
    return groups


def _looks_like_number(text: str) -> bool:
    clean = text.strip()
    return bool(re.fullmatch(r"\(?-?\d[\d,]*(?:\.\d+)?%?\)?", clean))


def _category_labels(lines: list[dict]) -> list[str]:
    labels = []
    for line in sorted(lines, key=lambda item: (item["y0"], item["x0"])):
        text = line["text"].strip()
        lower = text.lower()
        if _looks_like_number(text) or _period_tokens(text):
            continue
        if not text[:1].isalnum():
            continue
        if text[:1] in {"-", "#", "*"}:
            continue
        if lower.startswith(("source", "note", "notes")):
            continue
        if lower in {"total income", "ebitda", "pbt"}:
            continue
        if any(
            word in lower
            for word in (
                "business",
                "segment",
                "division",
                "category",
                "product",
                "region",
                "geography",
                "vertical",
                "portfolio",
                "consolidated",
                "total",
            )
        ):
            if text not in labels and len(text) <= 80:
                labels.append(text)
    return labels[:8]


def _nearest_heading_bottom(lines: list[dict], min_x: float, max_x: float, period_y: float) -> float:
    candidates = [
        line
        for line in lines
        if line["cy"] < period_y
        and min_x <= line["cx"] <= max_x
        and not _looks_like_number(line["text"])
        and not _period_tokens(line["text"])
    ]
    if not candidates:
        return 0.0
    return max(candidates, key=lambda line: line["y0"])["y1"]


def _nearest_metric_heading(lines: list[dict], min_x: float, max_x: float, period_y: float) -> str:
    candidates = [
        line
        for line in lines
        if line["cy"] < period_y
        and min_x <= line["cx"] <= max_x
        and not _looks_like_number(line["text"])
        and not _period_tokens(line["text"])
        and "crore" not in line["text"].lower()
        and "rs." not in line["text"].lower()
        and "inr" not in line["text"].lower()
        and not line["text"].startswith("#")
        and len(line["text"]) > 1
        and len(line["text"]) <= 60
    ]
    if not candidates:
        return ""
    return max(candidates, key=lambda line: line["y0"])["text"]


def _numeric_rows(values: list[dict], period_items: list[dict]) -> list[dict[str, str]]:
    by_period: dict[str, list[dict]] = {item["label"]: [] for item in period_items}
    for value in values:
        nearest = min(period_items, key=lambda item: abs(item["cx"] - value["cx"]))
        by_period[nearest["label"]].append(value)
    for label in by_period:
        by_period[label] = sorted(by_period[label], key=lambda item: item["cy"], reverse=True)

    row_count = min((len(items) for items in by_period.values()), default=0)
    output = []
    for row_index in range(row_count):
        mapped = {}
        for item in period_items:
            values_for_period = by_period[item["label"]]
            if row_index < len(values_for_period):
                mapped[item["label"]] = values_for_period[row_index]["text"]
        if len(mapped) >= 2:
            output.append(mapped)
    return output


def _page_unit(lines: list[dict]) -> str:
    page_text = " ".join(line["text"] for line in lines).lower()
    if "crore" in page_text:
        return "INR crore"
    if "million" in page_text:
        return "million"
    if "billion" in page_text:
        return "billion"
    if "percent" in page_text or "%" in page_text:
        return "percent where marked"
    return ""
