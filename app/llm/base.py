from dataclasses import dataclass
from typing import Protocol, runtime_checkable, Optional, List, Any

from app.models.call import Call


@dataclass
class CallContext:
    call: Call


@dataclass
class CallAnalysisResult:
    summary: str
    pain_points: Optional[str] = None
    objections: Optional[str] = None
    action_items: List[str] = None  # type: ignore[assignment]
    follow_up_message: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None

    def __post_init__(self) -> None:
        if self.action_items is None:
            self.action_items = []


@runtime_checkable
class LLMClient(Protocol):
    def analyze_call(self, transcript: str, context: CallContext) -> CallAnalysisResult:
        ...
