"""Contract for complete note generation."""

from typing import Protocol

from notes_ai.models import ExtractedContent, Note, Source


class NoteGenerationService(Protocol):
    async def generate(
        self,
        source: Source,
        content: ExtractedContent,
    ) -> Note: ...
