"""
E2E Test Fixtures and Configuration

This module provides fixtures for end-to-end testing including:
- FastAPI test server instance
- Streamlit test server instance
- Test database and file system setup
- Browser instance management
- Sample audio file generation
"""
import asyncio
import multiprocessing
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Generator

import pytest
from playwright.async_api import Browser, BrowserContext, Page, async_playwright
from sqlmodel import create_engine, SQLModel
from httpx import AsyncClient

from app.models import Call, Transcript, CallAnalysis, CRMNote, CRMTask, CRMSyncLog  # noqa: F401


@pytest.fixture(scope="session")
def test_db_path(tmp_path_factory) -> str:
    """Create a temporary database file for e2e tests"""
    db_dir = tmp_path_factory.mktemp("e2e_db")
    db_path = db_dir / "test.db"
    # Ensure directory exists and is writable
    db_dir.mkdir(parents=True, exist_ok=True)
    return str(db_path)


@pytest.fixture(scope="session")
def test_audio_dir(tmp_path_factory) -> str:
    """Create a temporary audio directory for e2e tests"""
    audio_dir = tmp_path_factory.mktemp("e2e_audio")
    return str(audio_dir)


@pytest.fixture(scope="session")
def test_env_vars(test_db_path: str, test_audio_dir: str) -> dict[str, str]:
    """Create environment variables for testing"""
    # Use absolute path for SQLite
    abs_db_path = os.path.abspath(test_db_path)
    abs_audio_dir = os.path.abspath(test_audio_dir)
    return {
        "DATABASE_URL": f"sqlite:///{abs_db_path}",
        "AUDIO_DIR": abs_audio_dir,
        "ASR_PROVIDER": "stub",
        "LLM_PROVIDER": "stub",
        "CRM_MODE": "fake",
        "CORS_ORIGINS": "http://localhost:8000,http://localhost:8501,http://localhost:3000",
    }


@pytest.fixture(scope="session")
def fastapi_server_port() -> int:
    """Port for FastAPI test server"""
    return 8888


@pytest.fixture(scope="session")
def streamlit_server_port() -> int:
    """Port for Streamlit test server"""
    return 8889


def _run_fastapi_server(port: int, env_vars: dict[str, str]) -> None:
    """Run FastAPI server in a subprocess"""
    # Set environment variables
    env = os.environ.copy()
    for key, value in env_vars.items():
        env[key] = value
    
    # Import after setting env vars
    import uvicorn
    from app.main import app
    
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="error", env_file=None)


def _run_streamlit_server(port: int, env_vars: dict[str, str]) -> None:
    """Run Streamlit server in a subprocess"""
    # Set environment variables
    env = os.environ.copy()
    for key, value in env_vars.items():
        env[key] = value
    
    # Run streamlit using subprocess
    import sys
    streamlit_cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        "app/ui/streamlit/dashboard.py",
        "--server.port", str(port),
        "--server.headless", "true",
        "--server.runOnSave", "false",
        "--server.enableCORS", "false",
        "--server.enableXsrfProtection", "false",
        "--browser.gatherUsageStats", "false",
        "--logger.level", "error",
    ]
    # Use subprocess.Popen but redirect output to devnull to avoid noise
    with open(os.devnull, 'w') as devnull:
        subprocess.Popen(
            streamlit_cmd,
            env=env,
            stdout=devnull,
            stderr=devnull,
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        )


@pytest.fixture(scope="session")
def fastapi_server(test_env_vars: dict[str, str], fastapi_server_port: int) -> Generator[str, None, None]:
    """Start FastAPI server for testing"""
    # Set environment variables before starting server
    original_env = {}
    for key, value in test_env_vars.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value
    
    process = multiprocessing.Process(
        target=_run_fastapi_server,
        args=(fastapi_server_port, test_env_vars),
        daemon=True
    )
    process.start()
    
    # Wait for server to be ready
    import requests
    max_retries = 30
    server_url = f"http://127.0.0.1:{fastapi_server_port}"
    for i in range(max_retries):
        try:
            response = requests.get(f"{server_url}/health", timeout=1)
            if response.status_code == 200:
                break
        except Exception:
            pass
        time.sleep(0.5)
    else:
        process.terminate()
        process.join(timeout=2)
        raise RuntimeError(f"FastAPI server failed to start on port {fastapi_server_port}")
    
    yield server_url
    
    # Cleanup
    try:
        process.terminate()
        process.join(timeout=5)
        if process.is_alive():
            process.kill()
    except Exception:
        pass
    
    # Restore original environment
    for key, value in original_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


@pytest.fixture(scope="session")
def streamlit_server(test_env_vars: dict[str, str], streamlit_server_port: int) -> Generator[str, None, None]:
    """Start Streamlit server for testing"""
    # Set environment variables before starting server
    original_env = {}
    for key, value in test_env_vars.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value
    
    process = multiprocessing.Process(
        target=_run_streamlit_server,
        args=(streamlit_server_port, test_env_vars),
        daemon=True
    )
    process.start()
    
    # Wait for server to be ready - Streamlit takes longer to start
    import requests
    max_retries = 60
    server_url = f"http://127.0.0.1:{streamlit_server_port}"
    for i in range(max_retries):
        try:
            # Try multiple endpoints Streamlit might use
            try:
                response = requests.get(f"{server_url}/_stcore/health", timeout=2)
                if response.status_code == 200:
                    break
            except Exception:
                pass
            
            # Try main page
            try:
                response = requests.get(server_url, timeout=2)
                if response.status_code == 200:
                    break
            except Exception:
                pass
        except Exception:
            pass
        time.sleep(1)
    else:
        # Check if process is still running
        if process.is_alive():
            try:
                process.terminate()
                process.join(timeout=2)
                if process.is_alive():
                    process.kill()
            except Exception:
                pass
        error_msg = (
            f"Streamlit server failed to start on port {streamlit_server_port}. "
            f"This may be due to missing dependencies (streamlit) or port conflicts."
        )
        raise RuntimeError(error_msg)
    
    yield server_url
    
    # Cleanup
    try:
        process.terminate()
        process.join(timeout=10)
        if process.is_alive():
            process.kill()
    except Exception:
        pass
    
    # Restore original environment
    for key, value in original_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def browser() -> Generator[Browser, None, None]:
    """Create a browser instance for Playwright tests"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        yield browser
        await browser.close()


@pytest.fixture
async def browser_context(browser: Browser) -> Generator[BrowserContext, None, None]:
    """Create a browser context for each test"""
    context = await browser.new_context(
        viewport={"width": 1920, "height": 1080},
        ignore_https_errors=True,
    )
    yield context
    await context.close()


@pytest.fixture
async def page(browser_context: BrowserContext) -> Generator[Page, None, None]:
    """Create a new page for each test"""
    page = await browser_context.new_page()
    yield page
    await page.close()


@pytest.fixture
async def api_client(fastapi_server: str) -> Generator[AsyncClient, None, None]:
    """Create an HTTP client for API testing"""
    async with AsyncClient(base_url=fastapi_server, timeout=30.0) as client:
        yield client


@pytest.fixture
def sample_audio_file(tmp_path):
    """Create a sample audio file for testing (valid WAV file)"""
    audio_file = tmp_path / "sample.wav"
    
    # Create a minimal valid WAV file
    sample_rate = 44100
    num_channels = 1
    bits_per_sample = 16
    duration_samples = int(sample_rate * 1.0)  # 1 second of audio
    data_size = duration_samples * num_channels * (bits_per_sample // 8)
    file_size = 36 + data_size  # Header (36 bytes) + data
    
    # WAV file structure
    wav_data = bytearray()
    # RIFF header
    wav_data.extend(b"RIFF")
    wav_data.extend((file_size - 8).to_bytes(4, "little"))  # Chunk size
    wav_data.extend(b"WAVE")
    # Format chunk
    wav_data.extend(b"fmt ")
    wav_data.extend((16).to_bytes(4, "little"))  # Format chunk size
    wav_data.extend((1).to_bytes(2, "little"))   # Audio format (PCM)
    wav_data.extend((num_channels).to_bytes(2, "little"))
    wav_data.extend((sample_rate).to_bytes(4, "little"))
    wav_data.extend((sample_rate * num_channels * (bits_per_sample // 8)).to_bytes(4, "little"))  # Byte rate
    wav_data.extend((num_channels * (bits_per_sample // 8)).to_bytes(2, "little"))  # Block align
    wav_data.extend((bits_per_sample).to_bytes(2, "little"))
    # Data chunk
    wav_data.extend(b"data")
    wav_data.extend((data_size).to_bytes(4, "little"))
    wav_data.extend(b"\x00" * data_size)  # Silent audio data
    
    audio_file.write_bytes(wav_data)
    return audio_file


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment(test_db_path: str, test_audio_dir: str) -> Generator[None, None, None]:
    """Set up test environment once per session"""
    # Ensure audio directory exists
    os.makedirs(test_audio_dir, exist_ok=True)
    
    # Ensure database directory exists
    db_dir = os.path.dirname(test_db_path)
    os.makedirs(db_dir, exist_ok=True)
    
    # Create database tables if they don't exist
    if not os.path.exists(test_db_path):
        engine = create_engine(f"sqlite:///{test_db_path}", connect_args={"check_same_thread": False})
        SQLModel.metadata.create_all(engine)
        engine.dispose()
    
    yield
    
    # Cleanup after all tests
    try:
        if os.path.exists(test_db_path):
            os.remove(test_db_path)
        if os.path.exists(test_audio_dir):
            shutil.rmtree(test_audio_dir)
    except Exception:
        pass  # Ignore cleanup errors
