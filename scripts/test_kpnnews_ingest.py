import argparse
import os
import sys

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(ROOT_DIR)
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from kpn_agent.config import ChunkConfig, StorageConfig
from kpn_agent.ingestion.kpn_news_ingestor import ingest_kpn_news


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest latest KPN news into kpnnews index using BeautifulSoup crawl")
    parser.add_argument("--seed-url", default="https://www.overons.kpn/nieuws/en")
    parser.add_argument("--allowed-domain", default="overons.kpn")
    parser.add_argument("--persist-dir", default=StorageConfig().chroma_persist_dir)
    parser.add_argument("--collection", default=StorageConfig().news_collection)
    parser.add_argument("--max-pages", type=int, default=30)
    parser.add_argument("--max-depth", type=int, default=2)
    parser.add_argument("--request-delay", type=float, default=1.0)
    parser.add_argument("--min-text-length", type=int, default=200)
    parser.add_argument("--chunk-size", type=int, default=ChunkConfig().chunk_size)
    parser.add_argument("--chunk-overlap", type=int, default=ChunkConfig().chunk_overlap)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    result = ingest_kpn_news(
        seed_url=args.seed_url,
        allowed_domain=args.allowed_domain,
        persist_dir=args.persist_dir,
        collection_name=args.collection,
        max_pages=args.max_pages,
        max_depth=args.max_depth,
        request_delay_sec=args.request_delay,
        min_text_length=args.min_text_length,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
    )

    print("=" * 80)
    print(f"Crawled pages: {result['crawled_pages']}")
    print(f"New or updated pages: {result['new_or_updated_pages']}")
    print(f"Unchanged pages: {result['unchanged_pages']}")
    print(f"Chunks written: {result['chunks_written']}")
    print(f"Collection count: {result['collection_count']}")
    print(f"Raw docs file: {result['docs_file']}")
    print(f"Processed chunks file: {result['chunks_file']}")
    print("=" * 80)


if __name__ == "__main__":
    main()
