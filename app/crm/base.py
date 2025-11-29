from typing import Protocol, runtime_checkable, List

from app.models.crm import CRMNote, CRMTask


@runtime_checkable
class CRMClient(Protocol):
    def create_note(self, call_id: int, content: str) -> CRMNote:
        ...

    def create_tasks(self, call_id: int, action_items: List[str]) -> List[CRMTask]:
        ...
