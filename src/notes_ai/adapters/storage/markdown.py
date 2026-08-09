from pathlib import Path

from notes_ai.interfaces.storage import NoteStore
from notes_ai.models import Note


class MarkdownNoteStore(NoteStore):
    """Saves a note to a markdown file."""

    def __init__(self, output_dir: str | Path = "output"):
        self.output_dir = Path(output_dir)

    async def save(self, note: Note) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        filepath = self.output_dir / f"{note.title}.md"
        filepath.write_text(note.content, encoding="utf-8")
