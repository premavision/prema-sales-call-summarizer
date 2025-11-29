import logging
from datetime import datetime
from typing import Optional

from sqlmodel import Session, select

from app.core.constants import CallStatus
from app.llm.base import CallContext, LLMClient
from app.models import Call, CallAnalysis, Transcript

logger = logging.getLogger(__name__)


class AnalysisService:
    def __init__(self, session: Session, client: LLMClient):
        self.session = session
        self.client = client

    def analyze_call(self, call_id: int) -> CallAnalysis:
        call = self.session.get(Call, call_id)
        if not call:
            raise ValueError(f"Call {call_id} not found")

        transcript = self.session.exec(
            select(Transcript).where(Transcript.call_id == call_id)
        ).first()
        if not transcript or not transcript.text:
            raise ValueError("Transcript not available for analysis")

        logger.info("Starting analysis for call %s", call_id)
        context = CallContext(call=call)
        result = self.client.analyze_call(transcript.text, context)

        existing = self.session.exec(
            select(CallAnalysis).where(CallAnalysis.call_id == call_id)
        ).first()
        if existing:
            self.session.delete(existing)
            self.session.commit()

        analysis = CallAnalysis(
            call_id=call_id,
            summary=result.summary,
            pain_points=result.pain_points,
            objections=result.objections,
            action_items=result.action_items,
            follow_up_message=result.follow_up_message,
            extra_metadata=result.metadata,
            created_at=datetime.utcnow(),
        )

        call.status = CallStatus.ANALYZED
        call.updated_at = datetime.utcnow()

        self.session.add(analysis)
        self.session.add(call)
        self.session.commit()
        self.session.refresh(analysis)
        logger.info("Completed analysis for call %s", call_id)
        return analysis
