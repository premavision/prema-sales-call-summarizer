import io
from datetime import datetime

import streamlit as st
from sqlmodel import Session, select

from app.core.config import get_settings
from app.core.constants import CallStatus
from app.db.session import engine
from app.models import Call, Transcript, CallAnalysis, CRMNote, CRMTask, CRMSyncLog
from app.services.call_service import CallService
from app.services.transcription_service import TranscriptionService
from app.services.analysis_service import AnalysisService
from app.services.crm_service import CRMService
from app.asr.stub_client import StubTranscriptionClient
from app.llm.stub_client import StubLLMClient
from app.crm.fake_client import FakeCRMClient
from app.storage.audio_storage import save_audio_file
from app.schemas import CallCreate


settings = get_settings()


def get_session() -> Session:
    return Session(engine)


def load_calls(session: Session) -> list[Call]:
    return session.exec(select(Call).order_by(Call.recorded_at.desc())).all()


def main() -> None:
    st.set_page_config(page_title="Sales Call Summarizer", layout="wide")
    st.title("Prema Vision | Sales Call Summarizer & CRM Sync")

    session = get_session()
    call_service = CallService(session)
    transcription_service = TranscriptionService(session, StubTranscriptionClient())
    analysis_service = AnalysisService(session, StubLLMClient())
    crm_service = CRMService(session, FakeCRMClient(session))

    with st.sidebar:
        st.header("Upload Call")
        title = st.text_input("Title", value="Demo call")
        recorded_at = st.text_input("Recorded at (ISO)", value=datetime.utcnow().isoformat())
        participants = st.text_input("Participants (comma separated)", value="Alex, Taylor")
        call_type = st.text_input("Call type", value="discovery")
        contact_name = st.text_input("Contact name", value="Alex Doe")
        company = st.text_input("Company", value="Acme Corp")
        crm_deal_id = st.text_input("CRM deal id", value="DEAL-123")
        audio_file = st.file_uploader("Audio file", type=["wav", "mp3", "m4a"])
        if st.button("Create call") and audio_file:
            filename = f"{datetime.utcnow().timestamp()}-{audio_file.name}"
            audio_path = save_audio_file(filename, io.BytesIO(audio_file.getvalue()))
            call_payload = CallCreate(
                title=title,
                recorded_at=datetime.fromisoformat(recorded_at),
                participants=[p.strip() for p in participants.split(",") if p.strip()],
                call_type=call_type,
                contact_name=contact_name,
                company=company,
                crm_deal_id=crm_deal_id,
            )
            new_call = call_service.create_call(call_data=call_payload, audio_path=audio_path)
            st.success(f"Created call {new_call.id}")

    st.subheader("Calls")
    calls = load_calls(session)
    for call in calls:
        with st.expander(f"{call.title} ({call.status})", expanded=False):
            st.write(f"Recorded at: {call.recorded_at}")
            st.write(f"Participants: {', '.join(call.participants)}")
            st.write(f"Company: {call.company or '-'}")
            cols = st.columns(4)
            if cols[0].button("Transcribe", key=f"t-{call.id}"):
                transcription_service.transcribe_call(call.id)
                st.success("Transcribed")
            if cols[1].button("Analyze", key=f"a-{call.id}"):
                analysis_service.analyze_call(call.id)
                st.success("Analyzed")
            if cols[2].button("Sync CRM", key=f"s-{call.id}"):
                crm_service.sync_call(call.id)
                st.success("CRM synced")

            transcript = session.exec(select(Transcript).where(Transcript.call_id == call.id)).first()
            analysis = session.exec(select(CallAnalysis).where(CallAnalysis.call_id == call.id)).first()
            notes = session.exec(select(CRMNote).where(CRMNote.call_id == call.id)).all()
            tasks = session.exec(select(CRMTask).where(CRMTask.call_id == call.id)).all()
            logs = session.exec(select(CRMSyncLog).where(CRMSyncLog.call_id == call.id)).all()

            if transcript:
                st.markdown("**Transcript**")
                st.text(transcript.text or "")
            if analysis:
                st.markdown("**Summary**")
                st.write(analysis.summary)
                st.markdown("**Action items**")
                for item in analysis.action_items:
                    st.write(f"- {item}")
                if analysis.follow_up_message:
                    st.markdown("**Follow-up draft**")
                    st.text(analysis.follow_up_message)
            if notes:
                st.markdown("**CRM Notes**")
                for note in notes:
                    st.write(note.content)
            if tasks:
                st.markdown("**CRM Tasks**")
                for task in tasks:
                    st.write(f"[ ] {task.description}")
            if logs:
                st.markdown("**CRM Sync Logs**")
                for log in logs:
                    st.write(f"{log.status} - {log.message}")


if __name__ == "__main__":
    main()
