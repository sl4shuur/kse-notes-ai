"""High-level note creation orchestration."""

from collections.abc import Sequence

from notes_ai.ingestion.router import extract_content
from notes_ai.interfaces.extractor import TextExtractor
from notes_ai.interfaces.generator import NoteGenerationService
from notes_ai.interfaces.storage import NoteStore
from notes_ai.models import Note, Source


async def create_note(
    source: Source,
    extractors: Sequence[TextExtractor],
    generator: NoteGenerationService,
    store: NoteStore,
) -> Note:
    """Extract, generate, and persist a note."""
    content = await extract_content(source, extractors)
    note = await generator.generate(source, content)
    await store.save(note)
    return note
