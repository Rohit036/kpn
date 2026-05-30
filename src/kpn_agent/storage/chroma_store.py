from typing import Any, Dict, List


def create_client(persist_dir: str) -> Any:
    try:
        import chromadb
    except ImportError as exc:
        raise RuntimeError("chromadb is not installed. Run: pip install chromadb") from exc
    return chromadb.PersistentClient(path=persist_dir)


def list_collection_names(client: Any) -> List[str]:
    names: List[str] = []
    for item in client.list_collections():
        if isinstance(item, str):
            names.append(item)
        else:
            names.append(getattr(item, "name", ""))
    return [name for name in names if name]


def upsert_chunks(
    client: Any,
    collection_name: str,
    chunks: List[Dict[str, Any]],
    batch_size: int = 64,
) -> None:
    collection = client.get_or_create_collection(name=collection_name)
    for start in range(0, len(chunks), batch_size):
        batch = chunks[start : start + batch_size]
        collection.upsert(
            ids=[item["id"] for item in batch],
            documents=[item["text"] for item in batch],
            metadatas=[item["metadata"] for item in batch],
        )


def query_collection(client: Any, collection_name: str, query: str, top_k: int) -> List[Dict[str, Any]]:
    collection = client.get_collection(name=collection_name)
    result = collection.query(
        query_texts=[query],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    ids = result.get("ids", [[]])[0]
    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0]

    rows: List[Dict[str, Any]] = []
    for idx in range(len(ids)):
        distance = distances[idx] if idx < len(distances) else None
        score = None
        if isinstance(distance, (int, float)):
            score = 1.0 / (1.0 + max(0.0, float(distance)))

        rows.append(
            {
                "id": ids[idx],
                "document": documents[idx] if idx < len(documents) else "",
                "metadata": metadatas[idx] if idx < len(metadatas) and metadatas[idx] else {},
                "distance": distance,
                "score": score,
                "collection": collection_name,
            }
        )

    return rows
