import json
import logging
from pathlib import Path
from uuid import uuid4

from notes_ai.interfaces.storage import NoteStore
from notes_ai.models import Note

logger = logging.getLogger(__name__)



class JsonNoteStore(NoteStore):
    """Saves the Note and all its metadata as a JSON file."""

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.tags_path = self.base_dir.parents[0] / "tags.json"
        if not self.tags_path.exists():  
            self.tags_path.write_text(json.dumps({}))

    async def save(self, note: Note) -> str:
        base_id = note.title
        note_id = base_id
        counter = 1
        while (self.base_dir / f"{note_id}.json").exists():
            note_id = f"{base_id}_{counter}"
            counter += 1

        file_path = self.base_dir / f"{note_id}.json"
        
        json_data = note.model_dump_json(indent=2)
        json_data = json.loads(json_data)
        json_data["title"] = note_id
        json_data["tags"] = []
        json_data = json.dumps(json_data, indent=2)
        file_path.write_text(json_data, encoding="utf-8")
        logger.info("Saved note to %s", file_path)
        return note_id
