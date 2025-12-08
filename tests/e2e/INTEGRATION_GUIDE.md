# E2E Test Integration Guide

## Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### Run Tests

```bash
# Run all e2e tests
pytest tests/e2e/ -v

# Run only API tests
pytest tests/e2e/test_api_endpoints.py -v

# Run only UI tests
pytest tests/e2e/test_streamlit_ui.py -v

# Run with markers
pytest -m e2e -v
pytest -m api -v
pytest -m ui -v
```

## Architecture

### Test Structure

```
tests/e2e/
├── __init__.py              # Package initialization
├── conftest.py              # Shared fixtures and configuration
├── test_api_endpoints.py    # FastAPI endpoint tests
├── test_streamlit_ui.py     # Streamlit UI tests
├── test_helpers.py          # Utility functions
├── README.md                # Detailed documentation
└── INTEGRATION_GUIDE.md     # This file
```

### Fixtures Overview

**Session-scoped fixtures** (shared across all tests):
- `test_db_path`: Temporary database file path
- `test_audio_dir`: Temporary audio directory
- `test_env_vars`: Environment variables for test servers
- `fastapi_server`: Running FastAPI server (port 8888)
- `streamlit_server`: Running Streamlit server (port 8889)
- `browser`: Playwright browser instance
- `event_loop`: Async event loop

**Function-scoped fixtures** (created per test):
- `api_client`: HTTP client for API requests
- `page`: Playwright page for UI interactions
- `browser_context`: Browser context for isolation
- `sample_audio_file`: Sample WAV file for testing

## Test Coverage Summary

### API Tests (test_api_endpoints.py)

✅ **Health Endpoint** (1 test)
- Health check validation

✅ **Call Creation** (5 tests)
- Create with all fields
- Create with minimal fields
- Validation for missing fields
- Invalid datetime handling
- Empty participants handling

✅ **Call Listing** (3 tests)
- Empty list
- Multiple calls
- Status filtering

✅ **Call Details** (3 tests)
- Get existing call
- Get non-existent call (404)
- Get with transcript and analysis

✅ **Transcription** (3 tests)
- Successful transcription
- Non-existent call handling
- Re-transcription handling

✅ **Analysis** (3 tests)
- Successful analysis
- Missing transcription handling
- Non-existent call handling

✅ **CRM Sync** (3 tests)
- Successful sync
- Missing analysis handling
- Multiple syncs

✅ **Pipeline Processing** (2 tests)
- Full pipeline execution
- Non-existent call handling

✅ **E2E Workflows** (2 tests)
- Manual step-by-step workflow
- Multiple calls processing

**Total: 25 API tests**

### UI Tests (test_streamlit_ui.py)

✅ **Dashboard Loading** (2 tests)
- Dashboard loads
- Metrics display

✅ **Call Upload** (3 tests)
- Upload with all fields
- Validation
- Minimal fields

✅ **Call Listing** (2 tests)
- Empty list
- Display calls

✅ **Call Filtering** (2 tests)
- Status filter
- Search functionality

✅ **Call Actions** (4 tests)
- Transcribe action
- Analyze action
- Sync CRM action
- Process All action

✅ **Call Details** (3 tests)
- Transcript tab
- Analysis tab
- CRM notes/tasks tabs

✅ **Refresh** (1 test)
- Refresh functionality

**Total: 17 UI tests**

**Grand Total: 42 E2E tests**

## Test Execution Flow

### API Tests
1. FastAPI server starts on port 8888
2. Tests make HTTP requests to the server
3. Server uses temporary database and audio directory
4. Tests verify responses and state changes

### UI Tests
1. FastAPI server starts on port 8888
2. Streamlit server starts on port 8889
3. Tests use Playwright to interact with Streamlit UI
4. Tests may use API client to set up test data
5. Tests verify UI elements and interactions

## Best Practices

### Writing New Tests

1. **Use descriptive names**: `test_create_call_with_all_fields`
2. **Include docstrings**: Document Test Case, Description, Expected
3. **Use markers**: Add `@pytest.mark.e2e` and appropriate markers
4. **Keep tests isolated**: Each test should be independent
5. **Use fixtures**: Leverage existing fixtures for setup

### Example Test

```python
@pytest.mark.asyncio
async def test_example_feature(self, api_client: AsyncClient, sample_audio_file: Path):
    """
    Test Case: Example Feature Test
    Description: Verify that the example feature works correctly
    Expected: Returns success response with expected data
    """
    # Arrange
    # ... setup code ...
    
    # Act
    response = await api_client.get("/example")
    
    # Assert
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
```

## Troubleshooting

### Common Issues

1. **Ports in use**: Change ports in fixture definitions
2. **Server startup timeout**: Increase retry counts
3. **Browser not found**: Run `playwright install`
4. **Database locked**: Check for concurrent test execution

### Debug Mode

```bash
# Run with debug output
pytest tests/e2e/ -v -s

# Run specific test with pdb
pytest tests/e2e/test_api_endpoints.py::TestCallCreation::test_create_call_with_all_fields --pdb

# Run UI tests with headed browser
# Edit conftest.py: browser = await p.chromium.launch(headless=False)
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          playwright install chromium
      - name: Run E2E tests
        run: pytest tests/e2e/ -v
      - name: Upload screenshots
        if: failure()
        uses: actions/upload-artifact@v3
        with:
          name: test-screenshots
          path: test-results/
```

## Performance Considerations

- API tests: Fast (~2-3 seconds per test)
- UI tests: Slower (~5-10 seconds per test due to browser startup)
- Server startup: ~2-5 seconds one-time cost
- Total suite time: ~5-10 minutes for all 42 tests

## Future Enhancements

- [ ] Parallel test execution
- [ ] Visual regression testing
- [ ] Performance benchmarks
- [ ] Accessibility testing
- [ ] Mobile viewport testing
- [ ] Screenshot comparison

