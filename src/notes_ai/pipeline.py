
from notes_ai.interfaces.extractor import TextExtractor
from notes_ai.interfaces.storage import NoteStore
from notes_ai.interfaces.llm import LLMClient
from notes_ai.models import Source, Note

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
    note = await generate_note(content, llm)
    await store.save(note)

    return note