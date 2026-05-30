from typing import Protocol

from kpn_agent.orchestration.schemas import ToolInput, ToolOutput


class Tool(Protocol):
    name: str

    def run(self, payload: ToolInput) -> ToolOutput:
        """Execute the tool and return normalized output."""

    def can_handle(self, payload: ToolInput) -> bool:
        """Return whether this tool should be considered for current intent."""
