"""Source discovery and routing helpers."""

from .detection import detect_source_type, is_valid_youtube_url
from .metadata import extract_source_metadata
from .router import extract_content, select_extractor
from .sources import create_source

__all__ = [
    "create_source",
    "detect_source_type",
    "extract_content",
    "extract_source_metadata",
    "is_valid_youtube_url",
    "select_extractor",
]
