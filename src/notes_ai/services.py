import asyncio
import mdformat
from typing import cast
from pathlib import Path

from notes_ai.unsorted.yt_processing.downloader import yt_dlp_download, DownloadType, AudioFormat, AudioQuality
from notes_ai.utils.input_handler import process_content
from notes_ai.unsorted.note_generator.generator import generate_note
from notes_ai.unsorted.note_generator.final_cleaner import clean_note
from notes_ai.unsorted.note_generator import apply_color_markup, generate_raw_outline
from notes_ai.unsorted.art_generator.ArtManager import ArtManager
from notes_ai.utils.logging_config import CustomLogger


def download_youtube(
    url: str,
    logger: CustomLogger,
    output_dir: Path | None = None,
    name: str | None = None,
    download_type: DownloadType = "audio",
    audio_format: AudioFormat = "mp3",
    audio_quality: AudioQuality = "320",
) -> Path:
    """
    Download audio or video from YouTube.

    Args:
        url: YouTube URL
        logger: Logger instance
        output_dir: Output directory (default: current working directory)
        name: Custom filename without extension
        download_type: 'audio' or 'video'
        audio_format: 'mp3', 'm4a', 'wav', 'opus'
        audio_quality: '128', '192', '256', '320' kbps

    Returns:
        Path to downloaded file
    """
    final_path = yt_dlp_download(
        yt_url=url,
        logger=logger,
        output_dir=output_dir,
        name=name,
        download_type=download_type,
        audio_format=audio_format,
        audio_quality=audio_quality,
    )
    return final_path


async def transcribe_content(
    input_path: str,
    logger: CustomLogger,
    output_dir: Path | None = None,
    name: str | None = None,
    chunk_duration: int = 600,
    include_metadata: bool = False,
    output_format: str = "text",
    save_to_file: bool = False,
) -> str:
    """
    Transcribe or extract text from ANY source (YouTube, Web, PDF, Image, Audio).

    Args:
        input_path: Path or URL to process
        logger: Logger instance
        output_dir: Output directory (if save_to_file=True)
        name: Custom filename without extension
        chunk_duration: Chunk duration in seconds
        include_metadata: Include metadata when extracting web articles
        output_format: 'text', 'md', 'json'
        save_to_file: Whether to save result to file

    Returns:
        Extracted/transcribed text
    """
    result = process_content(
        input_path,
        logger=logger,
        chunk_duration=chunk_duration,
        include_metadata=include_metadata,
        output_format=output_format,
    )

    # Handle async/sync
    if asyncio.iscoroutine(result):
        text = await result
    else:
        text = cast(str, result)

    if save_to_file:
        output_path = output_dir if output_dir else Path.cwd()
        filename = name if name else "extracted_content"

        # Determine extension
        ext = ".txt"
        if output_format == "json":
            ext = ".json"
        elif output_format == "md" or include_metadata:
            ext = ".md"

        filename += ext

        final_path = output_path / filename
        final_path.parent.mkdir(parents=True, exist_ok=True)
        final_path.write_text(text, encoding="utf-8")
        logger.success(f"Saved content to: {final_path}")

    return text


async def create_structured_note_with_orchestration(
    input_path: str,
    logger: CustomLogger,
    output_dir: Path | None = None,
    name: str | None = None,
    chunk_duration: int = 600,
    include_metadata: bool = False,
    output_format: str = "md",
) -> tuple[str, Path]:
    """
    Create a structured note using orchestrated multi-agent pipeline.

    Two-step orchestration:
    1. generate_raw_outline() - Create outline with selective semantic color markup
    2. enrich_with_examples_and_metaphors() - Add Example and Metaphor blocks for complex concepts

    Args:
        input_path: Path or URL to process
        logger: Logger instance
        output_dir: Output directory (default: current working directory)
        name: Custom filename without extension (default: 'note')
        chunk_duration: Chunk duration in seconds
        include_metadata: Include metadata when extracting web articles
        output_format: 'text', 'md', 'json'

    Returns:
        Tuple of (note_content, file_path)
    """
    logger.info("Step 1/3: Extracting content from source...")
    extracted_text = await transcribe_content(
        input_path,
        logger=logger,
        chunk_duration=chunk_duration,
        include_metadata=include_metadata,
        output_format=output_format,
        save_to_file=False,
    )

    logger.info("Step 2/3: Generating outline with selective color markup...")

    outline = generate_raw_outline(
        source_content=extracted_text,
        logger=logger,
    )

    manager = ArtManager()

    outline_with_art = manager.process_document(
        document_content=outline
    )

    colored_outline = apply_color_markup(
        outline=outline_with_art,
        logger=logger,
    )

    # Format the markdown content
    formatted_content = mdformat.text(
        colored_outline,
        extensions=["myst"],
    )

    cleaned_content = clean_note(formatted_content)

    # Save to file
    output_path = output_dir if output_dir else Path.cwd()
    filename = name if name else "note"

    if not filename.endswith(".md"):
        cleaned_content = f"# {filename}\n\n" + cleaned_content
        filename += ".md"
    else:
        cleaned_content = f"# {filename[:-3]}\n\n" + cleaned_content

    logger.debug(f"Final content:\n\n{cleaned_content[:1000]}...")

    final_path = output_path / filename
    final_path.parent.mkdir(parents=True, exist_ok=True)
    final_path.write_text(cleaned_content, encoding="utf-8")

    logger.success(f"Created note: {final_path.absolute()}")

    return cleaned_content, final_path


async def create_note_from_source(
    input_path: str,
    logger: CustomLogger,
    output_dir: Path | None = None,
    name: str | None = None,
    chunk_duration: int = 600,
    include_metadata: bool = False,
    output_format: str = "md",
) -> tuple[str, Path]:
    """
    Create a structured note from ANY source (YouTube, Web, PDF, Image, Audio).

    Extracts/transcribes content, then generates an AI-powered note.

    Args:
        input_path: Path or URL to process
        logger: Logger instance
        output_dir: Output directory (default: current working directory)
        name: Custom filename without extension (default: 'note')
        chunk_duration: Chunk duration in seconds
        include_metadata: Include metadata when extracting web articles
        output_format: 'text', 'md', 'json'

    Returns:
        Tuple of (note_content, file_path)
    """
    logger.info("Step 1/2: Extracting content from source...")
    extracted_text = await transcribe_content(
        input_path,
        logger=logger,
        chunk_duration=chunk_duration,
        include_metadata=include_metadata,
        output_format=output_format,
        save_to_file=False,
    )

    logger.debug(f"Extracted {len(extracted_text)} characters")

    logger.info("Step 2/2: Generating structured note with AI...")
    note_content = generate_note(
        source_content=extracted_text,
        logger=logger,
    )

    # Clean up final content
    cleaned_content = clean_note(note_content)

    # Format the markdown content
    formatted_content = mdformat.text(
        cleaned_content,
        extensions=["myst"],
    )

    # Save to file
    output_path = output_dir if output_dir else Path.cwd()
    filename = name if name else "note"

    if not filename.endswith(".md"):
        formatted_content = f"# {filename}\n\n" + formatted_content
        filename += ".md"
    else:
        formatted_content = f"# {filename[:-3]}\n\n" + formatted_content

    logger.debug(f"Final content:\n\n{formatted_content[:1000]}...")

    final_path = output_path / filename
    final_path.parent.mkdir(parents=True, exist_ok=True)
    final_path.write_text(formatted_content, encoding="utf-8")

    logger.success(f"Created note: {final_path.absolute()}")

    return formatted_content, final_path
