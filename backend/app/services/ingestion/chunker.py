"""Paragraph-aware chunking with overlap."""
import re
from dataclasses import dataclass


@dataclass
class Chunk:
    page: int | None
    text: str


def _split_long(text: str, size: int) -> list[str]:
    """Split an oversized paragraph on sentence boundaries, hard-cutting as a last resort."""
    parts: list[str] = []
    buf = ""
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        while len(sentence) > size:
            if buf:
                parts.append(buf)
                buf = ""
            parts.append(sentence[:size])
            sentence = sentence[size:]
        if buf and len(buf) + 1 + len(sentence) > size:
            parts.append(buf)
            buf = sentence
        else:
            buf = f"{buf} {sentence}".strip()
    if buf:
        parts.append(buf)
    return parts


def _overlap_tail(text: str, overlap: int) -> str:
    if overlap <= 0 or len(text) <= overlap:
        return ""
    tail = text[-overlap:]
    return tail[tail.find(" ") + 1:] if " " in tail else tail


def chunk_pages(pages: list[tuple[int | None, str]], size: int = 800, overlap: int = 100) -> list[Chunk]:
    chunks: list[Chunk] = []
    for page, text in pages:
        pieces: list[str] = []
        for para in re.split(r"\n\s*\n", text):
            para = para.strip()
            if not para:
                continue
            pieces.extend([para] if len(para) <= size else _split_long(para, size))
        buf = ""
        for piece in pieces:
            if buf and len(buf) + 2 + len(piece) > size:
                chunks.append(Chunk(page, buf))
                tail = _overlap_tail(buf, overlap)
                buf = f"{tail} {piece}".strip() if tail else piece
            else:
                buf = f"{buf}\n\n{piece}" if buf else piece
        if buf.strip():
            chunks.append(Chunk(page, buf))
    return chunks
