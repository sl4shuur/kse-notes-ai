
from notes_ai.interfaces.extractor import TextExtractor
from notes_ai.interfaces.storage import NoteStore
from notes_ai.interfaces.llm import LLMClient
from notes_ai.models import Source, Note
from notes_ai.interfaces.exceptions import UnsupportedSourceError
from notes_ai.adapters.extractors.youtube import is_valid_youtube_url
from notes_ai.utils.loggers import CustomLogger
from pathlib import Path
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






def create_source(location):
    input_type = process_content(location)
    metadata = {}
    title = ""
    return Source(input_type, location, title, metadata)



async def create_note(
    source: Source,
    extractors: list[TextExtractor],
    llm: LLMClient,
    store: NoteStore,
) -> Note:
    extractor = next(
        (item for item in extractors if item.supports(source)),
        None,
    )

    if extractor is None:
        raise UnsupportedSourceError(source.location)

    content = await extractor.extract(source)
    note = await llm.generate(content)
    await store.save(note)

    return note