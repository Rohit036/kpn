from dataclasses import dataclass, field
from typing import List, Literal


Intent = Literal["annual", "news", "both"]
ToolStatus = Literal["ok", "empty", "error"]


@dataclass(frozen=True)
class ToolInput:
    query: str
    user_intent: Intent
    top_k: int = 4


@dataclass(frozen=True)
class EvidenceItem:
    tool_name: str
    source_type: str
    title: str
    url: str
    snippet: str
    score: float = 0.0


@dataclass(frozen=True)
class ToolOutput:
    tool_name: str
    status: ToolStatus
    evidence: List[EvidenceItem] = field(default_factory=list)
    error_message: str = ""
