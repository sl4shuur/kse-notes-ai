"""LLM-backed application services and note cleanup helpers."""

from .final_cleaner import (
    add_spaces_around_em_dashes,
    clean_heading_colors,
    clean_note,
    escape_underscores_in_textcolor,
    normalize_smart_quotes,
    remove_spammy_underscores,
    trim_spaces_in_math,
    unwrap_backticked_math,
)
from .note_generator import NoteGenerator

__all__ = [
    "NoteGenerator",
    "add_spaces_around_em_dashes",
    "clean_heading_colors",
    "clean_note",
    "escape_underscores_in_textcolor",
    "normalize_smart_quotes",
    "remove_spammy_underscores",
    "trim_spaces_in_math",
    "unwrap_backticked_math",
]
