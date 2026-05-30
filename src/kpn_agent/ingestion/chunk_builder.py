from typing import Any, Dict, List

from kpn_agent.common.hash_utils import sha1_hex
from kpn_agent.common.text_utils import chunk_text
from kpn_agent.config import ChunkConfig


def build_chunk_rows(docs: List[Dict[str, Any]], chunk_config: ChunkConfig) -> List[Dict[str, Any]]:
    chunk_rows: List[Dict[str, Any]] = []

    for doc in docs:
        parts = chunk_text(
            text=doc["text"],
            chunk_size=chunk_config.chunk_size,
            overlap=chunk_config.chunk_overlap,
        )
        for index, part in enumerate(parts):
            chunk_rows.append(
                {
                    "id": sha1_hex(f"{doc['url']}|{index}|{part[:80]}"),
                    "text": part,
                    "metadata": {
                        "doc_id": doc["doc_id"],
                        "url": doc["url"],
                        "title": doc["title"] or doc["url"],
                        "source_type": doc["source_type"],
                        "crawl_depth": int(doc["crawl_depth"]),
                        "crawl_timestamp_utc": doc["crawl_timestamp_utc"],
                        "crawl_timestamp_epoch": int(doc["crawl_timestamp_epoch"]),
                        "status_code": int(doc["status_code"]),
                        "text_char_len": int(doc["text_char_len"]),
                        "content_hash": doc["content_hash"],
                        "chunk_index": int(index),
                        "chunk_count": int(0),
                    },
                }
            )

    by_doc_id: Dict[str, int] = {}
    for row in chunk_rows:
        doc_id = row["metadata"]["doc_id"]
        by_doc_id[doc_id] = by_doc_id.get(doc_id, 0) + 1

    for row in chunk_rows:
        row["metadata"]["chunk_count"] = by_doc_id[row["metadata"]["doc_id"]]

    return chunk_rows
