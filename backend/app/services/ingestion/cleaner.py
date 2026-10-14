"""Text cleaning. Pages are (page_number | None, text) tuples."""
import re
from collections import Counter

Page = tuple[int | None, str]


def clean_text(text: str) -> str:
    text = text.replace("\x00", "").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)  # re-join words hyphenated across lines
    lines = []
    for line in text.split("\n"):
        line = re.sub(r"[ \t\u00a0]+", " ", line).strip()
        if re.fullmatch(r"(page\s*)?\d{1,4}(\s*(/|of)\s*\d{1,4})?", line, flags=re.I):
            continue  # bare page numbers
        lines.append(line)
    text = "\n".join(lines)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _remove_repeated_lines(pages: list[Page]) -> list[Page]:
    """Drop short lines that appear on more than half the pages (headers/footers)."""
    if len(pages) < 3:
        return pages
    counts: Counter[str] = Counter()
    for _, text in pages:
        counts.update({ln.strip() for ln in text.split("\n") if 0 < len(ln.strip()) < 80})
    repeated = {ln for ln, n in counts.items() if n > len(pages) / 2}
    return [(p, "\n".join(ln for ln in text.split("\n") if ln.strip() not in repeated)) for p, text in pages]


def clean_pages(pages: list[Page]) -> list[Page]:
    cleaned = [(p, clean_text(t)) for p, t in pages]
    cleaned = _remove_repeated_lines(cleaned)
    cleaned = [(p, clean_text(t)) for p, t in cleaned]
    return [(p, t) for p, t in cleaned if t]
