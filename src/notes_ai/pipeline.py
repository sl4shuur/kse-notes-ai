"""High-level note creation orchestration."""

from collections.abc import Sequence
from notes_ai.interfaces import NoteGenerationService, NoteStore, TextExtractor
from notes_ai.models import Note, Source
from notes_ai.synthesis import ExtractionStep, GenerationStep, NoteContext, PersistenceStep, SequentialSynthesisPipeline


async def create_note(
    source: Source,
    extractors: Sequence[TextExtractor],
    generator: NoteGenerationService,
    store: NoteStore,
) -> Note:
    """Extract, generate, and persist a note."""
    from pathlib import Path

    from notes_ai.adapters.storage.json_store import JsonNoteStore
    
    pipeline = SequentialSynthesisPipeline([
        ExtractionStep(extractors),
        GenerationStep(generator),
        PersistenceStep(store),
        PersistenceStep(JsonNoteStore(base_dir=Path("data/note_data"))),
    ])
    ctx = await pipeline.run(NoteContext(source=source))
    assert ctx.note is not None
    return ctx.note

