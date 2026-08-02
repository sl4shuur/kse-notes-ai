"""Simple CLI for Notes AI using argparse and the package pipeline."""

import argparse
import asyncio
import os
import sys
from pathlib import Path
import logging
from notes_ai.utils.logging_config import setup_logging
import asyncio
import dotenv

# Load .env from workspace root if present
dotenv.load_dotenv(Path.cwd() / ".env")

if not os.getenv("GROQ_API_KEY"):
    os.environ["GROQ_API_KEY"] = "placeholder_key_for_import"
    _ENV_KEY_WAS_MISSING = True
else:
    _ENV_KEY_WAS_MISSING = False

import notes_ai.utils.config_helper as _config_helper

_orig_find_root = _config_helper.find_project_root


def _patched_find_project_root(start_path=None, **kwargs):
    if start_path is None:
        start_path = Path.cwd()
    return _orig_find_root(start_path=start_path, **kwargs)


_config_helper.find_project_root = _patched_find_project_root

_orig_exists = Path.exists


def _patched_exists(self):
    if self.name == ".env" and not _orig_exists(self):
        return True
    return _orig_exists(self)


Path.exists = _patched_exists

import notes_ai.adapters.extractors.youtube as _yt_module

if not hasattr(_yt_module, "is_valid_youtube_url"):
    setattr(_yt_module, "is_valid_youtube_url", getattr(_yt_module.YouTubeExtractor, "is_valid_youtube_url", None))

from notes_ai.adapters.extractors.audio import AudioExtractor
from notes_ai.adapters.extractors.image import ImageExtractor
from notes_ai.adapters.extractors.pdf import PDFExtractor
from notes_ai.adapters.extractors.web import WebExtractor
from notes_ai.adapters.extractors.youtube import YouTubeExtractor
from notes_ai.adapters.llm.groq import GroqLLMClient
from notes_ai.adapters.storage.markdown import MarkdownNoteStore
from notes_ai.models import Source
from notes_ai.pipeline import create_note, process_content
from notes_ai.utils.loggers import CustomLogger

Path.exists = _orig_exists


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Notes AI — Generate structured study notes from YouTube, web, PDF, image, or audio sources."
    )
    parser.add_argument(
        "sources",
        nargs="+",
        type=str,
        help="One or more URLs or local file paths to process.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=str,
        default="output",
        help="Directory to save the generated markdown note(s) (default: output).",
    )
    parser.add_argument(
        "-n",
        "--name",
        type=str,
        default=None,
        help="Custom title/name for the note (only applicable when processing a single source).",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging.",
    )
    
    args = parser.parse_args()
    logger = setup_logging(
    level=logging.DEBUG,
    logger_class=CustomLogger,
    logger_name="notes_ai",
    )
    groq_key = os.getenv("GROQ_API_KEY", "")
    if not groq_key or groq_key == "placeholder_key_for_import":
        logger.error("GROQ_API_KEY environment variable is not set. Please set it in your environment or .env file.")
        sys.exit(1)

    extractors = [
        YouTubeExtractor(logger= logger),
        WebExtractor(logger=logger),
        PDFExtractor(logger=logger),
        ImageExtractor(api_key=groq_key, logger=logger),
        AudioExtractor(logger=logger),
    ]
    llm = GroqLLMClient(api_key=groq_key)
    store = MarkdownNoteStore(output_dir=args.output_dir)

    for idx, source_path in enumerate(args.sources, start=1):
        logger.info(f"[{idx}/{len(args.sources)}] Processing source: {source_path}")
        try:
            input_type = process_content(source_path, logger=logger)
            logger.info(f"Source detected:{input_type}")
        except Exception as e:
            logger.error(f"Unsupported source or file not found ({source_path}): {e}")
            continue

        title = (
            args.name if (args.name and len(args.sources) == 1)
            else (Path(source_path).stem if not source_path.startswith(("http://", "https://")) else f"note_{idx}")
        )

        source_obj = Source(
            input_type=input_type,
            location=source_path,
            title=title,
            metadata={},
        )

        try:
            note = asyncio.run(
                create_note(
                    source=source_obj,
                    extractors=extractors,
                    llm=llm,
                    store=store,
                    logger =logger
                )
            )
            logger.success(f"Successfully generated note: {args.output_dir}/{note.title}.md")
        except Exception as e:
            logger.error(f"Failed to create note for {source_path}: {e}")


if __name__ == "__main__":
    main()
