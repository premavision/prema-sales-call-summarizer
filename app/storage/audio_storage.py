import os
from pathlib import Path
from typing import BinaryIO

from fastapi import HTTPException

from app.core.config import get_settings

settings = get_settings()


def ensure_audio_dir() -> Path:
    path = Path(settings.audio_dir).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def validate_filename(filename: str) -> str:
    """Validate and sanitize filename to prevent path traversal attacks."""
    # Remove any path components
    safe_filename = os.path.basename(filename)
    # Remove any remaining path separators
    safe_filename = safe_filename.replace("/", "").replace("\\", "")
    if not safe_filename or safe_filename in (".", ".."):
        raise HTTPException(status_code=400, detail="Invalid filename")
    return safe_filename


def save_audio_file(filename: str, file_obj: BinaryIO, max_size_mb: int | None = None) -> str:
    """
    Save uploaded audio file with security validations.
    
    Args:
        filename: Original filename
        file_obj: File object to read from
        max_size_mb: Maximum file size in MB (from settings if None)
    
    Returns:
        Path to saved file
    
    Raises:
        HTTPException: If file is too large or filename is invalid
    """
    # Validate filename to prevent path traversal
    safe_filename = validate_filename(filename)
    
    # Get max size from settings if not provided
    if max_size_mb is None:
        max_size_mb = settings.max_upload_size_mb
    
    max_size_bytes = max_size_mb * 1024 * 1024
    
    base_dir = ensure_audio_dir()
    target = base_dir / safe_filename
    
    # Ensure target is within base_dir (prevent path traversal)
    try:
        target.resolve().relative_to(base_dir.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid file path")
    
    # Write file with size limit
    total_size = 0
    with open(target, "wb") as out_file:
        while True:
            chunk = file_obj.read(1024 * 1024)  # 1MB chunks
            if not chunk:
                break
            total_size += len(chunk)
            if total_size > max_size_bytes:
                # Clean up partial file
                target.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large. Maximum size is {max_size_mb}MB"
                )
            out_file.write(chunk)
    
    return str(target)
