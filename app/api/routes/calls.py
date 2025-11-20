import uuid
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, Query
from sqlmodel import Session, select

from app.api.dependencies import (
    get_db_session,
    get_llm_client,
    get_transcription_client,
    get_crm_client,
)
from app.asr.base import TranscriptionClient
from app.crm.base import CRMClient
from app.schemas import CallCreate, CallRead, CallDetail
from app.schemas import TranscriptRead, AnalysisRead, CRMNoteRead, CRMTaskRead, CRMSyncLogRead
from app.services.call_service import CallService
from app.services.transcription_service import TranscriptionService
from app.services.analysis_service import AnalysisService
from app.services.crm_service import CRMService
from app.services.pipeline_service import PipelineService
from app.storage.audio_storage import save_audio_file
from app.core.constants import CallStatus
from app.models import Call, Transcript, CallAnalysis, CRMNote, CRMTask, CRMSyncLog
from app.llm.base import LLMClient

router = APIRouter()


@router.post("/calls", response_model=CallRead)
async def create_call(
    title: str = Form(...),
    recorded_at: str = Form(...),
    participants: Optional[str] = Form(None, description="Comma-separated list"),
    call_type: Optional[str] = Form(None),
    contact_name: Optional[str] = Form(None),
    company: Optional[str] = Form(None),
    crm_deal_id: Optional[str] = Form(None),
    external_id: Optional[str] = Form(None),
    audio_file: UploadFile = File(...),
    session: Session = Depends(get_db_session),
) -> CallRead:
    try:
        recorded_dt = datetime.fromisoformat(recorded_at)
    except ValueError:
        raise HTTPException(status_code=400, detail="recorded_at must be ISO datetime string")

    participant_list: List[str] = []
    if participants:
        participant_list = [p.strip() for p in participants.split(",") if p.strip()]

    filename = f"{uuid.uuid4()}-{audio_file.filename}"
    audio_path = save_audio_file(filename, audio_file.file)

    call_data = CallCreate(
        title=title,
        recorded_at=recorded_dt,
        participants=participant_list,
        call_type=call_type,
        contact_name=contact_name,
        company=company,
        crm_deal_id=crm_deal_id,
        external_id=external_id,
    )
    call_service = CallService(session)
    call = call_service.create_call(call_data, audio_path=audio_path)
    return CallRead.from_orm(call)


@router.get("/calls", response_model=list[CallRead])
async def list_calls(
    status: Optional[CallStatus] = Query(default=None),
    session: Session = Depends(get_db_session),
) -> list[CallRead]:
    call_service = CallService(session)
    calls = call_service.list_calls(status=status)
    return [CallRead.from_orm(c) for c in calls]


@router.get("/calls/{call_id}", response_model=CallDetail)
async def get_call_detail(call_id: int, session: Session = Depends(get_db_session)) -> CallDetail:
    call = session.get(Call, call_id)
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    transcript = session.exec(select(Transcript).where(Transcript.call_id == call_id)).first()
    analysis = session.exec(select(CallAnalysis).where(CallAnalysis.call_id == call_id)).first()
    notes = session.exec(select(CRMNote).where(CRMNote.call_id == call_id)).all()
    tasks = session.exec(select(CRMTask).where(CRMTask.call_id == call_id)).all()
    logs = session.exec(select(CRMSyncLog).where(CRMSyncLog.call_id == call_id)).all()

    return CallDetail(
        call=CallRead.from_orm(call),
        transcript=TranscriptRead.from_orm(transcript) if transcript else None,
        analysis=AnalysisRead.from_orm(analysis) if analysis else None,
        crm_notes=[CRMNoteRead.from_orm(n) for n in notes],
        crm_tasks=[CRMTaskRead.from_orm(t) for t in tasks],
        crm_sync_logs=[CRMSyncLogRead.from_orm(l) for l in logs],
    )


@router.post("/calls/{call_id}/transcribe", response_model=TranscriptRead)
async def transcribe_call(
    call_id: int,
    session: Session = Depends(get_db_session),
    transcription_client: TranscriptionClient = Depends(get_transcription_client),
) -> TranscriptRead:
    service = TranscriptionService(session, transcription_client)
    try:
        transcript = service.transcribe_call(call_id)
        return TranscriptRead.from_orm(transcript)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/calls/{call_id}/analyze", response_model=AnalysisRead)
async def analyze_call(
    call_id: int,
    session: Session = Depends(get_db_session),
    llm_client: LLMClient = Depends(get_llm_client),
) -> AnalysisRead:
    service = AnalysisService(session, llm_client)
    try:
        analysis = service.analyze_call(call_id)
        return AnalysisRead.from_orm(analysis)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/calls/{call_id}/sync-crm", response_model=CRMSyncLogRead)
async def sync_crm(
    call_id: int,
    session: Session = Depends(get_db_session),
    crm_client: CRMClient = Depends(get_crm_client),
) -> CRMSyncLogRead:
    service = CRMService(session, crm_client)
    try:
        log = service.sync_call(call_id)
        return CRMSyncLogRead.from_orm(log)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/calls/{call_id}/process")
async def process_call(
    call_id: int,
    session: Session = Depends(get_db_session),
    transcription_client: TranscriptionClient = Depends(get_transcription_client),
    llm_client: LLMClient = Depends(get_llm_client),
    crm_client: CRMClient = Depends(get_crm_client),
) -> dict[str, str]:
    pipeline = PipelineService(session, transcription_client, llm_client, crm_client)
    try:
        pipeline.process_call(call_id)
        return {"status": "completed"}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
