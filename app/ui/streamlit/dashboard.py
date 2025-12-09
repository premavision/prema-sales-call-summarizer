import io
import sys
import time
import uuid
import urllib.parse
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
from app.db.session import engine, reset_db
from app.models import Call, Transcript, CallAnalysis, CRMNote, CRMTask, CRMSyncLog
from app.services.call_service import CallService
from app.services.transcription_service import TranscriptionService
from app.services.analysis_service import AnalysisService
from app.services.crm_service import CRMService
from app.api.dependencies import _create_transcription_client, _create_llm_client, _create_crm_client
from app.storage.audio_storage import save_audio_file
from app.schemas import CallCreate


settings = get_settings()


def get_session() -> Session:
    return Session(engine)


def load_calls(session: Session, status_filter: Optional[CallStatus] = None, search_query: str = "", limit: int = 10, offset: int = 0, session_id: Optional[str] = None) -> tuple[List[Call], int]:
    query = select(Call)
    if session_id:
        query = query.where(Call.session_id == session_id)
    if status_filter:
        query = query.where(Call.status == status_filter)
    if search_query:
        search = f"%{search_query.lower()}%"
        query = query.where(
            (func.lower(Call.title).like(search)) |
            (func.lower(Call.contact_name).like(search)) |
            (func.lower(Call.company).like(search))
        )
    
    # Get total count for pagination
    count_query = select(func.count()).select_from(query.subquery())
    total_count = session.exec(count_query).one()
    
    # Get paginated results
    calls = session.exec(query.order_by(Call.recorded_at.desc()).offset(offset).limit(limit)).all()
    
    return calls, total_count


def get_status_color(status: CallStatus) -> str:
    colors = {
        CallStatus.NEW: "🔵",
        CallStatus.TRANSCRIBED: "🟡",
        CallStatus.ANALYZED: "🟠",
        CallStatus.SYNCED: "☑️",
        CallStatus.COMPLETED: "🟢",
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
    completed_calls = session.exec(select(func.count(Call.id)).where(Call.status == CallStatus.COMPLETED)).one()
    
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
        "completed": completed_calls,
        "recent": recent_calls,
    }


def main() -> None:
    st.set_page_config(
        page_title="Sales Call Summarizer",
        page_icon="📞",
        layout="wide",
        initial_sidebar_state="auto"
    )

    # Initialize Session ID for isolation
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    
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
        height: auto;
        min-height: 44px; /* Better touch target for mobile */
    }
    
    /* Mobile optimizations */
    @media (max-width: 768px) {
        .main-header {
            font-size: 1.8rem;
        }
        .call-card {
            padding: 1rem;
        }
        .block-container {
            padding-top: 2rem;
            padding-left: 1rem;
            padding-right: 1rem;
        }
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<h1 class="main-header">📞 Prema Vision | Sales Call Summarizer</h1>', unsafe_allow_html=True)
    st.markdown("---")

    session = get_session()
    call_service = CallService(session)
    # Use proper dependency injection to get the configured clients
    transcription_client = _create_transcription_client(settings)
    llm_client = _create_llm_client(settings)
    crm_client = _create_crm_client(session)
    transcription_service = TranscriptionService(session, transcription_client)
    analysis_service = AnalysisService(session, llm_client)
    crm_service = CRMService(session, crm_client)

    # Sidebar for upload and filters
    with st.sidebar:
        if settings.demo_mode:
            st.header("🎮 Demo Mode")
            st.caption(f"Session: {st.session_state.session_id[:8]}...")
            
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Load Demo 1", use_container_width=True):
                    p = Path(settings.audio_dir) / "demo_call_1.mp3"
                    if p.exists():
                        call_payload = CallCreate(
                            title="Discovery Call (Demo 1)",
                            recorded_at=datetime.utcnow(),
                            participants=["Alice", "Bob"],
                            call_type="discovery",
                            contact_name="Alice Smith",
                            company="Nexus Tech",
                            crm_deal_id="DEMO-001"
                        )
                        call_service.create_call(
                            call_data=call_payload, 
                            audio_path=str(p),
                            session_id=st.session_state.session_id
                        )
                        st.rerun()
                    else:
                        st.error("Demo file 1 not found")
            
            with c2:
                if st.button("Load Demo 2", use_container_width=True):
                    p = Path(settings.audio_dir) / "demo_call_2.mp3"
                    if p.exists():
                        call_payload = CallCreate(
                            title="Product Demo (Demo 2)",
                            recorded_at=datetime.utcnow(),
                            participants=["Charlie", "Dave"],
                            call_type="demo",
                            contact_name="Charlie Brown",
                            company="Solstice",
                            crm_deal_id="DEMO-002"
                        )
                        call_service.create_call(
                            call_data=call_payload, 
                            audio_path=str(p),
                            session_id=st.session_state.session_id
                        )
                        st.rerun()
                    else:
                        st.error("Demo file 2 not found")

            if st.button("🔄 Reset / New Demo", type="primary", use_container_width=True):
                st.session_state.session_id = str(uuid.uuid4())
                # Clear all other session state
                for key in list(st.session_state.keys()):
                    if key != "session_id":
                        del st.session_state[key]
                st.rerun()
            
            st.markdown("---")

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
                    new_call = call_service.create_call(
                        call_data=call_payload, 
                        audio_path=audio_path,
                        session_id=st.session_state.session_id if settings.demo_mode else None
                    )
                    st.success(f"Call created successfully! ID: {new_call.id}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error creating call: {str(e)}")
            elif submitted:
                st.warning("Please fill in required fields (Title and Audio File)")
        
        st.markdown("---")
        st.header("🔍 Filters")
        status_filter = st.selectbox(
            "Filter by Status",
            ["All"] + [status.value for status in CallStatus],
            key="status_filter"
        )
        search_query = st.text_input("🔎 Search", placeholder="Search by title, contact, or company...")

        st.markdown("---")
        # Settings Popover
        with st.sidebar.popover("⚙️ Settings", use_container_width=True):
            st.markdown("### Database")
            if st.button("🧨 Reset Database", type="primary", use_container_width=True):
                reset_db()
                st.success("Database reset successfully!")
                st.rerun()
    
    # Metrics Dashboard
    metrics = calculate_metrics(session)
    
    # Custom CSS for metrics grid
    st.markdown("""
    <style>
    .metric-container {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 1rem;
        margin-bottom: 2rem;
    }
    .metric-item {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    .metric-label {
        color: #555;
        font-size: 0.875rem;
        margin-bottom: 0.25rem;
        font-weight: 500;
    }
    .metric-value {
        color: #0f172a;
        font-size: 1.75rem;
        font-weight: 700;
    }
    
    /* Mobile styles */
    @media (max-width: 768px) {
        .metric-container {
            grid-template-columns: repeat(2, 1fr);
            gap: 0.75rem;
        }
        .metric-item {
            padding: 0.75rem;
        }
        .metric-value {
            font-size: 1.5rem;
        }
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="metric-container">
        <div class="metric-item">
            <div class="metric-label">Total Calls</div>
            <div class="metric-value">{metrics["total"]}</div>
        </div>
        <div class="metric-item">
            <div class="metric-label">New</div>
            <div class="metric-value">{metrics["new"]}</div>
        </div>
        <div class="metric-item">
            <div class="metric-label">Completed</div>
            <div class="metric-value">{metrics["completed"]}</div>
        </div>
        <div class="metric-item">
            <div class="metric-label">Last 7 Days</div>
            <div class="metric-value">{metrics["recent"]}</div>
        </div>
        <div class="metric-item">
            <div class="metric-label">Transcribed</div>
            <div class="metric-value">{metrics["transcribed"]}</div>
        </div>
        <div class="metric-item">
            <div class="metric-label">Analyzed</div>
            <div class="metric-value">{metrics["analyzed"]}</div>
        </div>
        <div class="metric-item">
            <div class="metric-label">Synced</div>
            <div class="metric-value">{metrics["synced"]}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Pagination State
    if "page_number" not in st.session_state:
        st.session_state.page_number = 1
    
    PAGE_SIZE = 10
    offset = (st.session_state.page_number - 1) * PAGE_SIZE
    
    # Filter calls
    selected_status = None if status_filter == "All" else CallStatus(status_filter)
    calls, total_count = load_calls(
        session, 
        status_filter=selected_status, 
        search_query=search_query or "", 
        limit=PAGE_SIZE, 
        offset=offset,
        session_id=st.session_state.session_id if settings.demo_mode else None
    )
    
    # Reset to page 1 if search/filter changes result in no items on current page (basic check)
    if total_count > 0 and offset >= total_count:
        st.session_state.page_number = 1
        st.rerun()

    # Header with refresh button
    header_col1, header_col2 = st.columns([3, 1])
    with header_col1:
        st.subheader(f"📋 Calls ({total_count})")
    with header_col2:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()

    # Initialize error state
    if "call_errors" not in st.session_state:
        st.session_state["call_errors"] = {}

    if not calls:
        if total_count == 0:
            st.info("📭 No calls found. Upload a new call to get started!")
        else:
            st.info("No calls match the current filters.")
    else:
        # Display calls in a better format
        for call in calls:
            with st.container():
                # Call header card
                # Use fewer columns for the header on mobile/general layout
                
                # Check for persistent errors
                if call.id in st.session_state["call_errors"]:
                    st.error(st.session_state["call_errors"][call.id], icon="🚨")

                if call.status == CallStatus.SYNCED:
                     st.warning("⚠️ CRM Synced, but follow-up email has not been sent yet.")

                selected_key = f"selected_action_items_{call.id}"
                if selected_key not in st.session_state:
                    st.session_state[selected_key] = []
                selected_action_items = st.session_state[selected_key]
                
                # Header row: Title and Status
                h_col1, h_col2 = st.columns([3, 1])
                with h_col1:
                    status_emoji = get_status_color(call.status)
                    st.markdown(f"### {status_emoji} {call.title}")
                    st.caption(f"Recorded: {format_datetime(call.recorded_at)} • {call.call_type or 'N/A'}")
                with h_col2:
                    # Compact status
                    status_colors = {
                        CallStatus.NEW: ("#3b82f6", "#dbeafe"),
                        CallStatus.TRANSCRIBED: ("#eab308", "#fef9c3"),
                        CallStatus.ANALYZED: ("#f97316", "#ffedd5"),
                        CallStatus.SYNCED: ("#0ea5e9", "#e0f2fe"),
                        CallStatus.COMPLETED: ("#16a34a", "#dcfce7"),
                    }
                    color, bg_color = status_colors.get(call.status, ("#6b7280", "#f3f4f6"))
                    st.markdown(
                        f'<div style="text-align: right;"><span style="background-color: {bg_color}; color: {color}; padding: 0.25rem 0.75rem; border-radius: 1rem; font-size: 0.8rem; font-weight: 600;">{call.status.value}</span></div>',
                        unsafe_allow_html=True
                    )
                
                # Details Row
                d_col1, d_col2, d_col3 = st.columns(3)
                with d_col1:
                    if call.contact_name: st.caption(f"👤 {call.contact_name}")
                with d_col2:
                    if call.company: st.caption(f"🏢 {call.company}")
                with d_col3:
                     if call.crm_deal_id: st.caption(f"🔗 {call.crm_deal_id}")

                # Action buttons - Simplified for mobile
                is_completed = call.status == CallStatus.COMPLETED
                
                # Group actions
                act_col1, act_col2, act_col3 = st.columns(3)
                
                with act_col1:
                    transcribe_container = st.empty()
                    if transcribe_container.button("🎙️ Transcribe", key=f"t-{call.id}", use_container_width=True, disabled=is_completed):
                        transcribe_container.button("🎙️ ...", key=f"t-loading-{call.id}", disabled=True, use_container_width=True)
                        try:
                            transcription_service.transcribe_call(call.id)
                            st.toast("Transcribed successfully!", icon="✅")
                            st.session_state["call_errors"].pop(call.id, None)
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            transcribe_container.button("🎙️ Transcribe", key=f"t-retry-{call.id}", use_container_width=True)
                            st.session_state["call_errors"][call.id] = f"Transcription failed: {str(e)}"
                            st.rerun()
                
                with act_col2:
                    analyze_container = st.empty()
                    if analyze_container.button("🧠 Analyze", key=f"a-{call.id}", use_container_width=True, disabled=is_completed):
                        analyze_container.button("🧠 ...", key=f"a-loading-{call.id}", disabled=True, use_container_width=True)
                        try:
                            analysis_service.analyze_call(call.id)
                            st.toast("Analyzed successfully!", icon="✅")
                            st.session_state["call_errors"].pop(call.id, None)
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            analyze_container.button("🧠 Analyze", key=f"a-retry-{call.id}", use_container_width=True)
                            st.session_state["call_errors"][call.id] = f"Analysis failed: {str(e)}"
                            st.rerun()
                
                with act_col3:
                    sync_container = st.empty()
                    if sync_container.button("🔄 Sync CRM", key=f"s-{call.id}", use_container_width=True, disabled=is_completed):
                        sync_container.button("🔄 ...", key=f"s-loading-{call.id}", disabled=True, use_container_width=True)
                        # Check follow-up status for warning
                        
                        try:
                            crm_service.sync_call(call.id, selected_action_items=selected_action_items)
                            st.session_state["call_errors"].pop(call.id, None)
                            st.toast("Synced with CRM!", icon="✅")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            sync_container.button("🔄 Sync CRM", key=f"s-retry-{call.id}", use_container_width=True)
                            st.session_state["call_errors"][call.id] = f"CRM Sync failed: {str(e)}"
                            st.rerun()
                
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
                                    st.caption("Check items to add them to your CRM Tasks list. They will be added after clicking 'Sync CRM'.")
                                    for i, item in enumerate(list(analysis.action_items)):
                                        is_checked = st.checkbox(
                                            item,
                                            value=item in selected_action_items,
                                            key=f"action-{call.id}-{i}",
                                        )
                                        if is_checked and item not in selected_action_items:
                                            selected_action_items.append(item)
                                            st.session_state[selected_key] = selected_action_items
                                        if not is_checked and item in selected_action_items:
                                            selected_action_items = [ai for ai in selected_action_items if ai != item]
                                            st.session_state[selected_key] = selected_action_items
                                else:
                                    st.info("No pending action items")
                                
                                if analysis.follow_up_message:
                                    st.markdown("### 💬 Follow-up Draft")
                                    updated_message = st.text_area(
                                        "Follow-up Message", 
                                        analysis.follow_up_message, 
                                        height=200, 
                                        key=f"followup-{call.id}",
                                        label_visibility="hidden"
                                    )
                                    
                                    # Save Draft Button
                                    col_save, col_empty = st.columns([1, 4])
                                    with col_save:
                                        # Check if current text differs from DB
                                        current_db_val = analysis.follow_up_message or ""
                                        current_ui_val = updated_message or ""
                                        is_dirty = current_ui_val.strip() != current_db_val.strip()
                                        
                                        if is_dirty:
                                            # Show primary Save button if changes detected
                                            if st.button("💾 Save", key=f"save-btn-{call.id}", type="primary"):
                                                analysis.follow_up_message = updated_message
                                                session.add(analysis)
                                                session.commit()
                                                st.rerun()
                                        else:
                                            # Show disabled/secondary Saved button if synced
                                            st.button("✅ Saved", key=f"save-btn-{call.id}", disabled=True)
                                    
                                    # Follow-up Actions
                                    st.markdown("---")
                                    st.markdown("#### Actions")
                                    
                                    # Prepare mailto link
                                    subject = urllib.parse.quote(f"Follow-up: {call.title}")
                                    body = urllib.parse.quote(analysis.follow_up_message or "")
                                    mailto_link = f"mailto:?subject={subject}&body={body}"
                                    
                                    col_email, col_sent, col_spacer = st.columns([2, 2, 3])
                                    
                                    with col_email:
                                        st.link_button("📧 Open Email", mailto_link)
                                        
                                    with col_sent:
                                        if analysis.follow_up_sent:
                                            st.success(f"Sent {format_datetime(analysis.follow_up_sent_at)}")
                                        else:
                                            if st.button("Mark Sent", key=f"mark-sent-{call.id}"):
                                                analysis.follow_up_sent = True
                                                analysis.follow_up_sent_at = datetime.utcnow()
                                                
                                                if call.status == CallStatus.SYNCED:
                                                    call.status = CallStatus.COMPLETED
                                                elif call.status != CallStatus.ANALYZED and call.status != CallStatus.COMPLETED:
                                                    call.status = CallStatus.ANALYZED
                                                
                                                session.add(analysis)
                                                session.add(call)
                                                session.commit()
                                                
                                                try:
                                                    crm_service.log_follow_up_sent(call.id)
                                                    st.toast("Logged to CRM!")
                                                except Exception as e:
                                                    st.error(f"Failed to log to CRM: {e}")
                                                    
                                                st.rerun()
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
                                due_date_str = f" (Due: {task.due_date})" if task.due_date else ""
                                synced_str = f" *[Synced: {format_datetime(task.created_at)}]*"
                                new_completed = st.checkbox(
                                    f"{task.description}{due_date_str}{synced_str}",
                                    value=task.completed,
                                    key=f"task-{task.id}"
                                )
                                if new_completed != task.completed:
                                    task.completed = new_completed
                                    session.add(task)
                                    session.commit()
                                    st.rerun()
                        else:
                            st.info("No CRM tasks available.")
                    
                    with tab5:
                        if logs:
                            for log in logs:
                                status_icon = "🟢" if log.status == CRMSyncStatus.SUCCESS else "🔴"
                                time_str = format_datetime(log.created_at)
                                label = f"{status_icon} {log.status.value} ({time_str})"
                                
                                with st.expander(label, expanded=(log.status != CRMSyncStatus.SUCCESS)):
                                    st.caption(f"Timestamp: {log.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
                                    
                                    if log.message:
                                        st.markdown("**Message:**")
                                        if log.status == CRMSyncStatus.SUCCESS:
                                            st.info(log.message)
                                        else:
                                            st.error(log.message)
                                    
                                    if log.payload:
                                        st.markdown("**Debug Payload:**")
                                        st.json(log.payload)
                        else:
                            st.info("No sync logs available.")
                
                st.markdown("---")
        
        # Pagination Controls
        if total_count > PAGE_SIZE:
            total_pages = (total_count + PAGE_SIZE - 1) // PAGE_SIZE
            c1, c2, c3 = st.columns([1, 2, 1])
            with c1:
                if st.session_state.page_number > 1:
                    if st.button("Previous", key="prev_page"):
                        st.session_state.page_number -= 1
                        st.rerun()
            with c2:
                st.markdown(f"<div style='text-align: center; padding-top: 10px;'>Page {st.session_state.page_number} of {total_pages}</div>", unsafe_allow_html=True)
            with c3:
                if st.session_state.page_number < total_pages:
                    if st.button("Next", key="next_page"):
                        st.session_state.page_number += 1
                        st.rerun()

if __name__ == "__main__":
    main()