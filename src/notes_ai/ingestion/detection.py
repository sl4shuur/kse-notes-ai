"""Detect supported source types from URLs and local paths."""

import re
from pathlib import Path

from notes_ai.loggers import CustomLogger
from notes_ai.models import SourceType

AUDIO_EXTENSIONS = frozenset({".mp3", ".wav", ".m4a", ".opus", ".flac", ".aac"})
VIDEO_EXTENSIONS = frozenset({".mp4", ".mkv", ".avi", ".mov", ".webm"})
IMAGE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".bmp", ".webp"})
YOUTUBE_URL_PATTERN = re.compile(
    r"^(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+$",
    re.IGNORECASE,
)


def _is_url(location: str) -> bool:
    return location.startswith(("http://", "https://"))


def is_valid_youtube_url(location: str) -> bool:
    return YOUTUBE_URL_PATTERN.match(location) is not None


def detect_source_type(location: str, logger: CustomLogger) -> SourceType:
    """Return the validated source type for a URL or local file."""
    if _is_url(location):
        source_type = (
            SourceType.YOUTUBE if is_valid_youtube_url(location) else SourceType.WEB
        )
        logger.debug("Detected source type: %s", source_type.value)
        return source_type

    path = Path(location)
    if not path.is_file():
        raise FileNotFoundError(f"Input file not found: {location}")

    suffix = path.suffix.lower()
    if suffix == ".pdf":
        source_type = SourceType.PDF
    elif suffix in IMAGE_EXTENSIONS:
        source_type = SourceType.IMAGE
    elif suffix in AUDIO_EXTENSIONS:
        source_type = SourceType.AUDIO
    elif suffix in VIDEO_EXTENSIONS:
        raise NotImplementedError("Video file processing is not yet implemented.")
    else:
        raise ValueError(f"Unsupported file type: {suffix or '<none>'}")

    logger.debug("Detected source type: %s", source_type.value)
    return source_type
