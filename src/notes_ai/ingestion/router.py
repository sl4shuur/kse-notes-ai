"""Select and invoke content extractors."""

from collections.abc import Sequence

from notes_ai.interfaces import TextExtractor, UnsupportedSourceError
from notes_ai.models import ExtractedContent, Source


def select_extractor(
    source: Source,
    extractors: Sequence[TextExtractor],
) -> TextExtractor:
    extractor = next((item for item in extractors if item.supports(source)), None)
    if extractor is None:
        raise UnsupportedSourceError(source.location)
    return extractor


async def extract_content(
    source: Source,
    extractors: Sequence[TextExtractor],
) -> ExtractedContent:
    return await select_extractor(source, extractors).extract(source)
