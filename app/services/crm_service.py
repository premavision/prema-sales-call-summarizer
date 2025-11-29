import logging
from datetime import datetime
from typing import List

from sqlmodel import Session, select

from app.core.constants import CallStatus, CRMSyncStatus
from app.crm.base import CRMClient
from app.models import Call, CallAnalysis, CRMNote, CRMTask, CRMSyncLog

logger = logging.getLogger(__name__)


class CRMService:
    def __init__(self, session: Session, client: CRMClient):
        self.session = session
        self.client = client

    def sync_call(self, call_id: int) -> CRMSyncLog:
        call = self.session.get(Call, call_id)
        if not call:
            raise ValueError(f"Call {call_id} not found")

        analysis = self.session.exec(
            select(CallAnalysis).where(CallAnalysis.call_id == call_id)
        ).first()
        if not analysis:
            raise ValueError("Analysis required before CRM sync")

        try:
            note_content = analysis.summary or "No summary available"
            if analysis.follow_up_message:
                note_content += f"\n\nFollow-up draft:\n{analysis.follow_up_message}"
            note = self.client.create_note(call_id=call_id, content=note_content)
            tasks = self.client.create_tasks(call_id=call_id, action_items=analysis.action_items)

            log = CRMSyncLog(
                call_id=call_id,
                status=CRMSyncStatus.SUCCESS,
                message="Synced note and tasks",
                created_at=datetime.utcnow(),
                payload={"note_id": note.id, "task_ids": [t.id for t in tasks]},
            )
            call.status = CallStatus.SYNCED
            call.updated_at = datetime.utcnow()
            self.session.add(log)
            self.session.add(call)
            self.session.commit()
            self.session.refresh(log)
            logger.info("CRM sync succeeded for call %s", call_id)
            return log
        except Exception as exc:  # pragma: no cover - defensive
            log = CRMSyncLog(
                call_id=call_id,
                status=CRMSyncStatus.FAILURE,
                message=str(exc),
                created_at=datetime.utcnow(),
            )
            self.session.add(log)
            self.session.commit()
            self.session.refresh(log)
            logger.error("CRM sync failed for call %s: %s", call_id, exc)
            raise
