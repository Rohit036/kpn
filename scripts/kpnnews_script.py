import argparse
import os
import sys

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(ROOT_DIR)
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from kpn_agent.config import ChunkConfig, CrawlConfig, StorageConfig
from kpn_agent.pipelines.news_ingest_pipeline import run_news_ingestion


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Crawl KPN news pages and persist text chunks")
    parser.add_argument("--seed-url", default=CrawlConfig().seed_url)
    parser.add_argument("--skip-chroma", action="store_true")
    parser.add_argument("--collection", default=StorageConfig().news_collection)
    parser.add_argument("--persist-dir", default=StorageConfig().chroma_persist_dir)
    parser.add_argument("--max-pages", type=int, default=CrawlConfig().max_pages)
    parser.add_argument("--max-depth", type=int, default=CrawlConfig().max_depth)
    parser.add_argument("--request-delay", type=float, default=CrawlConfig().request_delay_sec)
    parser.add_argument("--chunk-size", type=int, default=ChunkConfig().chunk_size)
    parser.add_argument("--chunk-overlap", type=int, default=ChunkConfig().chunk_overlap)
    parser.add_argument("--raw-output", default=StorageConfig().docs_output_file)
    parser.add_argument("--chunks-output", default=StorageConfig().chunks_output_file)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    crawl_config = CrawlConfig(
        seed_url=args.seed_url,
        max_pages=args.max_pages,
        max_depth=args.max_depth,
        request_delay_sec=args.request_delay,
    )
    chunk_config = ChunkConfig(chunk_size=args.chunk_size, chunk_overlap=args.chunk_overlap)
    storage_config = StorageConfig(
        docs_output_file=args.raw_output,
        chunks_output_file=args.chunks_output,
        chroma_persist_dir=args.persist_dir,
    )

    result = run_news_ingestion(
        crawl_config=crawl_config,
        chunk_config=chunk_config,
        storage_config=storage_config,
        collection_name=args.collection,
        skip_chroma=args.skip_chroma,
    )

    if not result["skipped_chroma"]:
        print(
            f"Saved {result['docs']} docs and {result['chunks']} chunks. "
            f"Chroma collection='{result['collection']}' at '{result['persist_dir']}'."
        )
    else:
        print(
            f"Saved {result['docs']} docs to {result['docs_file']} and {result['chunks']} chunks to {result['chunks_file']}. "
            "Skipped Chroma write."
        )


if __name__ == "__main__":
    main()