# Prema Vision | Sales Call Summarizer & CRM Sync

Portfolio-grade mini-product that ingests sales/CS call recordings, transcribes them, extracts insights with an LLM, and syncs notes/tasks to a CRM (fake CRM for MVP). Built with FastAPI, SQLModel/SQLite, and Streamlit.

## Why this exists
Sales and CS teams lose context between calls. This prototype automates the capture of what happened, risks, and next steps, and pushes structured updates into a CRM-friendly shape. It is intentionally small but realistic so it can be piloted or extended into a production integration.

## Architecture
- Calls uploaded via FastAPI or the Streamlit dashboard are stored on disk (`data/audio`) and registered in SQLite.
- Transcription workflow delegates to a pluggable `TranscriptionClient` (Whisper via OpenAI or stub) and stores results.
- Analysis workflow delegates to a pluggable `LLMClient` (OpenAI Chat or stub) with a focused prompt to produce summary bullets, risks/objections, action items, and a follow-up draft.
- CRM sync delegates to a `CRMClient`; the default `FakeCRMClient` writes notes/tasks to local tables and logs sync attempts. Real HubSpot/Pipedrive/Salesforce clients can be slotted in without changing business logic.
- FastAPI exposes a thin API on top of services; Streamlit reads/writes via the same services for a quick demo UI.

### High-level flow
1) Upload call (metadata + audio) → audio saved under `data/audio`, row added to `call` table.  
2) Transcribe → `TranscriptionClient` produces text/metadata, stored in `transcript`, call status → TRANSCRIBED.  
3) Analyze → `LLMClient` generates structured insights/actions, stored in `callanalysis`, call status → ANALYZED.  
4) CRM sync → `CRMClient` pushes summary/tasks (fake client stores locally), sync log recorded, call status → SYNCED.

## Getting started
### Prerequisites
- Python 3.11+
- Optional: valid `OPENAI_API_KEY` if you want real Whisper/LLM behavior.

### Install
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set values in `.env` as needed (e.g., `OPENAI_API_KEY`, `ASR_PROVIDER=whisper` to use OpenAI Whisper, otherwise defaults to stubs).

### Run FastAPI
```bash
uvicorn app.main:app --reload
```
API docs: http://localhost:8000/docs

### Run Streamlit dashboard
```bash
streamlit run app/ui/streamlit/dashboard.py
```
Upload a sample audio file (place under `data/audio` if you want to reference it) and trigger transcribe → analyze → sync actions from the UI.

## API quickstart
- Health: `GET /health`
- Create call (multipart): `POST /calls` with form fields `title`, `recorded_at` (ISO), optional `participants`, `call_type`, etc., plus `audio_file`.
- Transcribe: `POST /calls/{id}/transcribe`
- Analyze: `POST /calls/{id}/analyze`
- Sync CRM: `POST /calls/{id}/sync-crm`
- Full pipeline: `POST /calls/{id}/process`

Example (after running uvicorn):
```bash
curl -F "title=Demo call" \
     -F "recorded_at=2024-01-01T12:00:00" \
     -F "participants=Alex,Sam" \
     -F "call_type=discovery" \
     -F "audio_file=@data/audio/sample.wav" \
     http://localhost:8000/calls
```

## Testing

### Unit and Integration Tests
```bash
pytest
```
Tests cover call creation, transcription workflow (stub client), analysis workflow (stub LLM), and CRM sync (fake client).

### End-to-End Tests
Comprehensive E2E tests using Playwright cover both the FastAPI backend and Streamlit frontend:

```bash
# Install Playwright browsers first
playwright install chromium

# Run all E2E tests
pytest tests/e2e/ -v

# Run only API E2E tests
pytest tests/e2e/test_api_endpoints.py -v

# Run only UI E2E tests
pytest tests/e2e/test_streamlit_ui.py -v
```

See [tests/e2e/README.md](tests/e2e/README.md) for detailed documentation on E2E tests, including:
- Complete test coverage (42 tests: 25 API + 17 UI)
- Test organization and structure
- Running and debugging tests
- CI/CD integration examples

## Notes on privacy and deployment
- Call recordings and transcripts are sensitive; by default they stay on disk (`data/audio`) and in local SQLite. If using external providers (OpenAI), data leaves the machine—confirm compliance with client policies.
- For pilots, deploy on client-owned infrastructure or VPC; swap in real CRM clients by implementing `CRMClient` and wiring via config without touching services.
- Environment-driven configuration keeps secrets out of code; see `.env.example`.
