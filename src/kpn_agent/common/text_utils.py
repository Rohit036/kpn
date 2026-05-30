import re
from typing import List


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def preview_text(text: str, max_len: int = 240) -> str:
    clean = normalize_whitespace(text or "")
    if len(clean) <= max_len:
        return clean
    return clean[:max_len] + "..."


def chunk_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    clean = normalize_whitespace(text)
    if not clean:
        return []
    if len(clean) <= chunk_size:
        return [clean]

    chunks = []
    start = 0
    while start < len(clean):
        end = min(len(clean), start + chunk_size)
        chunks.append(clean[start:end])
        if end == len(clean):
            break
        start = max(0, end - overlap)
    return chunks
