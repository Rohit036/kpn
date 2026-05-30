import argparse
import os
import sys
from typing import Any


ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(ROOT_DIR)
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from kpn_agent.config import StorageConfig
from kpn_agent.storage.chroma_store import create_client, list_collection_names


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect Chroma collections and stored embeddings")
    parser.add_argument("--persist-dir", default=StorageConfig().chroma_persist_dir)
    parser.add_argument("--collection", default="", help="Inspect only one collection name")
    parser.add_argument("--limit", type=int, default=2, help="Sample rows to read per collection")
    parser.add_argument("--preview-len", type=int, default=8, help="How many embedding values to preview")
    return parser.parse_args()


def _safe_preview(text: str, max_len: int = 140) -> str:
    clean = " ".join((text or "").split())
    if len(clean) <= max_len:
        return clean
    return clean[:max_len] + "..."


def _coerce_sequence(value: Any) -> list[Any]:
    if value is None:
        return []
    try:
        return list(value)
    except TypeError:
        return []


def _print_default_embedder_hint() -> None:
    try:
        from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

        ef: Any = DefaultEmbeddingFunction()
        model_name = getattr(ef, "model_name", None)
        print("DefaultEmbeddingFunction class:", ef.__class__.__name__)
        if model_name:
            print("DefaultEmbeddingFunction model hint:", model_name)
        else:
            print("DefaultEmbeddingFunction model hint: not exposed by this Chroma version")
    except Exception as exc:
        print("Default embedding introspection unavailable:", exc)


def inspect_collection(client: Any, collection_name: str, limit: int, preview_len: int) -> None:
    print("=" * 80)
    print(f"Collection: {collection_name}")

    collection = client.get_collection(name=collection_name)

    try:
        count = collection.count()
    except Exception as exc:
        print("Count error:", exc)
        return

    print("Count:", count)
    print("Metadata:", collection.metadata or {})

    if count == 0:
        print("No rows to inspect.")
        return

    rows = collection.get(include=["embeddings", "documents", "metadatas"], limit=max(1, limit))

    ids = _coerce_sequence(rows.get("ids"))
    embeds = _coerce_sequence(rows.get("embeddings"))
    docs = _coerce_sequence(rows.get("documents"))
    metas = _coerce_sequence(rows.get("metadatas"))

    dim = len(embeds[0]) if embeds else 0
    print("Embedding dimension:", dim)

    for idx, row_id in enumerate(ids):
        print(f"- Row {idx + 1}")
        print("  id:", row_id)
        vector = _coerce_sequence(embeds[idx]) if idx < len(embeds) else []
        if vector:
            print("  embedding preview:", vector[:preview_len])
        else:
            print("  embedding preview: n/a")

        md = metas[idx] if idx < len(metas) and metas[idx] else {}
        print(
            "  metadata source:",
            md.get("source_url") or md.get("url") or md.get("source_title") or "n/a",
        )

        doc = docs[idx] if idx < len(docs) else ""
        print("  document preview:", _safe_preview(str(doc)))


def main() -> None:
    args = parse_args()

    client = create_client(args.persist_dir)

    print("Persist dir:", args.persist_dir)
    _print_default_embedder_hint()

    if args.collection:
        targets = [args.collection]
    else:
        targets = list_collection_names(client)

    if not targets:
        print("No collections found.")
        return

    print("Collections:", ", ".join(targets))
    for name in targets:
        inspect_collection(client, name, args.limit, args.preview_len)


if __name__ == "__main__":
    main()
