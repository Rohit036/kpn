import argparse
import os
import sys

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(ROOT_DIR)
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from kpn_agent.config import ChunkConfig, StorageConfig
from kpn_agent.ingestion.quarterly_reports_ingestor import ingest_quarterly_reports


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest local quarterly report PDFs into kpnquarterlyreports")
    parser.add_argument("--pdf-dir", default="data/quarterly_reports")
    parser.add_argument("--persist-dir", default=StorageConfig().chroma_persist_dir)
    parser.add_argument("--collection", default=StorageConfig().annual_collection)
    parser.add_argument("--chunk-size", type=int, default=ChunkConfig().chunk_size)
    parser.add_argument("--chunk-overlap", type=int, default=ChunkConfig().chunk_overlap)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = ingest_quarterly_reports(
        pdf_dir=args.pdf_dir,
        persist_dir=args.persist_dir,
        collection_name=args.collection,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
    )

    print("=" * 80)
    print(f"PDF files found: {result['pdf_files_found']}")
    print(f"New files ingested: {result['new_files_ingested']}")
    print(f"Chunks written: {result['chunks_written']}")
    print(f"Collection count: {result['collection_count']}")
    print(f"Raw docs file: {result['docs_file']}")
    print(f"Processed chunks file: {result['chunks_file']}")
    print("=" * 80)


if __name__ == "__main__":
    main()
