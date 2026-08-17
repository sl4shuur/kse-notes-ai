import logging
from collections.abc import Sequence
from typing import Protocol

from notes_ai.ingestion import extract_content
from notes_ai.interfaces import NoteGenerationService, NoteStore, TextExtractor
from notes_ai.models import ExtractedContent, Note, Source

logger = logging.getLogger(__name__)


class NoteContext:

    def __init__(self, source: Source) -> None:
        self.source = source
        self.content: ExtractedContent | None = None
        self.note: Note | None = None


class SynthesisStep(Protocol):

    name: str

    async def run(self, context: NoteContext) -> NoteContext: ...


class ExtractionStep:
    name = "extraction"

    def __init__(self, extractors: Sequence[TextExtractor]) -> None:
        self.extractors = extractors

    async def run(self, context: NoteContext) -> NoteContext:
        context.content = await extract_content(context.source, self.extractors)
        return context


class GenerationStep:
    name = "generation"

    def __init__(self, generator: NoteGenerationService) -> None:
        self.generator = generator

    async def run(self, context: NoteContext) -> NoteContext:
        if context.content is None:
            raise RuntimeError("ExtractionStep must run before GenerationStep")
        context.note = await self.generator.generate(context.source, context.content)
        return context


class PersistenceStep:
    name = "persistence"

    def __init__(self, store: NoteStore) -> None:
        self.store = store

    async def run(self, context: NoteContext) -> NoteContext:
        if context.note is None:
            raise RuntimeError("GenerationStep must run before PersistenceStep")
        await self.store.save(context.note)
        return context


class SequentialSynthesisPipeline:

    def __init__(self, steps: Sequence[SynthesisStep]) -> None:
        self.steps = list(steps)

    async def run(self, context: NoteContext) -> NoteContext:
        total = len(self.steps)
        for index, step in enumerate(self.steps, 1):
            logger.info("[%d/%d] Running step: %s", index, total, step.name)
            context = await step.run(context)
            logger.info("[%d/%d] Completed step: %s", index, total, step.name)
        return context
