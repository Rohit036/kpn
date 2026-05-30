import pytest

from kpn_agent.storage.chroma_store import create_client, query_collection, upsert_chunks


pytest.importorskip("chromadb")


def test_local_chroma_upsert_and_query(tmp_path) -> None:
    persist_dir = tmp_path / "chroma_test_store"
    client = create_client(str(persist_dir))

    chunks = [
        {
            "id": "doc-1",
            "text": "KPN quarterly report mentions strong broadband growth in the Netherlands.",
            "metadata": {
                "source_type": "quarterly_report",
                "source_title": "KPN Q1 2026",
                "source_url": "https://example.com/q1-2026",
            },
        },
        {
            "id": "doc-2",
            "text": "KPN announced a network modernization initiative for enterprise customers.",
            "metadata": {
                "source_type": "news",
                "source_title": "KPN Network Update",
                "source_url": "https://example.com/news-network",
            },
        },
    ]

    upsert_chunks(client, "test_collection", chunks)
    rows = query_collection(client, "test_collection", "broadband growth", top_k=2)

    assert len(rows) >= 1
    assert rows[0]["collection"] == "test_collection"
    assert "document" in rows[0]
    assert "metadata" in rows[0]
    assert "id" in rows[0]
