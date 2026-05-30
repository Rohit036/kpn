from typing import Any, Dict

from kpn_agent.common.jsonl_utils import write_jsonl
from kpn_agent.config import ChunkConfig, CrawlConfig, StorageConfig
from kpn_agent.ingestion.chunk_builder import build_chunk_rows
from kpn_agent.ingestion.crawler import crawl_news
from kpn_agent.storage.chroma_store import create_client, upsert_chunks


def run_news_ingestion(
    crawl_config: CrawlConfig,
    chunk_config: ChunkConfig,
    storage_config: StorageConfig,
    collection_name: str,
    skip_chroma: bool,
) -> Dict[str, Any]:
    docs = crawl_news(crawl_config)
    chunks = build_chunk_rows(docs, chunk_config)

    write_jsonl(storage_config.docs_output_file, docs)
    write_jsonl(storage_config.chunks_output_file, chunks)

    if not skip_chroma:
        client = create_client(storage_config.chroma_persist_dir)
        upsert_chunks(client=client, collection_name=collection_name, chunks=chunks)

    return {
        "docs": len(docs),
        "chunks": len(chunks),
        "skipped_chroma": skip_chroma,
        "collection": collection_name,
        "persist_dir": storage_config.chroma_persist_dir,
        "docs_file": storage_config.docs_output_file,
        "chunks_file": storage_config.chunks_output_file,
    }
