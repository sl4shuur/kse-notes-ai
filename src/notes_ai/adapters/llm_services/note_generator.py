"""Generate a complete, color-annotated study note in one LLM call."""

from notes_ai.interfaces import LLMClient
from notes_ai.loggers import CustomLogger
from notes_ai.models import ExtractedContent, Note, NoteMetadata, Source
from notes_ai.prompts import (
    NOTE_GENERATION_SYSTEM_PROMPT,
    NOTE_GENERATION_USER_PROMPT_TEMPLATE,
)

from .final_cleaner import clean_note

SYSTEM_PROMPT = NOTE_GENERATION_SYSTEM_PROMPT
USER_PROMPT_TEMPLATE = NOTE_GENERATION_USER_PROMPT_TEMPLATE


class NoteGenerator:
    """Single agent responsible for the complete generated note."""

    def __init__(
        self,
        llm: LLMClient,
        logger: CustomLogger,
        note_focus: str | None = None,
    ):
        self.llm = llm
        self.logger = logger
        self.note_focus = note_focus

    async def generate(
        self,
        source: Source,
        content: ExtractedContent,
        *,
        user_prompt: str = USER_PROMPT_TEMPLATE,
        system_prompt: str = SYSTEM_PROMPT,
    ) -> Note:
        prompt = user_prompt.format(content=content.text)
        if self.note_focus:
            prompt += f"\n\nGive special attention to this focus: {self.note_focus}"
        generated_markdown = str(
            await self.llm.complete(
                user_prompt=prompt,
                system_prompt=system_prompt,
            )
        ).strip()
        cleaned_markdown = clean_note(generated_markdown)

        self.logger.debug("Generated complete study note in one LLM pass.")
        return Note(
            title=source.title,
            content=cleaned_markdown,
            source=source,
            metadata=NoteMetadata(
                extraction=content.metadata,
                model=getattr(self.llm, "model", "unknown"),
            ),
        )
