import logging
from typing import List

from sqlmodel import Session

from app.crm.base import CRMClient
from app.models.crm import CRMNote, CRMTask

logger = logging.getLogger(__name__)


class FakeCRMClient(CRMClient):
    def __init__(self, session: Session):
        self.session = session

    def create_note(self, call_id: int, content: str) -> CRMNote:
        note = CRMNote(call_id=call_id, content=content)
        self.session.add(note)
        self.session.commit()
        self.session.refresh(note)
        logger.info("Created fake CRM note for call %s", call_id)
        return note

    def create_tasks(self, call_id: int, action_items: List[str]) -> List[CRMTask]:
        tasks: List[CRMTask] = []
        for item in action_items:
            task = CRMTask(call_id=call_id, description=item)
            self.session.add(task)
            tasks.append(task)
        self.session.commit()
        for task in tasks:
            self.session.refresh(task)
        logger.info("Created %s fake CRM tasks for call %s", len(tasks), call_id)
        return tasks
