import logging
from datetime import datetime
from typing import List, Optional

from sqlmodel import Session, select

from app.core.constants import CallStatus, CRMSyncStatus
from app.crm.base import CRMClient
from app.models import Call, CallAnalysis, CRMNote, CRMTask, CRMSyncLog

logger = logging.getLogger(__name__)


class CRMService:
    def __init__(self, session: Session, client: CRMClient):
        self.session = session
        self.client = client

    def log_follow_up_sent(self, call_id: int) -> CRMNote:
        """Create a CRM note indicating the follow-up email was sent manually."""
        content = f"Follow-up email manually sent to client on {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}."
        return self.client.create_note(call_id=call_id, content=content)

    def sync_call(self, call_id: int, selected_action_items: Optional[List[str]] = None) -> CRMSyncLog:
        call = self.session.get(Call, call_id)
        if not call:
            raise ValueError(f"Call {call_id} not found")

        analysis = self.session.exec(
            select(CallAnalysis).where(CallAnalysis.call_id == call_id)
        ).first()
        if not analysis:
            raise ValueError("Analysis required before CRM sync")

        try:
            parts = []
            if analysis.summary:
                parts.append(f"SUMMARY:\n{analysis.summary}")
            if analysis.pain_points:
                parts.append(f"PAIN POINTS:\n{analysis.pain_points}")
            if analysis.objections:
                parts.append(f"OBJECTIONS:\n{analysis.objections}")
            
            if getattr(analysis, "follow_up_sent", False):
                sent_at = getattr(analysis, "follow_up_sent_at", datetime.utcnow())
                date_str = sent_at.strftime("%Y/%m/%d")
                parts.append(f"FOLLOW-UP:\nEmail sent to client on {date_str}.")
            else:
                parts.append("FOLLOW-UP:\nNot sent yet.")
                
            note_content = "\n\n".join(parts) or "No content available"
            note = self.client.create_note(call_id=call_id, content=note_content)
            # Deduplicate against existing tasks for this call (case-insensitive, trimmed)
            existing_tasks = self.session.exec(
                select(CRMTask).where(CRMTask.call_id == call_id)
            ).all()
            
            # Normalize strings for comparison: lowercase, strip, remove extra spaces
            def normalize(s: str) -> str:
                return " ".join((s or "").split()).lower()

            existing_descriptions = {
                normalize(t.description) for t in existing_tasks
            }
            deduped_items: List[str] = []
            items_to_sync = selected_action_items if selected_action_items is not None else analysis.action_items
            for item in items_to_sync:
                normalized = normalize(item)
                if normalized and normalized not in existing_descriptions:
                    deduped_items.append(item)
                    existing_descriptions.add(normalized)
            tasks = self.client.create_tasks(call_id=call_id, action_items=deduped_items)

            log = CRMSyncLog(
                call_id=call_id,
                status=CRMSyncStatus.SUCCESS,
                message="Synced note and tasks",
                created_at=datetime.utcnow(),
                payload={"note_id": note.id, "task_ids": [t.id for t in tasks]},
            )
            call.status = CallStatus.COMPLETED if getattr(analysis, "follow_up_sent", False) else CallStatus.SYNCED
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
