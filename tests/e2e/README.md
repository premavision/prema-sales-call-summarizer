# End-to-End Tests

This directory contains comprehensive end-to-end (e2e) tests for the Prema Vision Sales Call Summarizer application. The tests use Playwright for browser automation and cover both the FastAPI backend and Streamlit frontend.

## Overview

The e2e test suite is organized into two main categories:

1. **API Tests** (`test_api_endpoints.py`) - Tests for all FastAPI endpoints
2. **UI Tests** (`test_streamlit_ui.py`) - Tests for Streamlit dashboard interactions

## Test Coverage

### API Endpoints Coverage

#### Health Endpoint
- ✅ Health check returns successful response

#### Call Creation
- ✅ Create call with all fields populated
- ✅ Create call with minimal required fields
- ✅ Validation for missing required fields
- ✅ Validation for invalid datetime format
- ✅ Handling of empty participants

#### Call Listing
- ✅ List calls when database is empty
- ✅ List multiple calls
- ✅ Filter calls by status

#### Call Details
- ✅ Get call details for existing call
- ✅ Get call details for non-existent call (404)
- ✅ Get call details with transcript and analysis

#### Transcription Workflow
- ✅ Transcribe call successfully
- ✅ Transcribe non-existent call (error handling)
- ✅ Transcribe already transcribed call

#### Analysis Workflow
- ✅ Analyze call successfully
- ✅ Analyze call without transcription (error handling)
- ✅ Analyze non-existent call (error handling)

#### CRM Sync Workflow
- ✅ Sync call to CRM successfully
- ✅ Sync call without analysis (error handling)
- ✅ Sync call multiple times

#### Pipeline Processing
- ✅ Process call through full pipeline
- ✅ Process non-existent call (error handling)

#### End-to-End Workflows
- ✅ Complete workflow with manual steps
- ✅ Process multiple calls in sequence

### UI/Streamlit Dashboard Coverage

#### Dashboard Loading
- ✅ Dashboard loads successfully
- ✅ Dashboard metrics display correctly

#### Call Upload
- ✅ Upload call with all fields
- ✅ Upload call validation for required fields
- ✅ Upload call with minimal fields

#### Call Listing
- ✅ Display empty call list
- ✅ Display calls in list

#### Call Filtering
- ✅ Filter calls by status
- ✅ Search calls by keyword

#### Call Actions
- ✅ Transcribe call action
- ✅ Analyze call action
- ✅ Sync CRM action
- ✅ Process All action

#### Call Details
- ✅ View transcript tab
- ✅ View analysis tab
- ✅ View CRM notes and tasks tabs

#### Refresh Functionality
- ✅ Refresh button updates data

## Setup

### Prerequisites

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Install Playwright browsers:
```bash
playwright install chromium
```

Or install all browsers:
```bash
playwright install
```

### Environment Setup

The tests use a temporary database and audio directory. No manual setup is required - the test fixtures handle this automatically.

## Running Tests

### Run All E2E Tests

```bash
pytest tests/e2e/ -v
```

### Run Only API Tests

```bash
pytest tests/e2e/test_api_endpoints.py -v
```

### Run Only UI Tests

```bash
pytest tests/e2e/test_streamlit_ui.py -v
```

### Run Specific Test Class

```bash
pytest tests/e2e/test_api_endpoints.py::TestCallCreation -v
```

### Run Specific Test

```bash
pytest tests/e2e/test_api_endpoints.py::TestCallCreation::test_create_call_with_all_fields -v
```

### Run with Headed Browser (for debugging)

To see the browser during UI tests, you can modify the `browser` fixture in `conftest.py` to set `headless=False`.

### Run with Screenshots

Playwright automatically captures screenshots on failure. Screenshots are saved in the `test-results/` directory.

## Test Structure

### Test Organization

Tests are organized by functionality:
- Each test class focuses on a specific feature or endpoint
- Each test method includes a descriptive docstring explaining:
  - **Test Case**: Name of the test scenario
  - **Description**: What is being tested
  - **Expected**: Expected outcome

### Fixtures

Key fixtures provided in `conftest.py`:

- `fastapi_server`: Starts FastAPI server on port 8888
- `streamlit_server`: Starts Streamlit server on port 8889
- `api_client`: HTTP client for API testing
- `page`: Playwright page for UI testing
- `sample_audio_file`: Sample audio file for testing
- `test_db_path`: Temporary database path
- `test_audio_dir`: Temporary audio directory

### Test Data

Tests use:
- Stub transcription client (no external API calls)
- Stub LLM client (no external API calls)
- Fake CRM client (local storage only)
- Temporary database (SQLite in-memory or temp file)
- Temporary audio directory

## Best Practices

### Writing New Tests

1. **Use descriptive test names**: Test names should clearly describe what they test
2. **Include docstrings**: Each test should have a docstring with Test Case, Description, and Expected
3. **Test both success and failure cases**: Include tests for error handling
4. **Keep tests independent**: Each test should be able to run independently
5. **Clean up after tests**: Use fixtures for cleanup (already handled)

### Debugging Tests

1. **Use `pytest --pdb`**: Drop into debugger on failure
2. **Use `page.pause()`**: Pause Playwright execution for debugging
3. **Check screenshots**: Failed tests automatically capture screenshots
4. **Use headed mode**: Set `headless=False` in browser fixture to see browser

## CI/CD Integration

These tests are designed to run in CI/CD pipelines. They:
- Use headless browsers
- Clean up resources automatically
- Use temporary directories
- Are isolated from production data

### Example GitHub Actions

```yaml
- name: Install Playwright
  run: |
    pip install -r requirements.txt
    playwright install chromium

- name: Run E2E Tests
  run: pytest tests/e2e/ -v
```

## Troubleshooting

### Server Startup Issues

If servers fail to start:
- Check if ports 8888 and 8889 are available
- Increase wait time in server fixtures
- Check server logs for errors

### Browser Issues

If browser tests fail:
- Ensure Playwright browsers are installed: `playwright install`
- Try updating Playwright: `pip install --upgrade playwright`
- Check for browser compatibility issues

### Database Issues

If database tests fail:
- Ensure SQLite is available
- Check file permissions for temp directory
- Verify database URL in test fixtures

## Notes

- Tests are designed to be fast and isolated
- Each test uses fresh database state
- Audio files are cleaned up automatically
- Servers are started and stopped automatically
- No external dependencies (OpenAI, etc.) are required for tests

