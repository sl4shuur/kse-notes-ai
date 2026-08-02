from typing import Protocol
from notes_ai.models import Source, ExtractedContent, Note
class LLMClient(Protocol):
    async def complete(self, user_prompt: str, system_prompt:str) -> Note: ...