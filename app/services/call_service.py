import logging
from datetime import datetime
from typing import List, Optional

from sqlmodel import Session, select

from app.core.constants import CallStatus
from app.models import Call
from app.schemas import CallCreate

logger = logging.getLogger(__name__)


class CallService:
    def __init__(self, session: Session):
        self.session = session

    def create_call(self, call_data: CallCreate, audio_path: str, session_id: Optional[str] = None) -> Call:
        call = Call(
            **call_data.dict(),
            audio_path=audio_path,
            session_id=session_id,
            status=CallStatus.NEW,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.session.add(call)
        self.session.commit()
        self.session.refresh(call)
        logger.info("Created call %s with audio %s", call.id, audio_path)
        return call

    def list_calls(self, status: Optional[CallStatus] = None, session_id: Optional[str] = None) -> List[Call]:
        query = select(Call)
        if session_id:
            query = query.where(Call.session_id == session_id)
        if status:
            query = query.where(Call.status == status)
        return self.session.exec(query.order_by(Call.recorded_at.desc())).all()

    def get_call(self, call_id: int) -> Optional[Call]:
        return self.session.get(Call, call_id)

    def update_status(self, call: Call, status: CallStatus) -> Call:
        call.status = status
        call.updated_at = datetime.utcnow()
        self.session.add(call)
        self.session.commit()
        self.session.refresh(call)
        logger.info("Updated call %s status to %s", call.id, status)
        return call
