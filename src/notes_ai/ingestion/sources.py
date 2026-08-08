"""Create validated sources from user-provided locations."""

from notes_ai.ingestion.detection import detect_source_type
from notes_ai.ingestion.metadata import extract_source_metadata
from notes_ai.loggers import CustomLogger
from notes_ai.models import Source


def create_source(
    location: str,
    logger: CustomLogger,
    *,
    title: str | None = None,
) -> Source:
    source_type = detect_source_type(location, logger)
    metadata = extract_source_metadata(location, source_type)

    if metadata.error:
        logger.warning("Could not extract source metadata: %s", metadata.error)

    return Source(
        input_type=source_type,
        location=location,
        title=title or metadata.title,
        metadata=metadata,
    )
