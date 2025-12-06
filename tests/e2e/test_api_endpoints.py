"""
End-to-End API Tests

This test suite covers all FastAPI endpoints with comprehensive scenarios:
- Health check endpoint
- Call creation with file upload
- Call listing and filtering
- Call detail retrieval
- Transcription workflow
- Analysis workflow
- CRM sync workflow
- Full pipeline processing
- Error handling and edge cases
"""
import io
from datetime import datetime
from pathlib import Path

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.e2e, pytest.mark.api]


class TestHealthEndpoint:
    """Tests for the health check endpoint"""
    
    @pytest.mark.asyncio
    async def test_health_check(self, api_client: AsyncClient):
        """
        Test Case: Health Check Endpoint
        Description: Verify that the health endpoint returns a successful response
        Expected: Returns 200 OK with {"status": "ok"}
        """
        response = await api_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data == {"status": "ok"}


class TestCallCreation:
    """Tests for call creation endpoint"""
    
    @pytest.mark.asyncio
    async def test_create_call_with_all_fields(self, api_client: AsyncClient, sample_audio_file: Path):
        """
        Test Case: Create Call with All Fields
        Description: Create a call with all optional fields populated
        Expected: Returns 201 Created with call data including all fields
        """
        recorded_at = datetime.utcnow().isoformat()
        
        with open(sample_audio_file, "rb") as f:
            response = await api_client.post(
                "/calls",
                data={
                    "title": "Discovery Call - Acme Corp",
                    "recorded_at": recorded_at,
                    "participants": "Alex Smith, Taylor Johnson",
                    "call_type": "discovery",
                    "contact_name": "Alex Smith",
                    "company": "Acme Corp",
                    "crm_deal_id": "DEAL-123",
                    "external_id": "EXT-456",
                },
                files={"audio_file": ("sample.wav", f, "audio/wav")}
            )
        
        assert response.status_code in [200, 201]  # FastAPI may return 200 or 201
        data = response.json()
        assert data["title"] == "Discovery Call - Acme Corp"
        assert data["contact_name"] == "Alex Smith"
        assert data["company"] == "Acme Corp"
        assert data["call_type"] == "discovery"
        assert data["crm_deal_id"] == "DEAL-123"
        assert data["external_id"] == "EXT-456"
        assert len(data["participants"]) == 2
        assert "Alex Smith" in data["participants"]
        assert "Taylor Johnson" in data["participants"]
        assert "id" in data
        assert data["status"].upper() == "NEW"
    
    @pytest.mark.asyncio
    async def test_create_call_minimal_fields(self, api_client: AsyncClient, sample_audio_file: Path):
        """
        Test Case: Create Call with Minimal Required Fields
        Description: Create a call with only title, recorded_at, and audio_file
        Expected: Returns 201 Created with call data using default values
        """
        recorded_at = datetime.utcnow().isoformat()
        
        with open(sample_audio_file, "rb") as f:
            response = await api_client.post(
                "/calls",
                data={
                    "title": "Minimal Call",
                    "recorded_at": recorded_at,
                },
                files={"audio_file": ("sample.wav", f, "audio/wav")}
            )
        
        assert response.status_code in [200, 201]  # FastAPI may return 200 or 201
        data = response.json()
        assert data["title"] == "Minimal Call"
        assert data["status"].upper() == "NEW"
        assert data["participants"] == []
    
    @pytest.mark.asyncio
    async def test_create_call_missing_required_fields(self, api_client: AsyncClient):
        """
        Test Case: Create Call with Missing Required Fields
        Description: Attempt to create a call without required fields
        Expected: Returns 422 Unprocessable Entity
        """
        # Missing title
        response = await api_client.post(
            "/calls",
            data={"recorded_at": datetime.utcnow().isoformat()},
            files={"audio_file": ("test.wav", io.BytesIO(b"dummy"), "audio/wav")}
        )
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_create_call_invalid_datetime(self, api_client: AsyncClient, sample_audio_file: Path):
        """
        Test Case: Create Call with Invalid DateTime Format
        Description: Attempt to create a call with invalid ISO datetime format
        Expected: Returns 400 Bad Request with error message
        """
        with open(sample_audio_file, "rb") as f:
            response = await api_client.post(
                "/calls",
                data={
                    "title": "Test Call",
                    "recorded_at": "invalid-datetime",
                },
                files={"audio_file": ("sample.wav", f, "audio/wav")}
            )
        
        assert response.status_code == 400
        detail = response.json()["detail"].lower()
        assert "iso datetime" in detail or "datetime" in detail
    
    @pytest.mark.asyncio
    async def test_create_call_with_empty_participants(self, api_client: AsyncClient, sample_audio_file: Path):
        """
        Test Case: Create Call with Empty Participants
        Description: Create a call with empty participants string
        Expected: Returns 201 Created with empty participants list
        """
        recorded_at = datetime.utcnow().isoformat()
        
        with open(sample_audio_file, "rb") as f:
            response = await api_client.post(
                "/calls",
                data={
                    "title": "Call Without Participants",
                    "recorded_at": recorded_at,
                    "participants": "",
                },
                files={"audio_file": ("sample.wav", f, "audio/wav")}
            )
        
        assert response.status_code in [200, 201]  # FastAPI may return 200 or 201
        data = response.json()
        assert data["participants"] == []


class TestCallListing:
    """Tests for call listing endpoint"""
    
    @pytest.mark.asyncio
    async def test_list_calls_empty(self, api_client: AsyncClient):
        """
        Test Case: List Calls When Database is Empty
        Description: Retrieve list of calls - verify endpoint returns array (may not be empty due to other tests)
        Expected: Returns 200 OK with array (which may contain calls from other tests)
        """
        response = await api_client.get("/calls")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Note: Database is session-scoped, so may contain data from other tests
    
    @pytest.mark.asyncio
    async def test_list_calls_with_multiple_calls(self, api_client: AsyncClient, sample_audio_file: Path):
        """
        Test Case: List Multiple Calls
        Description: Create multiple calls and verify they are all returned
        Expected: Returns 200 OK with all created calls
        """
        recorded_at = datetime.utcnow().isoformat()
        call_ids = []
        
        # Create 3 calls
        for i in range(3):
            with open(sample_audio_file, "rb") as f:
                response = await api_client.post(
                    "/calls",
                    data={
                        "title": f"Test Call {i+1}",
                        "recorded_at": recorded_at,
                    },
                    files={"audio_file": ("sample.wav", f, "audio/wav")}
                )
                assert response.status_code in [200, 201]  # FastAPI may return 200 or 201
                call_ids.append(response.json()["id"])
        
        # List all calls
        response = await api_client.get("/calls")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 3  # May have more calls from other tests
        returned_ids = [call["id"] for call in data]
        assert all(cid in returned_ids for cid in call_ids)  # All our calls should be present
    
    @pytest.mark.asyncio
    async def test_list_calls_filtered_by_status(self, api_client: AsyncClient, sample_audio_file: Path):
        """
        Test Case: List Calls Filtered by Status
        Description: Create calls in different states and filter by status
        Expected: Returns only calls matching the specified status
        """
        recorded_at = datetime.utcnow().isoformat()
        
        # Create a call
        with open(sample_audio_file, "rb") as f:
            response = await api_client.post(
                "/calls",
                data={
                    "title": "Test Call for Status Filter",
                    "recorded_at": recorded_at,
                },
                files={"audio_file": ("sample.wav", f, "audio/wav")}
            )
            call_id = response.json()["id"]
        
        # Transcribe it to change status
        await api_client.post(f"/calls/{call_id}/transcribe")
        
        # List only new calls
        response = await api_client.get("/calls?status=NEW")
        assert response.status_code == 200
        data = response.json()
        # Should not include our call since it's now transcribed
        assert all(call["status"].upper() == "NEW" for call in data)
        assert call_id not in [call["id"] for call in data]
        
        # List transcribed calls
        response = await api_client.get("/calls?status=TRANSCRIBED")
        assert response.status_code == 200
        data = response.json()
        assert any(call["id"] == call_id and call["status"].upper() == "TRANSCRIBED" for call in data)


class TestCallDetails:
    """Tests for call detail endpoint"""
    
    @pytest.mark.asyncio
    async def test_get_call_detail_existing(self, api_client: AsyncClient, sample_audio_file: Path):
        """
        Test Case: Get Call Details for Existing Call
        Description: Retrieve full details of a specific call
        Expected: Returns 200 OK with complete call information including transcript, analysis, etc.
        """
        recorded_at = datetime.utcnow().isoformat()
        
        # Create a call
        with open(sample_audio_file, "rb") as f:
            response = await api_client.post(
                "/calls",
                data={
                    "title": "Detailed Call Test",
                    "recorded_at": recorded_at,
                    "contact_name": "John Doe",
                    "company": "Test Corp",
                },
                files={"audio_file": ("sample.wav", f, "audio/wav")}
            )
            call_id = response.json()["id"]
        
        # Get call details
        response = await api_client.get(f"/calls/{call_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["call"]["id"] == call_id
        assert data["call"]["title"] == "Detailed Call Test"
        assert data["call"]["contact_name"] == "John Doe"
        assert data["call"]["company"] == "Test Corp"
        assert "transcript" in data
        assert "analysis" in data
        assert "crm_notes" in data
        assert "crm_tasks" in data
        assert "crm_sync_logs" in data
    
    @pytest.mark.asyncio
    async def test_get_call_detail_nonexistent(self, api_client: AsyncClient):
        """
        Test Case: Get Call Details for Non-Existent Call
        Description: Attempt to retrieve details of a call that doesn't exist
        Expected: Returns 404 Not Found
        """
        response = await api_client.get("/calls/99999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_get_call_detail_with_transcript_and_analysis(
        self, api_client: AsyncClient, sample_audio_file: Path
    ):
        """
        Test Case: Get Call Details with Transcript and Analysis
        Description: Process a call through transcription and analysis, then retrieve details
        Expected: Returns complete details including transcript text and analysis insights
        """
        recorded_at = datetime.utcnow().isoformat()
        
        # Create and process a call
        with open(sample_audio_file, "rb") as f:
            response = await api_client.post(
                "/calls",
                data={
                    "title": "Processed Call",
                    "recorded_at": recorded_at,
                },
                files={"audio_file": ("sample.wav", f, "audio/wav")}
            )
            call_id = response.json()["id"]
        
        # Transcribe
        await api_client.post(f"/calls/{call_id}/transcribe")
        
        # Analyze
        await api_client.post(f"/calls/{call_id}/analyze")
        
        # Get details
        response = await api_client.get(f"/calls/{call_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["transcript"] is not None
        assert data["transcript"]["text"] is not None
        assert data["analysis"] is not None
        assert data["call"]["status"].upper() == "ANALYZED"


class TestTranscriptionWorkflow:
    """Tests for transcription endpoint"""
    
    @pytest.mark.asyncio
    async def test_transcribe_call_success(self, api_client: AsyncClient, sample_audio_file: Path):
        """
        Test Case: Transcribe Call Successfully
        Description: Transcribe a new call
        Expected: Returns 200 OK with transcript data, call status updated to TRANSCRIBED
        """
        recorded_at = datetime.utcnow().isoformat()
        
        # Create a call
        with open(sample_audio_file, "rb") as f:
            response = await api_client.post(
                "/calls",
                data={
                    "title": "Call to Transcribe",
                    "recorded_at": recorded_at,
                },
                files={"audio_file": ("sample.wav", f, "audio/wav")}
            )
            call_id = response.json()["id"]
        
        # Transcribe
        response = await api_client.post(f"/calls/{call_id}/transcribe")
        assert response.status_code == 200
        data = response.json()
        assert "text" in data
        assert "language" in data
        assert data["call_id"] == call_id
        
        # Verify call status updated
        call_response = await api_client.get(f"/calls/{call_id}")
        assert call_response.json()["call"]["status"].upper() == "TRANSCRIBED"
    
    @pytest.mark.asyncio
    async def test_transcribe_call_nonexistent(self, api_client: AsyncClient):
        """
        Test Case: Transcribe Non-Existent Call
        Description: Attempt to transcribe a call that doesn't exist
        Expected: Returns 400 Bad Request with error message
        """
        response = await api_client.post("/calls/99999/transcribe")
        assert response.status_code == 400
    
    @pytest.mark.asyncio
    async def test_transcribe_call_already_transcribed(self, api_client: AsyncClient, sample_audio_file: Path):
        """
        Test Case: Transcribe Already Transcribed Call
        Description: Attempt to transcribe a call that has already been transcribed
        Expected: Should handle gracefully (may update or skip based on implementation)
        """
        recorded_at = datetime.utcnow().isoformat()
        
        # Create and transcribe a call
        with open(sample_audio_file, "rb") as f:
            response = await api_client.post(
                "/calls",
                data={
                    "title": "Double Transcribe Test",
                    "recorded_at": recorded_at,
                },
                files={"audio_file": ("sample.wav", f, "audio/wav")}
            )
            call_id = response.json()["id"]
        
        # First transcription
        response1 = await api_client.post(f"/calls/{call_id}/transcribe")
        assert response1.status_code == 200
        
        # Second transcription attempt
        response2 = await api_client.post(f"/calls/{call_id}/transcribe")
        # Implementation may allow re-transcription or return error
        assert response2.status_code in [200, 400]


class TestAnalysisWorkflow:
    """Tests for analysis endpoint"""
    
    @pytest.mark.asyncio
    async def test_analyze_call_success(self, api_client: AsyncClient, sample_audio_file: Path):
        """
        Test Case: Analyze Call Successfully
        Description: Analyze a transcribed call
        Expected: Returns 200 OK with analysis data including summary, action items, etc.
        """
        recorded_at = datetime.utcnow().isoformat()
        
        # Create and transcribe a call
        with open(sample_audio_file, "rb") as f:
            response = await api_client.post(
                "/calls",
                data={
                    "title": "Call to Analyze",
                    "recorded_at": recorded_at,
                },
                files={"audio_file": ("sample.wav", f, "audio/wav")}
            )
            call_id = response.json()["id"]
        
        await api_client.post(f"/calls/{call_id}/transcribe")
        
        # Analyze
        response = await api_client.post(f"/calls/{call_id}/analyze")
        assert response.status_code == 200
        data = response.json()
        assert data["call_id"] == call_id
        assert "summary" in data or "action_items" in data  # At least some analysis fields
        
        # Verify call status updated
        call_response = await api_client.get(f"/calls/{call_id}")
        assert call_response.json()["call"]["status"].upper() == "ANALYZED"
    
    @pytest.mark.asyncio
    async def test_analyze_call_without_transcription(self, api_client: AsyncClient, sample_audio_file: Path):
        """
        Test Case: Analyze Call Without Transcription
        Description: Attempt to analyze a call that hasn't been transcribed
        Expected: Returns 400 Bad Request with appropriate error message
        """
        recorded_at = datetime.utcnow().isoformat()
        
        # Create a call without transcribing
        with open(sample_audio_file, "rb") as f:
            response = await api_client.post(
                "/calls",
                data={
                    "title": "Call Without Transcript",
                    "recorded_at": recorded_at,
                },
                files={"audio_file": ("sample.wav", f, "audio/wav")}
            )
            call_id = response.json()["id"]
        
        # Attempt to analyze
        response = await api_client.post(f"/calls/{call_id}/analyze")
        assert response.status_code == 400
    
    @pytest.mark.asyncio
    async def test_analyze_call_nonexistent(self, api_client: AsyncClient):
        """
        Test Case: Analyze Non-Existent Call
        Description: Attempt to analyze a call that doesn't exist
        Expected: Returns 400 Bad Request
        """
        response = await api_client.post("/calls/99999/analyze")
        assert response.status_code == 400


class TestCRMSyncWorkflow:
    """Tests for CRM sync endpoint"""
    
    @pytest.mark.asyncio
    async def test_sync_crm_success(self, api_client: AsyncClient, sample_audio_file: Path):
        """
        Test Case: Sync Call to CRM Successfully
        Description: Sync a fully processed call to CRM
        Expected: Returns 200 OK with sync log, call status updated to SYNCED
        """
        recorded_at = datetime.utcnow().isoformat()
        
        # Create, transcribe, and analyze a call
        with open(sample_audio_file, "rb") as f:
            response = await api_client.post(
                "/calls",
                data={
                    "title": "Call to Sync",
                    "recorded_at": recorded_at,
                    "crm_deal_id": "DEAL-789",
                },
                files={"audio_file": ("sample.wav", f, "audio/wav")}
            )
            call_id = response.json()["id"]
        
        await api_client.post(f"/calls/{call_id}/transcribe")
        await api_client.post(f"/calls/{call_id}/analyze")
        
        # Sync to CRM
        response = await api_client.post(f"/calls/{call_id}/sync-crm")
        assert response.status_code == 200
        data = response.json()
        assert data["call_id"] == call_id
        assert "status" in data
        assert "created_at" in data
        
        # Verify call status updated
        call_response = await api_client.get(f"/calls/{call_id}")
        assert call_response.json()["call"]["status"].upper() == "SYNCED"
        
        # Verify CRM notes and tasks were created
        call_detail = call_response.json()
        assert len(call_detail["crm_notes"]) > 0 or len(call_detail["crm_tasks"]) > 0
    
    @pytest.mark.asyncio
    async def test_sync_crm_without_analysis(self, api_client: AsyncClient, sample_audio_file: Path):
        """
        Test Case: Sync Call to CRM Without Analysis
        Description: Attempt to sync a call that hasn't been analyzed
        Expected: Returns 400 Bad Request with error message
        """
        recorded_at = datetime.utcnow().isoformat()
        
        # Create and transcribe a call (no analysis)
        with open(sample_audio_file, "rb") as f:
            response = await api_client.post(
                "/calls",
                data={
                    "title": "Call Without Analysis",
                    "recorded_at": recorded_at,
                },
                files={"audio_file": ("sample.wav", f, "audio/wav")}
            )
            call_id = response.json()["id"]
        
        await api_client.post(f"/calls/{call_id}/transcribe")
        
        # Attempt to sync
        response = await api_client.post(f"/calls/{call_id}/sync-crm")
        assert response.status_code == 400
    
    @pytest.mark.asyncio
    async def test_sync_crm_multiple_times(self, api_client: AsyncClient, sample_audio_file: Path):
        """
        Test Case: Sync Call to CRM Multiple Times
        Description: Sync the same call to CRM multiple times
        Expected: Each sync creates a new sync log entry
        """
        recorded_at = datetime.utcnow().isoformat()
        
        # Create and process a call
        with open(sample_audio_file, "rb") as f:
            response = await api_client.post(
                "/calls",
                data={
                    "title": "Multiple Sync Test",
                    "recorded_at": recorded_at,
                },
                files={"audio_file": ("sample.wav", f, "audio/wav")}
            )
            call_id = response.json()["id"]
        
        await api_client.post(f"/calls/{call_id}/transcribe")
        await api_client.post(f"/calls/{call_id}/analyze")
        
        # Sync multiple times
        await api_client.post(f"/calls/{call_id}/sync-crm")
        await api_client.post(f"/calls/{call_id}/sync-crm")
        
        # Verify multiple sync logs
        call_response = await api_client.get(f"/calls/{call_id}")
        sync_logs = call_response.json()["crm_sync_logs"]
        assert len(sync_logs) >= 2


class TestPipelineProcessing:
    """Tests for full pipeline processing endpoint"""
    
    @pytest.mark.asyncio
    async def test_process_call_full_pipeline(self, api_client: AsyncClient, sample_audio_file: Path):
        """
        Test Case: Process Call Through Full Pipeline
        Description: Use the process endpoint to run transcription, analysis, and CRM sync in sequence
        Expected: Returns 200 OK, call fully processed with status SYNCED
        """
        recorded_at = datetime.utcnow().isoformat()
        
        # Create a call
        with open(sample_audio_file, "rb") as f:
            response = await api_client.post(
                "/calls",
                data={
                    "title": "Full Pipeline Test",
                    "recorded_at": recorded_at,
                },
                files={"audio_file": ("sample.wav", f, "audio/wav")}
            )
            call_id = response.json()["id"]
        
        # Process full pipeline
        response = await api_client.post(f"/calls/{call_id}/process")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        
        # Verify call is fully processed
        call_response = await api_client.get(f"/calls/{call_id}")
        call_data = call_response.json()
        assert call_data["call"]["status"].upper() == "SYNCED"
        assert call_data["transcript"] is not None
        assert call_data["analysis"] is not None
        assert len(call_data["crm_sync_logs"]) > 0
    
    @pytest.mark.asyncio
    async def test_process_call_nonexistent(self, api_client: AsyncClient):
        """
        Test Case: Process Non-Existent Call
        Description: Attempt to process a call that doesn't exist
        Expected: Returns 400 Bad Request
        """
        response = await api_client.post("/calls/99999/process")
        assert response.status_code == 400


class TestEndToEndWorkflow:
    """Tests for complete end-to-end workflows"""
    
    @pytest.mark.asyncio
    async def test_complete_workflow_manual_steps(self, api_client: AsyncClient, sample_audio_file: Path):
        """
        Test Case: Complete Workflow with Manual Steps
        Description: Create a call and process it step-by-step through all stages
        Expected: Call progresses through NEW → TRANSCRIBED → ANALYZED → SYNCED
        """
        recorded_at = datetime.utcnow().isoformat()
        
        # Step 1: Create call
        with open(sample_audio_file, "rb") as f:
            response = await api_client.post(
                "/calls",
                data={
                    "title": "Manual Workflow Test",
                    "recorded_at": recorded_at,
                    "contact_name": "Jane Doe",
                    "company": "Test Company",
                    "call_type": "demo",
                },
                files={"audio_file": ("sample.wav", f, "audio/wav")}
            )
            call_id = response.json()["id"]
        
        # Verify initial state
        call_response = await api_client.get(f"/calls/{call_id}")
        assert call_response.json()["call"]["status"].upper() == "NEW"
        
        # Step 2: Transcribe
        await api_client.post(f"/calls/{call_id}/transcribe")
        call_response = await api_client.get(f"/calls/{call_id}")
        assert call_response.json()["call"]["status"].upper() == "TRANSCRIBED"
        assert call_response.json()["transcript"] is not None
        
        # Step 3: Analyze
        await api_client.post(f"/calls/{call_id}/analyze")
        call_response = await api_client.get(f"/calls/{call_id}")
        assert call_response.json()["call"]["status"].upper() == "ANALYZED"
        assert call_response.json()["analysis"] is not None
        
        # Step 4: Sync to CRM
        await api_client.post(f"/calls/{call_id}/sync-crm")
        call_response = await api_client.get(f"/calls/{call_id}")
        assert call_response.json()["call"]["status"].upper() == "SYNCED"
        assert len(call_response.json()["crm_sync_logs"]) > 0
    
    @pytest.mark.asyncio
    async def test_multiple_calls_workflow(self, api_client: AsyncClient, sample_audio_file: Path):
        """
        Test Case: Process Multiple Calls in Sequence
        Description: Create and process multiple calls to verify system handles concurrent operations
        Expected: All calls are processed independently and correctly
        """
        recorded_at = datetime.utcnow().isoformat()
        call_ids = []
        
        # Create 3 calls
        for i in range(3):
            with open(sample_audio_file, "rb") as f:
                response = await api_client.post(
                    "/calls",
                    data={
                        "title": f"Batch Call {i+1}",
                        "recorded_at": recorded_at,
                    },
                    files={"audio_file": ("sample.wav", f, "audio/wav")}
                )
                call_ids.append(response.json()["id"])
        
        # Process all calls
        for call_id in call_ids:
            await api_client.post(f"/calls/{call_id}/process")
        
        # Verify all are synced
        list_response = await api_client.get("/calls?status=SYNCED")
        synced_ids = [call["id"] for call in list_response.json()]
        synced_call_statuses = [call["status"].upper() for call in list_response.json()]
        assert all(status == "SYNCED" for status in synced_call_statuses)
        assert all(cid in synced_ids for cid in call_ids)
