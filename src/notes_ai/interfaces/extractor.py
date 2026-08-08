"""Contract implemented by content extractors."""

from typing import Protocol

from notes_ai.models import ExtractedContent, Source


class TextExtractor(Protocol):
    def supports(self, source: Source) -> bool: ...

    async def extract(self, source: Source) -> ExtractedContent: ...
