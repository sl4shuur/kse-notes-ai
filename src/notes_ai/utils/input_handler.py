from pathlib import Path
from typing import Any

# Import processors
from notes_ai.unsorted.yt_processing.yt_video2text import generate_yt_transcript, is_valid_youtube_url
from notes_ai.unsorted.web_processing.web2text import fetch_article_text
from notes_ai.unsorted.doc_processing.pdf2text import single_pdf2text
from notes_ai.unsorted.image_processing.img2text import single_img2text
from notes_ai.unsorted.audio_processing.speech2text import transcribe_with_groq
from notes_ai.utils.logging_config import CustomLogger

# Supported extensions
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".opus", ".flac", ".aac"}
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
PDF_EXTENSION = ".pdf"


def _is_url(input_path: str) -> bool:
    """Check if the input string is a URL."""
    return input_path.startswith(("http://", "https://"))


async def process_content(input: str, logger: CustomLogger, **kwargs: Any) -> str:
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
            # Extract specific kwargs for YouTube
            chunk_duration = kwargs.get("chunk_duration", 60 * 15)  # default 15 minutes
            return generate_yt_transcript(
                input, 
                chunk_duration_ms=chunk_duration * 1000, 
                logger=logger
            )
        else:
            logger.debug("Detected source: Web Article")
            include_metadata = kwargs.get("include_metadata", False)
            return fetch_article_text(
                input, 
                logger=logger, 
                include_metadata=include_metadata
            )

    # 2. Handle Local Files
    path = Path(input)
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {input}")

    suffix = path.suffix.lower()

    if suffix == PDF_EXTENSION:
        logger.debug("Detected source: PDF Document")
        output_format = kwargs.get("output_format", "text")
        try:
            return single_pdf2text(path, logger=logger, output_format=output_format)
        except Exception as e:
            return single_pdf2text(path, logger=logger)
        

    elif suffix in IMAGE_EXTENSIONS:
        logger.debug("Detected source: Image")
        return single_img2text(path, logger=logger)

    elif suffix in AUDIO_EXTENSIONS:
        logger.debug(f"Detected source: Audio File ({suffix})")
        return transcribe_with_groq(path, logger=logger)

    elif suffix in VIDEO_EXTENSIONS:
        raise NotImplementedError("Video file processing is not yet implemented.")

    else:
        raise ValueError(f"Unsupported file type: {suffix}")
