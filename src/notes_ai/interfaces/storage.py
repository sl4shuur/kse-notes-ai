from typing import Protocol
from notes_ai.models import Note

class NoteStore(Protocol):
    async def save(self, note: Note) -> None: ...