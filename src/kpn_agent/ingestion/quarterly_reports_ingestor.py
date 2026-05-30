from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Set

from kpn_agent.common.hash_utils import sha1_hex
from kpn_agent.common.jsonl_utils import write_jsonl
from kpn_agent.config import ChunkConfig, StorageConfig
from kpn_agent.storage.chroma_store import create_client, upsert_chunks
from kpn_agent.tools.shared_indexing import build_chunks_from_documents, utc_now_iso


def ingest_quarterly_reports(
    pdf_dir: str = "data/quarterly_reports",
    persist_dir: str | None = None,
    collection_name: str | None = None,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> Dict[str, int]:
    pdf_path = Path(pdf_dir)
    storage = StorageConfig()
    chunk_config = ChunkConfig()

    persist_dir = persist_dir or storage.chroma_persist_dir
    collection_name = collection_name or storage.annual_collection
    chunk_size = chunk_size or chunk_config.chunk_size
    chunk_overlap = chunk_overlap or chunk_config.chunk_overlap

    client = create_client(persist_dir)
    collection = client.get_or_create_collection(name=collection_name)
    existing_source_ids = _existing_source_ids(collection)

    pdf_files = sorted(pdf_path.glob("*.pdf")) if pdf_path.exists() else []
    documents: List[Dict[str, str]] = []
    new_files = 0

    for file_path in pdf_files:
        source_id = sha1_hex(str(file_path.resolve()))
        if source_id in existing_source_ids:
            continue

        text = _extract_pdf_text(file_path)
        if not text.strip():
            continue

        new_files += 1
        documents.append(
            {
                "source_type": "kpnquarterlyreports",
                "source_id": source_id,
                "source_title": file_path.stem,
                "source_url": str(file_path.as_posix()),
                "source_updated_utc": utc_now_iso(),
                "ingested_at_utc": utc_now_iso(),
                "text": text,
            }
        )

    write_jsonl(storage.quarterly_docs_output_file, documents)

    chunks = build_chunks_from_documents(
        documents=documents,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    write_jsonl(storage.quarterly_chunks_output_file, chunks)
    if chunks:
        upsert_chunks(client=client, collection_name=collection_name, chunks=chunks)

    return {
        "pdf_files_found": len(pdf_files),
        "new_files_ingested": new_files,
        "chunks_written": len(chunks),
        "collection_count": collection.count(),
        "docs_file": storage.quarterly_docs_output_file,
        "chunks_file": storage.quarterly_chunks_output_file,
    }


def _existing_source_ids(collection: Any) -> Set[str]:
    source_ids: Set[str] = set()
    count = collection.count()
    if count == 0:
        return source_ids

    rows = collection.get(include=["metadatas"])
    for metadata in rows.get("metadatas", []) or []:
        if not metadata:
            continue
        source_id = str(metadata.get("source_id", "")).strip()
        if source_id:
            source_ids.add(source_id)
    return source_ids


def _extract_pdf_text(pdf_path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("pypdf is not installed. Run: pip install pypdf") from exc

    reader = PdfReader(str(pdf_path))
    parts: List[str] = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return "\n".join(parts)
