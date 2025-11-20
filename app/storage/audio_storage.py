from pathlib import Path
from typing import BinaryIO

from app.core.config import get_settings

settings = get_settings()


def ensure_audio_dir() -> Path:
    path = Path(settings.audio_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_audio_file(filename: str, file_obj: BinaryIO) -> str:
    base_dir = ensure_audio_dir()
    target = base_dir / filename
    with open(target, "wb") as out_file:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            out_file.write(chunk)
    return str(target)
