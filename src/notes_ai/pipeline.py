
from notes_ai.interfaces.extractor import TextExtractor
from notes_ai.interfaces.storage import NoteStore
from notes_ai.interfaces.llm import LLMClient
from notes_ai.models import Source, Note
from notes_ai.interfaces.exceptions import UnsupportedSourceError
from notes_ai.adapters.extractors.youtube import is_valid_youtube_url
from notes_ai.utils.loggers import CustomLogger
from notes_ai.adapters.llm.final_cleaner import clean_note
from pathlib import Path
from typing import Any
import trafilatura
from yt_dlp import YoutubeDL
import fitz
from PIL import Image
from mutagen import File as AudioFile

AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".opus", ".flac", ".aac"}
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
PDF_EXTENSION = ".pdf"




def _is_url(input_path: str) -> bool:
    """Check if the input string is a URL."""
    return input_path.startswith(("http://", "https://"))

def process_content(input: str, logger: CustomLogger, **kwargs: Any) -> str:
    """
    Identify the input type and process it using the appropriate module.

    Args:
        input_path: URL or file path to process.
        logger: Logger instance.
        **kwargs: Additional arguments passed to specific processors
                  (e.g., chunk_duration, include_metadata).

    Returns:
        str: The extracted text content.

    Raises:
        ValueError: If the input type is unsupported or file does not exist.
    """
    
    # 1. Handle URLs
    if _is_url(input):
        if is_valid_youtube_url(input):
            logger.debug("Detected source: YouTube Video")
            return "youtube"
        else:
            logger.debug("Detected source: Web Article")
            include_metadata = kwargs.get("include_metadata", False)
            return "web"

    # 2. Handle Local Files
    path = Path(input)
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {input}")

    suffix = path.suffix.lower()

    if suffix == PDF_EXTENSION:
        logger.debug("Detected source: PDF Document")
        return "pdf"
        

    elif suffix in IMAGE_EXTENSIONS:
        logger.debug("Detected source: Image")
        return "image"

    elif suffix in AUDIO_EXTENSIONS:
        logger.debug(f"Detected source: Audio File ({suffix})")
        return "audio"

    elif suffix in VIDEO_EXTENSIONS:
        raise NotImplementedError("Video file processing is not yet implemented.")

    else:
        raise ValueError(f"Unsupported file type: {suffix}")




def extract_metadata(location: str, input_type: str) -> dict:
    """
    Extract metadata from a supported source.

    Returns:
        dict containing at least a 'title' key when available.
    """

    try:
        match input_type:

            case "web":
                downloaded = trafilatura.fetch_url(location)
                if not downloaded:
                    return {}

                meta = trafilatura.extract_metadata(downloaded)

                return {
                    "title": meta.title or "",
                    "author": meta.author,
                    "date": meta.date,
                    "description": meta.description,
                    "hostname": meta.hostname,
                    "url": meta.url,
                    "sitename": getattr(meta, "sitename", None),
                }

            case "youtube":
                with YoutubeDL({"quiet": True}) as ydl:
                    info = ydl.extract_info(location, download=False)

                return {
                    "title": info.get("title"),
                    "author": info.get("uploader"),
                    "channel": info.get("channel"),
                    "duration": info.get("duration"),
                    "upload_date": info.get("upload_date"),
                    "description": info.get("description"),
                    "view_count": info.get("view_count"),
                    "url": location,
                }

            case "pdf":
                doc = fitz.open(location)

                meta = doc.metadata or {}

                return {
                    "title": meta.get("title") or Path(location).stem,
                    "author": meta.get("author"),
                    "subject": meta.get("subject"),
                    "keywords": meta.get("keywords"),
                    "creator": meta.get("creator"),
                    "producer": meta.get("producer"),
                    "creation_date": meta.get("creationDate"),
                    "modification_date": meta.get("modDate"),
                    "pages": doc.page_count,
    }

            case "image":
                img = Image.open(location)

                return {
                    "title": Path(location).stem,
                    "format": img.format,
                    "mode": img.mode,
                    "width": img.width,
                    "height": img.height,
                    "exif": dict(img.getexif()),
                }

            case "audio":
                audio = AudioFile(location)

                metadata = {
                    "title": Path(location).stem,
                }

                if audio:
                    metadata.update({
                        "duration": getattr(audio.info, "length", None),
                        "bitrate": getattr(audio.info, "bitrate", None),
                        "sample_rate": getattr(audio.info, "sample_rate", None),
                    })

                    if audio.tags:
                        metadata["tags"] = {
                            str(k): str(v)
                            for k, v in audio.tags.items()
                        }

                return metadata

            case _:
                return {
                    "title": Path(location).stem
                }

    except Exception as e:
        return {
            "title": Path(location).stem,
            "error": str(e),
        }

def create_source(location: str, logger: CustomLogger) -> Source:
    input_type = process_content(location, logger)

    metadata = extract_metadata(location, input_type)
    title = metadata["title"]
    return Source(
        input_type=input_type,
        location=location,
        title=title,
        metadata=metadata,
    )



async def create_note(
    source: Source,
    extractors: list[TextExtractor],
    llm: LLMClient,
    store: NoteStore,
    enrich = False,
    color_markup = False,

) -> Note:
    extractor = next(
        (item for item in extractors if item.supports(source)),
        None,
    )

    if extractor is None:
        raise UnsupportedSourceError(source.location)

    content = await extractor.extract(source)
    note = await llm.generate(content)
    cleaned_note =  clean_note(note)
    await store.save(cleaned_note)

    return note