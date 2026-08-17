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
    pipeline = SequentialSynthesisPipeline([
        ExtractionStep(extractors),
        GenerationStep(generator),
        PersistenceStep(store),
    ])
    ctx = await pipeline.run(NoteContext(source=source))
    assert ctx.note is not None
    return ctx.note

