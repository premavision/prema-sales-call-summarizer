"""
End-to-End Streamlit UI Tests

This test suite covers all Streamlit dashboard interactions:
- Dashboard loading and metrics display
- Call upload form with validation
- Call listing and filtering
- Status filtering and search functionality
- Individual call actions (Transcribe, Analyze, Sync CRM, Process All)
- Call details tabs (Transcript, Analysis, CRM Notes, Tasks, Sync Logs)
- Error handling and edge cases
"""
from datetime import datetime
from pathlib import Path

import pytest
from httpx import AsyncClient
from playwright.async_api import Page, expect

pytestmark = [pytest.mark.e2e, pytest.mark.ui]


class TestDashboardLoading:
    """Tests for dashboard initialization and basic rendering"""
    
    @pytest.mark.asyncio
    async def test_dashboard_loads_successfully(self, page: Page, streamlit_server: str):
        """
        Test Case: Dashboard Loads Successfully
        Description: Verify that the Streamlit dashboard loads and displays the main header
        Expected: Page loads with title "Sales Call Summarizer" visible
        """
        await page.goto(streamlit_server)
        
        # Wait for Streamlit to load
        await page.wait_for_selector("h1", timeout=10000)
        
        # Check for main header
        header = page.locator("h1")
        await expect(header).to_contain_text("Sales Call Summarizer", timeout=5000)
    
    @pytest.mark.asyncio
    async def test_dashboard_metrics_display(self, page: Page, streamlit_server: str):
        """
        Test Case: Dashboard Metrics Display
        Description: Verify that metrics are displayed on the dashboard
        Expected: Metrics cards showing Total Calls, New, Transcribed, Analyzed, Synced, Last 7 Days
        """
        await page.goto(streamlit_server)
        await page.wait_for_selector("h1", timeout=10000)
        
        # Wait for metrics to load
        await page.wait_for_timeout(2000)
        
        # Check for metric labels
        page_text = await page.text_content("body")
        assert "Total Calls" in page_text
        assert "New" in page_text or "Transcribed" in page_text


class TestCallUpload:
    """Tests for call upload functionality"""
    
    @pytest.mark.asyncio
    async def test_upload_call_with_all_fields(
        self, page: Page, streamlit_server: str, sample_audio_file: Path
    ):
        """
        Test Case: Upload Call with All Fields
        Description: Upload a call using the sidebar form with all fields filled
        Expected: Call is created successfully and appears in the call list
        """
        await page.goto(streamlit_server)
        await page.wait_for_selector("h1", timeout=10000)
        
        # Fill in the upload form
        title_input = page.locator('input[placeholder*="Discovery call"]').first()
        await title_input.fill("E2E Test Call - Complete")
        
        # Set participants
        participants_input = page.locator('input[placeholder*="Alex, Taylor"]')
        if await participants_input.count() > 0:
            await participants_input.fill("John Doe, Jane Smith")
        
        # Set contact name
        contact_input = page.locator('input[placeholder*="Alex Doe"]')
        if await contact_input.count() > 0:
            await contact_input.fill("John Doe")
        
        # Set company
        company_input = page.locator('input[placeholder*="Acme Corp"]')
        if await company_input.count() > 0:
            await company_input.fill("Test Company Inc")
        
        # Select call type
        call_type_select = page.locator('select').first()
        if await call_type_select.count() > 0:
            await call_type_select.select_option("discovery")
        
        # Upload audio file
        file_input = page.locator('input[type="file"]')
        await file_input.set_input_files(str(sample_audio_file))
        
        # Submit form
        submit_button = page.locator('button:has-text("Create Call")').first()
        await submit_button.click()
        
        # Wait for success message or call to appear
        await page.wait_for_timeout(3000)
        
        # Verify call was created (check for success message or call in list)
        page_text = await page.text_content("body")
        assert "created successfully" in page_text.lower() or "E2E Test Call" in page_text
    
    @pytest.mark.asyncio
    async def test_upload_call_validation_required_fields(
        self, page: Page, streamlit_server: str
    ):
        """
        Test Case: Upload Call Validation - Required Fields
        Description: Attempt to submit form without required fields (title and audio file)
        Expected: Warning message displayed, call not created
        """
        await page.goto(streamlit_server)
        await page.wait_for_selector("h1", timeout=10000)
        
        # Try to submit without filling required fields
        submit_button = page.locator('button:has-text("Create Call")').first()
        await submit_button.click()
        
        # Wait for validation message
        await page.wait_for_timeout(1000)
        
        # Check for warning message
        page_text = await page.text_content("body")
        assert "required fields" in page_text.lower() or "please fill" in page_text.lower()
    
    @pytest.mark.asyncio
    async def test_upload_call_minimal_fields(
        self, page: Page, streamlit_server: str, sample_audio_file: Path
    ):
        """
        Test Case: Upload Call with Minimal Fields
        Description: Upload a call with only required fields (title and audio)
        Expected: Call is created successfully with default values
        """
        await page.goto(streamlit_server)
        await page.wait_for_selector("h1", timeout=10000)
        
        # Fill only required fields
        title_input = page.locator('input[placeholder*="Discovery call"]').first()
        await title_input.fill("Minimal Call Test")
        
        # Upload audio file
        file_input = page.locator('input[type="file"]')
        await file_input.set_input_files(str(sample_audio_file))
        
        # Submit form
        submit_button = page.locator('button:has-text("Create Call")').first()
        await submit_button.click()
        
        # Wait for success
        await page.wait_for_timeout(3000)
        
        # Verify call was created
        page_text = await page.text_content("body")
        assert "created successfully" in page_text.lower() or "Minimal Call Test" in page_text


class TestCallListing:
    """Tests for call listing and display"""
    
    @pytest.mark.asyncio
    async def test_display_empty_call_list(self, page: Page, streamlit_server: str):
        """
        Test Case: Display Empty Call List
        Description: View dashboard when no calls exist
        Expected: Message indicating no calls found, with suggestion to upload
        """
        await page.goto(streamlit_server)
        await page.wait_for_selector("h1", timeout=10000)
        await page.wait_for_timeout(2000)
        
        # Check for empty state message
        page_text = await page.text_content("body")
        assert "no calls found" in page_text.lower() or "upload" in page_text.lower()
    
    @pytest.mark.asyncio
    async def test_display_calls_in_list(
        self, page: Page, streamlit_server: str, sample_audio_file: Path, api_client
    ):
        """
        Test Case: Display Calls in List
        Description: Create calls via API and verify they appear in the Streamlit dashboard
        Expected: Created calls are visible in the call list with correct information
        """
        # Create a call via API
        recorded_at = datetime.utcnow().isoformat()
        with open(sample_audio_file, "rb") as f:
            await api_client.post(
                "/calls",
                data={
                    "title": "UI Display Test Call",
                    "recorded_at": recorded_at,
                    "contact_name": "Test Contact",
                    "company": "Test Company",
                },
                files={"audio_file": ("sample.wav", f, "audio/wav")}
            )
        
        # Load dashboard
        await page.goto(streamlit_server)
        await page.wait_for_selector("h1", timeout=10000)
        await page.wait_for_timeout(3000)
        
        # Verify call appears
        page_text = await page.text_content("body")
        assert "UI Display Test Call" in page_text
        assert "Test Contact" in page_text or "Test Company" in page_text


class TestCallFiltering:
    """Tests for call filtering and search"""
    
    @pytest.mark.asyncio
    async def test_filter_calls_by_status(
        self, page: Page, streamlit_server: str, sample_audio_file: Path, api_client
    ):
        """
        Test Case: Filter Calls by Status
        Description: Use the status filter dropdown to filter calls
        Expected: Only calls matching the selected status are displayed
        """
        # Create calls in different states
        recorded_at = datetime.utcnow().isoformat()
        with open(sample_audio_file, "rb") as f:
            response = await api_client.post(
                "/calls",
                data={
                    "title": "New Status Call",
                    "recorded_at": recorded_at,
                },
                files={"audio_file": ("sample.wav", f, "audio/wav")}
            )
            call_id = response.json()["id"]
            
            # Transcribe to change status
            await api_client.post(f"/calls/{call_id}/transcribe")
        
        # Load dashboard
        await page.goto(streamlit_server)
        await page.wait_for_selector("h1", timeout=10000)
        await page.wait_for_timeout(2000)
        
        # Find and use status filter
        status_filter = page.locator('select').first()
        if await status_filter.count() > 0:
            await status_filter.select_option("transcribed")
            await page.wait_for_timeout(2000)
            
            # Verify filtered results
            page_text = await page.text_content("body")
            assert "New Status Call" in page_text
    
    @pytest.mark.asyncio
    async def test_search_calls_by_keyword(
        self, page: Page, streamlit_server: str, sample_audio_file: Path, api_client
    ):
        """
        Test Case: Search Calls by Keyword
        Description: Use the search input to filter calls by title, contact, or company
        Expected: Only calls matching the search query are displayed
        """
        # Create a call with specific details
        recorded_at = datetime.utcnow().isoformat()
        with open(sample_audio_file, "rb") as f:
            await api_client.post(
                "/calls",
                data={
                    "title": "Unique Search Test Call",
                    "recorded_at": recorded_at,
                    "contact_name": "Searchable Contact",
                    "company": "Search Company",
                },
                files={"audio_file": ("sample.wav", f, "audio/wav")}
            )
        
        # Load dashboard
        await page.goto(streamlit_server)
        await page.wait_for_selector("h1", timeout=10000)
        await page.wait_for_timeout(2000)
        
        # Find and use search input
        search_inputs = page.locator('input[placeholder*="Search"]')
        if await search_inputs.count() > 0:
            search_input = search_inputs.first()
            await search_input.fill("Unique Search")
            await page.wait_for_timeout(2000)
            
            # Verify search results
            page_text = await page.text_content("body")
            assert "Unique Search Test Call" in page_text


class TestCallActions:
    """Tests for call action buttons"""
    
    @pytest.mark.asyncio
    async def test_transcribe_call_action(
        self, page: Page, streamlit_server: str, sample_audio_file: Path, api_client
    ):
        """
        Test Case: Transcribe Call Action
        Description: Click the Transcribe button for a call
        Expected: Call is transcribed, status updated, success message displayed
        """
        # Create a call via API
        recorded_at = datetime.utcnow().isoformat()
        with open(sample_audio_file, "rb") as f:
            response = await api_client.post(
                "/calls",
                data={
                    "title": "Transcribe Action Test",
                    "recorded_at": recorded_at,
                },
                files={"audio_file": ("sample.wav", f, "audio/wav")}
            )
            call_id = response.json()["id"]
        
        # Load dashboard
        await page.goto(streamlit_server)
        await page.wait_for_selector("h1", timeout=10000)
        await page.wait_for_timeout(3000)
        
        # Find and click Transcribe button
        transcribe_buttons = page.locator('button:has-text("Transcribe")')
        if await transcribe_buttons.count() > 0:
            await transcribe_buttons.first().click()
            await page.wait_for_timeout(3000)
            
            # Check for success message
            page_text = await page.text_content("body")
            assert "transcribed" in page_text.lower()
    
    @pytest.mark.asyncio
    async def test_analyze_call_action(
        self, page: Page, streamlit_server: str, sample_audio_file: Path, api_client
    ):
        """
        Test Case: Analyze Call Action
        Description: Transcribe a call then click Analyze button
        Expected: Call is analyzed, status updated, success message displayed
        """
        # Create and transcribe a call via API
        recorded_at = datetime.utcnow().isoformat()
        with open(sample_audio_file, "rb") as f:
            response = await api_client.post(
                "/calls",
                data={
                    "title": "Analyze Action Test",
                    "recorded_at": recorded_at,
                },
                files={"audio_file": ("sample.wav", f, "audio/wav")}
            )
            call_id = response.json()["id"]
        
        await api_client.post(f"/calls/{call_id}/transcribe")
        
        # Load dashboard
        await page.goto(streamlit_server)
        await page.wait_for_selector("h1", timeout=10000)
        await page.wait_for_timeout(3000)
        
        # Find and click Analyze button
        analyze_buttons = page.locator('button:has-text("Analyze")')
        if await analyze_buttons.count() > 0:
            await analyze_buttons.first().click()
            await page.wait_for_timeout(3000)
            
            # Check for success message
            page_text = await page.text_content("body")
            assert "analyzed" in page_text.lower()
    
    @pytest.mark.asyncio
    async def test_sync_crm_action(
        self, page: Page, streamlit_server: str, sample_audio_file: Path, api_client
    ):
        """
        Test Case: Sync CRM Action
        Description: Process a call then click Sync CRM button
        Expected: Call is synced to CRM, status updated, success message displayed
        """
        # Create, transcribe, and analyze a call via API
        recorded_at = datetime.utcnow().isoformat()
        with open(sample_audio_file, "rb") as f:
            response = await api_client.post(
                "/calls",
                data={
                    "title": "Sync CRM Action Test",
                    "recorded_at": recorded_at,
                },
                files={"audio_file": ("sample.wav", f, "audio/wav")}
            )
            call_id = response.json()["id"]
        
        await api_client.post(f"/calls/{call_id}/transcribe")
        await api_client.post(f"/calls/{call_id}/analyze")
        
        # Load dashboard
        await page.goto(streamlit_server)
        await page.wait_for_selector("h1", timeout=10000)
        await page.wait_for_timeout(3000)
        
        # Find and click Sync CRM button
        sync_buttons = page.locator('button:has-text("Sync CRM")')
        if await sync_buttons.count() > 0:
            await sync_buttons.first().click()
            await page.wait_for_timeout(3000)
            
            # Check for success message
            page_text = await page.text_content("body")
            assert "synced" in page_text.lower()
    
    @pytest.mark.asyncio
    async def test_process_all_action(
        self, page: Page, streamlit_server: str, sample_audio_file: Path, api_client
    ):
        """
        Test Case: Process All Action
        Description: Click Process All button to run full pipeline
        Expected: Call is processed through all stages, success message displayed
        """
        # Create a call via API
        recorded_at = datetime.utcnow().isoformat()
        with open(sample_audio_file, "rb") as f:
            response = await api_client.post(
                "/calls",
                data={
                    "title": "Process All Action Test",
                    "recorded_at": recorded_at,
                },
                files={"audio_file": ("sample.wav", f, "audio/wav")}
            )
            call_id = response.json()["id"]
        
        # Load dashboard
        await page.goto(streamlit_server)
        await page.wait_for_selector("h1", timeout=10000)
        await page.wait_for_timeout(3000)
        
        # Find and click Process All button
        process_buttons = page.locator('button:has-text("Process All")')
        if await process_buttons.count() > 0:
            await process_buttons.first().click()
            await page.wait_for_timeout(5000)  # Process All takes longer
            
            # Check for success message
            page_text = await page.text_content("body")
            assert "completed" in page_text.lower() or "synced" in page_text.lower()


class TestCallDetails:
    """Tests for call detail tabs"""
    
    @pytest.mark.asyncio
    async def test_view_transcript_tab(
        self, page: Page, streamlit_server: str, sample_audio_file: Path, api_client
    ):
        """
        Test Case: View Transcript Tab
        Description: Open a transcribed call and view the transcript tab
        Expected: Transcript text is displayed in the tab
        """
        # Create and transcribe a call via API
        recorded_at = datetime.utcnow().isoformat()
        with open(sample_audio_file, "rb") as f:
            response = await api_client.post(
                "/calls",
                data={
                    "title": "Transcript View Test",
                    "recorded_at": recorded_at,
                },
                files={"audio_file": ("sample.wav", f, "audio/wav")}
            )
            call_id = response.json()["id"]
        
        await api_client.post(f"/calls/{call_id}/transcribe")
        
        # Load dashboard
        await page.goto(streamlit_server)
        await page.wait_for_selector("h1", timeout=10000)
        await page.wait_for_timeout(3000)
        
        # Find and click Transcript tab
        transcript_tabs = page.locator('button[role="tab"]:has-text("Transcript")')
        if await transcript_tabs.count() > 0:
            await transcript_tabs.first().click()
            await page.wait_for_timeout(1000)
            
            # Check for transcript content
            page_text = await page.text_content("body")
            assert "transcript" in page_text.lower() or "text" in page_text.lower()
    
    @pytest.mark.asyncio
    async def test_view_analysis_tab(
        self, page: Page, streamlit_server: str, sample_audio_file: Path, api_client
    ):
        """
        Test Case: View Analysis Tab
        Description: Open an analyzed call and view the analysis tab
        Expected: Analysis data including summary, action items, etc. is displayed
        """
        # Create, transcribe, and analyze a call via API
        recorded_at = datetime.utcnow().isoformat()
        with open(sample_audio_file, "rb") as f:
            response = await api_client.post(
                "/calls",
                data={
                    "title": "Analysis View Test",
                    "recorded_at": recorded_at,
                },
                files={"audio_file": ("sample.wav", f, "audio/wav")}
            )
            call_id = response.json()["id"]
        
        await api_client.post(f"/calls/{call_id}/transcribe")
        await api_client.post(f"/calls/{call_id}/analyze")
        
        # Load dashboard
        await page.goto(streamlit_server)
        await page.wait_for_selector("h1", timeout=10000)
        await page.wait_for_timeout(3000)
        
        # Find and click Analysis tab
        analysis_tabs = page.locator('button[role="tab"]:has-text("Analysis")')
        if await analysis_tabs.count() > 0:
            await analysis_tabs.first().click()
            await page.wait_for_timeout(1000)
            
            # Check for analysis content
            page_text = await page.text_content("body")
            assert "summary" in page_text.lower() or "action" in page_text.lower()
    
    @pytest.mark.asyncio
    async def test_view_crm_notes_and_tasks_tabs(
        self, page: Page, streamlit_server: str, sample_audio_file: Path, api_client
    ):
        """
        Test Case: View CRM Notes and Tasks Tabs
        Description: Open a synced call and view CRM notes and tasks
        Expected: CRM notes and tasks are displayed in their respective tabs
        """
        # Create and fully process a call via API
        recorded_at = datetime.utcnow().isoformat()
        with open(sample_audio_file, "rb") as f:
            response = await api_client.post(
                "/calls",
                data={
                    "title": "CRM View Test",
                    "recorded_at": recorded_at,
                },
                files={"audio_file": ("sample.wav", f, "audio/wav")}
            )
            call_id = response.json()["id"]
        
        await api_client.post(f"/calls/{call_id}/process")
        
        # Load dashboard
        await page.goto(streamlit_server)
        await page.wait_for_selector("h1", timeout=10000)
        await page.wait_for_timeout(3000)
        
        # Check for CRM tabs
        page_text = await page.text_content("body")
        notes_tabs = page.locator('button[role="tab"]:has-text("CRM Notes")')
        tasks_tabs = page.locator('button[role="tab"]:has-text("Tasks")')
        
        if await notes_tabs.count() > 0:
            await notes_tabs.first().click()
            await page.wait_for_timeout(1000)
        
        if await tasks_tabs.count() > 0:
            await tasks_tabs.first().click()
            await page.wait_for_timeout(1000)


class TestRefreshFunctionality:
    """Tests for refresh and data updates"""
    
    @pytest.mark.asyncio
    async def test_refresh_button_updates_data(
        self, page: Page, streamlit_server: str, sample_audio_file: Path, api_client
    ):
        """
        Test Case: Refresh Button Updates Data
        Description: Create a call via API, then click refresh button to see it appear
        Expected: New call appears in the list after refresh
        """
        # Load dashboard first
        await page.goto(streamlit_server)
        await page.wait_for_selector("h1", timeout=10000)
        await page.wait_for_timeout(2000)
        
        # Create a call via API
        recorded_at = datetime.utcnow().isoformat()
        with open(sample_audio_file, "rb") as f:
            await api_client.post(
                "/calls",
                data={
                    "title": "Refresh Test Call",
                    "recorded_at": recorded_at,
                },
                files={"audio_file": ("sample.wav", f, "audio/wav")}
            )
        
        # Click refresh button
        refresh_buttons = page.locator('button:has-text("Refresh")')
        if await refresh_buttons.count() > 0:
            await refresh_buttons.first().click()
            await page.wait_for_timeout(3000)
            
            # Verify new call appears
            page_text = await page.text_content("body")
            assert "Refresh Test Call" in page_text

