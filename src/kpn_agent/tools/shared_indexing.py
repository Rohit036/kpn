from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List

from kpn_agent.common.hash_utils import sha1_hex
from kpn_agent.common.text_utils import chunk_text, normalize_whitespace


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_chunks_from_documents(
    documents: List[Dict[str, str]],
    chunk_size: int,
    chunk_overlap: int,
) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []

    for doc in documents:
        text = normalize_whitespace(doc.get("text", ""))
        if not text:
            continue

        source_id = doc["source_id"]
        source_title = doc["source_title"]
        source_url = doc["source_url"]
        source_type = doc["source_type"]
        source_updated_utc = doc.get("source_updated_utc", "")
        ingested_at_utc = doc.get("ingested_at_utc", utc_now_iso())

        chunks = chunk_text(text, chunk_size=chunk_size, overlap=chunk_overlap)
        content_hash = sha1_hex(text)

        for idx, part in enumerate(chunks):
            rows.append(
                {
                    "id": sha1_hex(f"{source_id}|{idx}|{part[:80]}"),
                    "text": part,
                    "metadata": {
                        "source_type": source_type,
                        "source_id": source_id,
                        "source_title": source_title,
                        "source_url": source_url,
                        "source_updated_utc": source_updated_utc,
                        "ingested_at_utc": ingested_at_utc,
                        "content_hash": content_hash,
                        "chunk_index": idx,
                        "chunk_count": len(chunks),
                    },
                }
            )

    return rows
