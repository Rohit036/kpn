from __future__ import annotations

from kpn_agent.config import StorageConfig
from kpn_agent.orchestration.schemas import EvidenceItem, ToolInput, ToolOutput
from kpn_agent.storage.chroma_store import create_client, query_collection


class KpnNewsTool:
    name = "kpn_news_tool"

    def __init__(
        self,
        persist_dir: str | None = None,
        collection_name: str = "kpnnews",
    ) -> None:
        self.persist_dir = persist_dir or StorageConfig().chroma_persist_dir
        self.collection_name = collection_name

    def can_handle(self, payload: ToolInput) -> bool:
        return payload.user_intent in ("news", "both")

    def run(self, payload: ToolInput) -> ToolOutput:
        client = create_client(self.persist_dir)

        try:
            rows = query_collection(
                client=client,
                collection_name=self.collection_name,
                query=payload.query,
                top_k=payload.top_k,
            )
        except Exception as exc:
            return ToolOutput(tool_name=self.name, status="error", error_message=str(exc))

        evidence = [self._to_evidence(item) for item in rows]
        if not evidence:
            return ToolOutput(tool_name=self.name, status="empty")

        return ToolOutput(tool_name=self.name, status="ok", evidence=evidence)

    def _to_evidence(self, item: dict) -> EvidenceItem:
        md = item.get("metadata", {}) or {}
        snippet = " ".join(str(item.get("document", "")).split())
        if len(snippet) > 240:
            snippet = snippet[:240] + "..."

        return EvidenceItem(
            tool_name=self.name,
            source_type=str(md.get("source_type", "kpn_news")),
            title=str(md.get("source_title", md.get("source_url", ""))),
            url=str(md.get("source_url", "")),
            snippet=snippet,
            score=float(item.get("score") or 0.0),
        )
