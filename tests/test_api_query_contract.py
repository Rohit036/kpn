from fastapi.testclient import TestClient

from app.main import app
from kpn_agent.orchestration.schemas import EvidenceItem


client = TestClient(app)


def test_query_contract_with_mocked_orchestration(monkeypatch) -> None:
    def _mock_orchestration(**kwargs):
        return {
            "run_id": "run_test_001",
            "question": kwargs["query"],
            "selected_tools": ["kpn_news_tool"],
            "answer": "Mocked grounded answer.",
            "citations": [
                EvidenceItem(
                    tool_name="kpn_news_tool",
                    source_type="news",
                    title="KPN News Title",
                    url="https://example.com/kpn-news",
                    snippet="A relevant snippet.",
                    score=0.91,
                )
            ],
            "run_log_path": "data/logs/run_test_001.json",
        }

    monkeypatch.setattr("app.main.run_llm_orchestration", _mock_orchestration)

    payload = {
        "query": "What did KPN report?",
        "top_k": 3,
        "max_tool_rounds": 2,
        "disable_log": True,
    }
    response = client.post("/query", json=payload)

    assert response.status_code == 200
    body = response.json()

    assert set(body.keys()) == {
        "run_id",
        "question",
        "selected_tools",
        "answer",
        "citations",
        "run_log_path",
    }
    assert body["run_id"] == "run_test_001"
    assert body["question"] == payload["query"]
    assert body["selected_tools"] == ["kpn_news_tool"]
    assert body["answer"] == "Mocked grounded answer."
    assert isinstance(body["citations"], list)
    assert len(body["citations"]) == 1
    assert body["citations"][0]["url"] == "https://example.com/kpn-news"
