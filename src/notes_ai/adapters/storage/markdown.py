from pathlib import Path

from notes_ai.interfaces import NoteStore
from notes_ai.models import Note


class MarkdownNoteStore(NoteStore):
    """Saves a note to a markdown file."""

    def __init__(self, output_dir: str | Path = "output"):
        self.output_dir = Path(output_dir)

    async def save(self, note: Note) -> str:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        base_title = note.title
        title = base_title
        counter = 1
        while (self.output_dir / f"{title}.md").exists():
            title = f"{base_title}_{counter}"
            counter += 1
            
        filepath = self.output_dir / f"{title}.md"
        filepath.write_text(note.content, encoding="utf-8")
        return title
