"""Extract provider-specific metadata into validated domain models."""

from pathlib import Path
from urllib.parse import unquote, urlparse

import fitz
import trafilatura
from mutagen import File as AudioFile
from PIL import Image
from yt_dlp import YoutubeDL

from notes_ai.models import (
    AudioMetadata,
    AudioTag,
    ImageMetadata,
    PdfMetadata,
    SourceMetadata,
    SourceType,
    WebMetadata,
    YouTubeMetadata,
)


def _fallback_title(location: str) -> str:
    parsed = urlparse(location)
    if parsed.scheme and parsed.netloc:
        path_title = Path(unquote(parsed.path)).stem
        return path_title or parsed.hostname or "Untitled"
    return Path(location).stem or "Untitled"


def _extract_youtube_metadata(location: str) -> YouTubeMetadata:
    with YoutubeDL({"quiet": True}) as downloader:
        info = downloader.extract_info(location, download=False)

    return YouTubeMetadata(
        title=info.get("title") or _fallback_title(location),
        author=info.get("uploader"),
        channel=info.get("channel"),
        duration_seconds=info.get("duration"),
        upload_date=info.get("upload_date"),
        description=info.get("description"),
        view_count=info.get("view_count"),
        url=location,
    )


def _extract_web_metadata(location: str) -> WebMetadata:
    downloaded = trafilatura.fetch_url(location)
    if not downloaded:
        raise ValueError("Web page could not be downloaded")

    metadata = trafilatura.extract_metadata(downloaded)
    return WebMetadata(
        title=metadata.title or _fallback_title(location),
        author=metadata.author,
        published_date=metadata.date,
        description=metadata.description,
        hostname=metadata.hostname,
        url=metadata.url or location,
        site_name=getattr(metadata, "sitename", None),
    )


def _extract_pdf_metadata(location: str) -> PdfMetadata:
    with fitz.open(location) as document:
        metadata = getattr(document, "metadata", None) or {}
        return PdfMetadata(
            title=metadata.get("title") or _fallback_title(location),
            author=metadata.get("author"),
            subject=metadata.get("subject"),
            keywords=metadata.get("keywords"),
            creator=metadata.get("creator"),
            producer=metadata.get("producer"),
            creation_date=metadata.get("creationDate"),
            modification_date=metadata.get("modDate"),
            page_count=document.page_count,
        )


def _extract_image_metadata(location: str) -> ImageMetadata:
    with Image.open(location) as image:
        return ImageMetadata(
            title=_fallback_title(location),
            image_format=image.format,
            color_mode=image.mode,
            width=image.width,
            height=image.height,
        )


def _extract_audio_metadata(location: str) -> AudioMetadata:
    audio = AudioFile(location)
    if audio is None:
        return AudioMetadata(title=_fallback_title(location))

    tags = tuple(
        AudioTag(name=str(name), value=str(value))
        for name, value in (audio.tags or {}).items()
    )
    return AudioMetadata(
        title=_fallback_title(location),
        duration_seconds=getattr(audio.info, "length", None),
        bitrate=getattr(audio.info, "bitrate", None),
        sample_rate=getattr(audio.info, "sample_rate", None),
        tags=tags,
    )


def _fallback_metadata(
    location: str,
    source_type: SourceType,
    error: Exception,
) -> SourceMetadata:
    title = _fallback_title(location)
    message = str(error)

    match source_type:
        case SourceType.YOUTUBE:
            return YouTubeMetadata(title=title, url=location, error=message)
        case SourceType.WEB:
            return WebMetadata(title=title, url=location, error=message)
        case SourceType.PDF:
            return PdfMetadata(title=title, error=message)
        case SourceType.IMAGE:
            return ImageMetadata(title=title, error=message)
        case SourceType.AUDIO:
            return AudioMetadata(title=title, error=message)


def extract_source_metadata(
    location: str,
    source_type: SourceType,
) -> SourceMetadata:
    """Extract typed metadata, preserving a typed fallback on provider errors."""
    try:
        match source_type:
            case SourceType.YOUTUBE:
                return _extract_youtube_metadata(location)
            case SourceType.WEB:
                return _extract_web_metadata(location)
            case SourceType.PDF:
                return _extract_pdf_metadata(location)
            case SourceType.IMAGE:
                return _extract_image_metadata(location)
            case SourceType.AUDIO:
                return _extract_audio_metadata(location)
    except Exception as error:
        return _fallback_metadata(location, source_type, error)
