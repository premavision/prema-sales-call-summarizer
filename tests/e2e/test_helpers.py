"""
Helper utilities for E2E tests

Provides utility functions for common test operations like creating test calls,
waiting for UI elements, and other shared functionality.
"""
from datetime import datetime
from pathlib import Path
from typing import Optional

from httpx import AsyncClient


async def create_test_call(
    client: AsyncClient,
    audio_file: Path,
    title: str = "Test Call",
    contact_name: Optional[str] = None,
    company: Optional[str] = None,
    call_type: Optional[str] = None,
    crm_deal_id: Optional[str] = None,
    participants: Optional[str] = None,
) -> dict:
    """
    Helper function to create a test call via API
    
    Args:
        client: HTTP client for API requests
        audio_file: Path to audio file
        title: Call title
        contact_name: Optional contact name
        company: Optional company name
        call_type: Optional call type
        crm_deal_id: Optional CRM deal ID
        participants: Optional comma-separated participants
    
    Returns:
        Created call data as dict
    """
    recorded_at = datetime.utcnow().isoformat()
    
    data = {
        "title": title,
        "recorded_at": recorded_at,
    }
    
    if contact_name:
        data["contact_name"] = contact_name
    if company:
        data["company"] = company
    if call_type:
        data["call_type"] = call_type
    if crm_deal_id:
        data["crm_deal_id"] = crm_deal_id
    if participants:
        data["participants"] = participants
    
    with open(audio_file, "rb") as f:
        response = await client.post(
            "/calls",
            data=data,
            files={"audio_file": ("sample.wav", f, "audio/wav")}
        )
        response.raise_for_status()
        return response.json()


async def process_call_pipeline(client: AsyncClient, call_id: int) -> None:
    """
    Helper function to process a call through the full pipeline
    
    Args:
        client: HTTP client for API requests
        call_id: ID of the call to process
    """
    await client.post(f"/calls/{call_id}/transcribe")
    await client.post(f"/calls/{call_id}/analyze")
    await client.post(f"/calls/{call_id}/sync-crm")


def create_sample_wav_file(path: Path, duration_seconds: float = 1.0) -> Path:
    """
    Create a minimal valid WAV file for testing
    
    Args:
        path: Path where to create the file
        duration_seconds: Duration in seconds (affects file size)
    
    Returns:
        Path to created file
    """
    sample_rate = 44100
    num_channels = 1
    bits_per_sample = 16
    duration_samples = int(sample_rate * duration_seconds)
    data_size = duration_samples * num_channels * (bits_per_sample // 8)
    file_size = 36 + data_size  # Header (36 bytes) + data
    
    # WAV header
    wav_file = bytearray()
    wav_file.extend(b"RIFF")
    wav_file.extend((file_size - 8).to_bytes(4, "little"))  # Chunk size
    wav_file.extend(b"WAVE")
    wav_file.extend(b"fmt ")  # Format chunk
    wav_file.extend((16).to_bytes(4, "little"))  # Format chunk size
    wav_file.extend((1).to_bytes(2, "little"))  # Audio format (PCM)
    wav_file.extend((num_channels).to_bytes(2, "little"))
    wav_file.extend((sample_rate).to_bytes(4, "little"))
    wav_file.extend((sample_rate * num_channels * (bits_per_sample // 8)).to_bytes(4, "little"))  # Byte rate
    wav_file.extend((num_channels * (bits_per_sample // 8)).to_bytes(2, "little"))  # Block align
    wav_file.extend((bits_per_sample).to_bytes(2, "little"))
    wav_file.extend(b"data")
    wav_file.extend((data_size).to_bytes(4, "little"))
    wav_file.extend(b"\x00" * data_size)  # Silent audio data
    
    path.write_bytes(wav_file)
    return path

