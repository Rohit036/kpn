from __future__ import annotations

from typing import Any, Dict, List

from kpn_agent.common.hash_utils import sha1_hex
from kpn_agent.common.jsonl_utils import write_jsonl
from kpn_agent.config import ChunkConfig, CrawlConfig, StorageConfig
from kpn_agent.ingestion.crawler import crawl_news
from kpn_agent.storage.chroma_store import create_client, upsert_chunks
from kpn_agent.tools.shared_indexing import build_chunks_from_documents, utc_now_iso


def ingest_kpn_news(
    seed_url: str | None = None,
    allowed_domain: str | None = None,
    persist_dir: str | None = None,
    collection_name: str | None = None,
    max_pages: int | None = None,
    max_depth: int | None = None,
    request_delay_sec: float | None = None,
    min_text_length: int | None = None,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> Dict[str, int]:
    storage = StorageConfig()
    chunk_config = ChunkConfig()
    crawl_defaults = CrawlConfig()

    persist_dir = persist_dir or storage.chroma_persist_dir
    collection_name = collection_name or storage.news_collection
    chunk_size = chunk_size or chunk_config.chunk_size
    chunk_overlap = chunk_overlap or chunk_config.chunk_overlap
    seed_url = seed_url or crawl_defaults.seed_url
    allowed_domain = allowed_domain or crawl_defaults.allowed_domain
    max_pages = max_pages or crawl_defaults.max_pages
    max_depth = max_depth or crawl_defaults.max_depth
    request_delay_sec = request_delay_sec if request_delay_sec is not None else crawl_defaults.request_delay_sec
    min_text_length = min_text_length or crawl_defaults.min_text_length

    client = create_client(persist_dir)
    collection = client.get_or_create_collection(name=collection_name)

    before_count = collection.count()
    existing_hashes_by_url = _existing_hashes_by_url(collection)

    crawled_docs = crawl_news(
        CrawlConfig(
            seed_url=seed_url,
            allowed_domain=allowed_domain,
            max_pages=max_pages,
            max_depth=max_depth,
            request_delay_sec=request_delay_sec,
            min_text_length=min_text_length,
            user_agent=crawl_defaults.user_agent,
        )
    )
    write_jsonl(storage.docs_output_file, crawled_docs)

    updated_docs = []
    updated_urls = []
    unchanged_urls = 0

    for item in crawled_docs:
        url = str(item.get("url", "")).strip()
        content_hash = str(item.get("content_hash", "")).strip()
        if not url or not content_hash:
            continue

        known_hashes = existing_hashes_by_url.get(url, set())
        if content_hash in known_hashes:
            unchanged_urls += 1
            continue

        updated_docs.append(item)
        updated_urls.append(url)

    if not updated_docs:
        write_jsonl(storage.chunks_output_file, [])
        return {
            "crawled_pages": len(crawled_docs),
            "new_or_updated_pages": 0,
            "unchanged_pages": unchanged_urls,
            "chunks_written": 0,
            "collection_count": before_count,
            "docs_file": storage.docs_output_file,
            "chunks_file": storage.chunks_output_file,
        }

    documents: List[Dict[str, str]] = []
    for item in updated_docs:
        text = str(item.get("text", "")).strip()
        if not text:
            continue
        documents.append(
            {
                "source_type": "kpn_news",
                "source_id": sha1_hex(str(item.get("url", ""))),
                "source_title": str(item.get("title", "")).strip() or str(item.get("url", "")).strip(),
                "source_url": str(item.get("url", "")).strip(),
                "source_updated_utc": str(item.get("crawl_timestamp_utc", "")).strip() or utc_now_iso(),
                "ingested_at_utc": utc_now_iso(),
                "text": text,
            }
        )

    for url in set(updated_urls):
        collection.delete(where={"source_url": url})

    chunks = build_chunks_from_documents(
        documents=documents,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    write_jsonl(storage.chunks_output_file, chunks)
    if chunks:
        upsert_chunks(client=client, collection_name=collection_name, chunks=chunks)

    return {
        "crawled_pages": len(crawled_docs),
        "new_or_updated_pages": len(set(updated_urls)),
        "unchanged_pages": unchanged_urls,
        "chunks_written": len(chunks),
        "collection_count": collection.count(),
        "docs_file": storage.docs_output_file,
        "chunks_file": storage.chunks_output_file,
    }


def _existing_hashes_by_url(collection: Any) -> Dict[str, set[str]]:
    rows_by_url: Dict[str, set[str]] = {}
    count = collection.count()
    if count == 0:
        return rows_by_url

    rows = collection.get(include=["metadatas"])
    for metadata in rows.get("metadatas", []) or []:
        if not metadata:
            continue
        url = str(metadata.get("source_url", "")).strip()
        content_hash = str(metadata.get("content_hash", "")).strip()
        if not url or not content_hash:
            continue
        rows_by_url.setdefault(url, set()).add(content_hash)
    return rows_by_url
