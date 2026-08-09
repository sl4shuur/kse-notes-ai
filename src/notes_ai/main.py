"""Application composition and note-generation workflow."""

import asyncio
import logging
from collections.abc import Sequence
from pathlib import Path

from notes_ai.adapters.extractors.audio import AudioExtractor
from notes_ai.adapters.extractors.image import ImageExtractor
from notes_ai.adapters.extractors.pdf import PDFExtractor
from notes_ai.adapters.extractors.web import WebExtractor
from notes_ai.adapters.extractors.youtube import YouTubeExtractor
from notes_ai.adapters.llm.groq import GroqLLMClient
from notes_ai.adapters.llm_services.note_generator import NoteGenerator
from notes_ai.adapters.storage.markdown import MarkdownNoteStore
from notes_ai.config import get_config
from notes_ai.ingestion import create_source
from notes_ai.interfaces.exceptions import ConfigurationError
from notes_ai.loggers import CustomLogger
from notes_ai.models import Note
from notes_ai.pipeline import create_note


def _note_title(
    source_path: str,
    index: int,
    source_count: int,
    custom_name: str | None,
) -> str:
    if custom_name and source_count == 1:
        return custom_name
    if source_path.startswith(("http://", "https://")):
        return f"note_{index}"
    return Path(source_path).stem


async def generate_notes(
    sources: Sequence[str],
    *,
    output_dir: str | Path = "output",
    name: str | None = None,
    verbose: bool = False,
) -> list[Note]:
    """Generate notes for sources using the configured application adapters."""
    config = get_config()
    logger = CustomLogger(config.app_name)
    if verbose:
        logger.setLevel(logging.DEBUG)

    if not config.groq_api_key:
        raise ConfigurationError("GROQ_API_KEY is not set. Add it to the environment or .env file.")

    llm = GroqLLMClient(api_key=config.groq_api_key)
    generator = NoteGenerator(llm, logger)
    store = MarkdownNoteStore(output_dir=output_dir)
    extractors = [
        YouTubeExtractor(logger=logger, temp_audio_dir=config.temp_audio_dir),
        WebExtractor(logger=logger),
        PDFExtractor(logger=logger),
        ImageExtractor(llm=llm, logger=logger),
        AudioExtractor(logger=logger),
    ]

    generated_notes: list[Note] = []
    source_count = len(sources)

    for index, source_path in enumerate(sources, start=1):
        logger.info("[%s/%s] Processing source: %s", index, source_count, source_path)
        title = _note_title(source_path, index, source_count, name)

        try:
            source = create_source(source_path, logger, title=title)
            logger.info("Source detected: %s", source.input_type.value)
        except Exception as error:
            logger.error("Unsupported source or file not found (%s): %s", source_path, error)
            continue

        try:
            note = await create_note(
                source=source,
                extractors=extractors,
                generator=generator,
                store=store,
            )
        except Exception as error:
            logger.error("Failed to create note for %s: %s", source_path, error)
            continue

        generated_notes.append(note)
        logger.success("Successfully generated note: %s/%s.md", output_dir, note.title)

    return generated_notes


def run(
    sources: Sequence[str],
    *,
    output_dir: str | Path = "output",
    name: str | None = None,
    verbose: bool = False,
) -> list[Note]:
    """Run the asynchronous application workflow from synchronous callers."""
    return asyncio.run(
        generate_notes(
            sources,
            output_dir=output_dir,
            name=name,
            verbose=verbose,
        )
    )
