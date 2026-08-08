"""Simple CLI for Notes AI using argparse and the package pipeline."""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from notes_ai.config import get_config

from notes_ai.adapters.extractors.audio import AudioExtractor
from notes_ai.adapters.extractors.image import ImageExtractor
from notes_ai.adapters.extractors.pdf import PDFExtractor
from notes_ai.adapters.extractors.web import WebExtractor
from notes_ai.adapters.extractors.youtube import YouTubeExtractor
from notes_ai.adapters.llm.groq import GroqLLMClient
from notes_ai.adapters.llm_services.note_generator import NoteGenerator
from notes_ai.adapters.storage.markdown import MarkdownNoteStore
from notes_ai.ingestion import create_source
from notes_ai.pipeline import create_note
from notes_ai.loggers import CustomLogger


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
    config = get_config()
    logger = CustomLogger(config.app_name)
    if args.verbose:
        logger.setLevel(logging.DEBUG)

    groq_key = config.groq_api_key
    if not groq_key:
        logger.error("GROQ_API_KEY environment variable is not set. Please set it in your environment or .env file.")
        sys.exit(1)
    llm = GroqLLMClient(api_key=groq_key)
    generator = NoteGenerator(llm, logger)
    store = MarkdownNoteStore(output_dir=args.output_dir)
    extractors = [
        YouTubeExtractor(logger=logger, temp_audio_dir=config.temp_audio_dir),
        WebExtractor(logger=logger),
        PDFExtractor(logger=logger),
        ImageExtractor(llm=llm, logger=logger),
        AudioExtractor(logger=logger),
    ]
    

    for idx, source_path in enumerate(args.sources, start=1):
        logger.info(f"[{idx}/{len(args.sources)}] Processing source: {source_path}")
        title = (
            args.name if (args.name and len(args.sources) == 1)
            else (Path(source_path).stem if not source_path.startswith(("http://", "https://")) else f"note_{idx}")
        )

        try:
            source_obj = create_source(
                source_path,
                logger,
                title=title,
            )
            logger.info("Source detected: %s", source_obj.input_type.value)
        except Exception as e:
            logger.error(f"Unsupported source or file not found ({source_path}): {e}")
            continue

        try:
            note = asyncio.run(
                create_note(
                    source=source_obj,
                    extractors=extractors,
                    generator=generator,
                    store=store,
                )
            )
            logger.success(f"Successfully generated note: {args.output_dir}/{note.title}.md")
        except Exception as e:
            logger.error(f"Failed to create note for {source_path}: {e}")


if __name__ == "__main__":
    main()
