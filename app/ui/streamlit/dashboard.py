import io
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import streamlit as st
from sqlmodel import Session, select, func

from app.core.config import get_settings
from app.core.constants import CallStatus, CRMSyncStatus
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


def load_calls(session: Session, status_filter: Optional[CallStatus] = None, search_query: str = "") -> List[Call]:
    query = select(Call)
    if status_filter:
        query = query.where(Call.status == status_filter)
    if search_query:
        search = f"%{search_query.lower()}%"
        query = query.where(
            (func.lower(Call.title).like(search)) |
            (func.lower(Call.contact_name).like(search)) |
            (func.lower(Call.company).like(search))
        )
    return session.exec(query.order_by(Call.recorded_at.desc())).all()


def get_status_color(status: CallStatus) -> str:
    colors = {
        CallStatus.NEW: "🔵",
        CallStatus.TRANSCRIBED: "🟡",
        CallStatus.ANALYZED: "🟠",
        CallStatus.SYNCED: "🟢",
    }
    return colors.get(status, "⚪")


def format_datetime(dt: datetime) -> str:
    """Format datetime in a user-friendly way"""
    now = datetime.utcnow()
    diff = now - dt
    
    if diff < timedelta(minutes=1):
        return "Just now"
    elif diff < timedelta(hours=1):
        minutes = int(diff.total_seconds() / 60)
        return f"{minutes}m ago"
    elif diff < timedelta(days=1):
        hours = int(diff.total_seconds() / 3600)
        return f"{hours}h ago"
    elif diff < timedelta(days=7):
        days = diff.days
        return f"{days}d ago"
    else:
        return dt.strftime("%b %d, %Y")


def calculate_metrics(session: Session) -> dict:
    """Calculate dashboard metrics"""
    total_calls = session.exec(select(func.count(Call.id))).one()
    new_calls = session.exec(select(func.count(Call.id)).where(Call.status == CallStatus.NEW)).one()
    transcribed_calls = session.exec(select(func.count(Call.id)).where(Call.status == CallStatus.TRANSCRIBED)).one()
    analyzed_calls = session.exec(select(func.count(Call.id)).where(Call.status == CallStatus.ANALYZED)).one()
    synced_calls = session.exec(select(func.count(Call.id)).where(Call.status == CallStatus.SYNCED)).one()
    
    # Recent calls (last 7 days)
    week_ago = datetime.utcnow() - timedelta(days=7)
    recent_calls = session.exec(
        select(func.count(Call.id)).where(Call.recorded_at >= week_ago)
    ).one()
    
    return {
        "total": total_calls,
        "new": new_calls,
        "transcribed": transcribed_calls,
        "analyzed": analyzed_calls,
        "synced": synced_calls,
        "recent": recent_calls,
    }


def main() -> None:
    st.set_page_config(
        page_title="Sales Call Summarizer",
        page_icon="📞",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS for better styling
    st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 1rem;
        font-size: 0.875rem;
        font-weight: 600;
    }
    .call-card {
        background-color: white;
        padding: 1.5rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
    .stButton>button {
        width: 100%;
        border-radius: 0.5rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<h1 class="main-header">📞 Prema Vision | Sales Call Summarizer</h1>', unsafe_allow_html=True)
    st.markdown("---")

    session = get_session()
    call_service = CallService(session)
    transcription_service = TranscriptionService(session, StubTranscriptionClient())
    analysis_service = AnalysisService(session, StubLLMClient())
    crm_service = CRMService(session, FakeCRMClient(session))

    # Sidebar for upload and filters
    with st.sidebar:
        st.header("📤 Upload New Call")
        with st.form("upload_call_form", clear_on_submit=True):
            title = st.text_input("Title *", placeholder="Discovery call with Acme Corp")
            recorded_at = st.date_input("Recorded Date", value=datetime.utcnow().date())
            recorded_time = st.time_input("Recorded Time", value=datetime.utcnow().time())
            participants = st.text_input("Participants", placeholder="Alex, Taylor", help="Comma-separated list")
            call_type = st.selectbox("Call Type", ["discovery", "demo", "follow-up", "negotiation", "other"])
            contact_name = st.text_input("Contact Name", placeholder="Alex Doe")
            company = st.text_input("Company", placeholder="Acme Corp")
            crm_deal_id = st.text_input("CRM Deal ID", placeholder="DEAL-123")
            audio_file = st.file_uploader("Audio File *", type=["wav", "mp3", "m4a", "mp4"])
            
            submitted = st.form_submit_button("🚀 Create Call", use_container_width=True)
            
            if submitted and audio_file and title:
                try:
                    recorded_dt = datetime.combine(recorded_at, recorded_time)
                    filename = f"{datetime.utcnow().timestamp()}-{audio_file.name}"
                    audio_path = save_audio_file(filename, io.BytesIO(audio_file.getvalue()))
                    call_payload = CallCreate(
                        title=title,
                        recorded_at=recorded_dt,
                        participants=[p.strip() for p in participants.split(",") if p.strip()] if participants else [],
                        call_type=call_type,
                        contact_name=contact_name or None,
                        company=company or None,
                        crm_deal_id=crm_deal_id or None,
                    )
                    new_call = call_service.create_call(call_data=call_payload, audio_path=audio_path)
                    st.success(f"✅ Call created successfully! ID: {new_call.id}")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error creating call: {str(e)}")
            elif submitted:
                st.warning("⚠️ Please fill in required fields (Title and Audio File)")
        
        st.markdown("---")
        st.header("🔍 Filters")
        status_filter = st.selectbox(
            "Filter by Status",
            ["All"] + [status.value for status in CallStatus],
            key="status_filter"
        )
        search_query = st.text_input("🔎 Search", placeholder="Search by title, contact, or company...")
    
    # Metrics Dashboard
    metrics = calculate_metrics(session)
    metric_cols = st.columns(6)
    with metric_cols[0]:
        st.metric("Total Calls", metrics["total"])
    with metric_cols[1]:
        st.metric("New", metrics["new"], delta=None)
    with metric_cols[2]:
        st.metric("Transcribed", metrics["transcribed"])
    with metric_cols[3]:
        st.metric("Analyzed", metrics["analyzed"])
    with metric_cols[4]:
        st.metric("Synced", metrics["synced"])
    with metric_cols[5]:
        st.metric("Last 7 Days", metrics["recent"])
    
    st.markdown("---")
    
    # Filter calls
    selected_status = None if status_filter == "All" else CallStatus(status_filter)
    calls = load_calls(session, status_filter=selected_status, search_query=search_query or "")
    
    # Header with refresh button
    header_col1, header_col2 = st.columns([3, 1])
    with header_col1:
        st.subheader(f"📋 Calls ({len(calls)})")
    with header_col2:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()
    
    if not calls:
        st.info("📭 No calls found. Upload a new call to get started!")
    else:
        # Display calls in a better format
        for call in calls:
            with st.container():
                # Call header card
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    status_emoji = get_status_color(call.status)
                    st.markdown(f"### {status_emoji} {call.title}")
                    st.caption(f"ID: {call.id} • Recorded: {format_datetime(call.recorded_at)}")
                    info_cols = st.columns(3)
                    with info_cols[0]:
                        if call.contact_name:
                            st.caption(f"👤 {call.contact_name}")
                    with info_cols[1]:
                        if call.company:
                            st.caption(f"🏢 {call.company}")
                    with info_cols[2]:
                        if call.participants:
                            st.caption(f"👥 {', '.join(call.participants[:2])}{'...' if len(call.participants) > 2 else ''}")
                
                with col2:
                    st.markdown(f"**Status**")
                    status_colors = {
                        CallStatus.NEW: ("#3b82f6", "#dbeafe"),
                        CallStatus.TRANSCRIBED: ("#eab308", "#fef9c3"),
                        CallStatus.ANALYZED: ("#f97316", "#ffedd5"),
                        CallStatus.SYNCED: ("#22c55e", "#dcfce7"),
                    }
                    color, bg_color = status_colors.get(call.status, ("#6b7280", "#f3f4f6"))
                    st.markdown(
                        f'<span style="background-color: {bg_color}; color: {color}; padding: 0.25rem 0.75rem; border-radius: 1rem; font-size: 0.875rem; font-weight: 600;">{call.status.value}</span>',
                        unsafe_allow_html=True
                    )
                
                with col3:
                    st.markdown(f"**Type**")
                    st.caption(f"📞 {call.call_type or 'N/A'}")
                    if call.crm_deal_id:
                        st.caption(f"🔗 {call.crm_deal_id}")
                
                # Action buttons
                action_cols = st.columns(5)
                
                with action_cols[0]:
                    if st.button("🎙️ Transcribe", key=f"t-{call.id}", use_container_width=True):
                        with st.spinner("Transcribing..."):
                            try:
                                transcription_service.transcribe_call(call.id)
                                st.success("✅ Transcribed!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {str(e)}")
                
                with action_cols[1]:
                    if st.button("🧠 Analyze", key=f"a-{call.id}", use_container_width=True):
                        with st.spinner("Analyzing..."):
                            try:
                                analysis_service.analyze_call(call.id)
                                st.success("✅ Analyzed!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {str(e)}")
                
                with action_cols[2]:
                    if st.button("🔄 Sync CRM", key=f"s-{call.id}", use_container_width=True):
                        with st.spinner("Syncing..."):
                            try:
                                crm_service.sync_call(call.id)
                                st.success("✅ Synced!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {str(e)}")
                
                with action_cols[3]:
                    if st.button("⚡ Process All", key=f"p-{call.id}", use_container_width=True):
                        with st.spinner("Processing..."):
                            try:
                                transcription_service.transcribe_call(call.id)
                                analysis_service.analyze_call(call.id)
                                crm_service.sync_call(call.id)
                                st.success("✅ All steps completed!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {str(e)}")
                
                with action_cols[4]:
                    if call.crm_deal_id:
                        st.markdown(f"**CRM Deal**")
                        st.caption(f"🔗 {call.crm_deal_id}")
                    else:
                        st.caption("No CRM deal linked")
                
                # Call details in tabs
                transcript = session.exec(select(Transcript).where(Transcript.call_id == call.id)).first()
                analysis = session.exec(select(CallAnalysis).where(CallAnalysis.call_id == call.id)).first()
                notes = session.exec(select(CRMNote).where(CRMNote.call_id == call.id).order_by(CRMNote.created_at.desc())).all()
                tasks = session.exec(select(CRMTask).where(CRMTask.call_id == call.id).order_by(CRMTask.created_at.desc())).all()
                logs = session.exec(select(CRMSyncLog).where(CRMSyncLog.call_id == call.id).order_by(CRMSyncLog.created_at.desc())).all()
                
                if transcript or analysis or notes or tasks:
                    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📝 Transcript", "📊 Analysis", "📌 CRM Notes", "✅ Tasks", "📋 Sync Logs"])
                    
                    with tab1:
                        if transcript and transcript.text:
                            st.markdown("### Full Transcript")
                            st.text_area("Transcript", transcript.text, height=300, key=f"transcript-{call.id}", disabled=True, label_visibility="hidden")
                        else:
                            st.info("No transcript available. Click 'Transcribe' to generate one.")
                    
                    with tab2:
                        if analysis:
                            col_a, col_b = st.columns(2)
                            
                            with col_a:
                                st.markdown("### 📄 Summary")
                                if analysis.summary:
                                    st.write(analysis.summary)
                                else:
                                    st.info("No summary available")
                                
                                if analysis.pain_points:
                                    st.markdown("### 💔 Pain Points")
                                    st.write(analysis.pain_points)
                                
                                if analysis.objections:
                                    st.markdown("### ⚠️ Objections")
                                    st.write(analysis.objections)
                            
                            with col_b:
                                st.markdown("### ✅ Action Items")
                                if analysis.action_items:
                                    for i, item in enumerate(analysis.action_items, 1):
                                        st.checkbox(f"{i}. {item}", value=False, key=f"action-{call.id}-{i}")
                                else:
                                    st.info("No action items")
                                
                                if analysis.follow_up_message:
                                    st.markdown("### 💬 Follow-up Draft")
                                    st.text_area("Follow-up Message", analysis.follow_up_message, height=200, key=f"followup-{call.id}", disabled=True, label_visibility="hidden")
                        else:
                            st.info("No analysis available. Click 'Analyze' to generate one.")
                    
                    with tab3:
                        if notes:
                            for note in notes:
                                with st.expander(f"Note from {format_datetime(note.created_at)}"):
                                    st.write(note.content)
                        else:
                            st.info("No CRM notes available.")
                    
                    with tab4:
                        if tasks:
                            for task in tasks:
                                status_icon = "✅" if task.completed else "⏳"
                                due_date_str = f" (Due: {task.due_date})" if task.due_date else ""
                                st.checkbox(
                                    f"{status_icon} {task.description}{due_date_str}",
                                    value=task.completed,
                                    key=f"task-{task.id}"
                                )
                        else:
                            st.info("No CRM tasks available.")
                    
                    with tab5:
                        if logs:
                            for log in logs:
                                status_color = "🟢" if log.status == CRMSyncStatus.SUCCESS else "🔴"
                                st.markdown(f"**{status_color} {log.status.value}** - {format_datetime(log.created_at)}")
                                if log.message:
                                    st.caption(log.message)
                                st.markdown("---")
                        else:
                            st.info("No sync logs available.")
                
                st.markdown("---")


if __name__ == "__main__":
    main()
