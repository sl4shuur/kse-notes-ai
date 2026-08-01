import re
import shutil
from pathlib import Path
from pydub import AudioSegment
from faster_whisper import WhisperModel

from notes_ai.utils.logging_config import CustomLogger
from notes_ai.models import Source, ExtractedContent


def create_audio_chunks(audio_file: str | Path, chunk_duration_ms: int, temp_dir: str | Path, logger: CustomLogger) -> list[Path]:
    """
    Create chunks of audio from a given audio file.

    Args:
        audio_file (str | Path): The path to the audio file to chunk.
        chunk_duration_ms (int): The duration of each chunk in milliseconds.
        temp_dir (str | Path, optional): The directory to store temporary files. Defaults to TEMP_DIR.

    Returns:
        list[Path]: A list of paths to the created audio chunks.
    """

    audio = AudioSegment.from_file(audio_file)
    total_duration_ms = len(audio)
    chunk_paths = []
    cur_temp_dir = Path(temp_dir) / Path(audio_file).stem
    # remove existing temp dir if exists
    shutil.rmtree(cur_temp_dir, ignore_errors=True)
    # and create a new one
    cur_temp_dir.mkdir(parents=True, exist_ok=True)

    for start_ms in range(0, total_duration_ms, chunk_duration_ms):
        end_ms = min(start_ms + chunk_duration_ms, total_duration_ms)
        chunk = audio[start_ms:end_ms]
        chunk_filename = f"{Path(audio_file).stem}_chunk_{start_ms // 1000}_{end_ms // 1000}.mp3"
        chunk_path = cur_temp_dir / chunk_filename
        chunk.export(chunk_path, format="mp3")
        chunk_paths.append(chunk_path)
        logger.debug(
            f"Created audio chunk from {start_ms // 1000}s to {end_ms // 1000}s")

    return chunk_paths


def _transcribe_audio_chunk_local(
    model: WhisperModel,
    chunk_path: str | Path,
    logger: CustomLogger,
    language: str | None = None
) -> str:
    chunk_path = Path(chunk_path)
    chunk_name = chunk_path.name
    logger.debug(f"Transcribing chunk {chunk_name} with WhisperModel locally.")

    # Check if the file exists and is valid
    if not chunk_path.exists():
        logger.error(f"Audio chunk {chunk_path} does not exist.")
        return ""

    segments, info = model.transcribe(
        str(chunk_path),
        language=language,
        log_progress=True,        # Show progress in console
        beam_size=5,              # Higher = better quality, slower
        best_of=5,                # Number of candidates to consider
        temperature=0.0,          # Deterministic output
        vad_filter=True,          # Voice Activity Detection
        vad_parameters=dict(
            min_silence_duration_ms=500,
            threshold=0.5
        ),
        word_timestamps=False     # Set to True if you need word-level timing
    )

    # Combine segments into a single transcription
    transcription = " ".join([segment.text for segment in segments])

    logger.debug(
        f"Detected language: {info.language} (probability: {info.language_probability:.2f})")
    logger.debug(f"Transcribed chunk {chunk_name}: {transcription[:50]}...")

    return transcription


def transcribe_with_faster_whisper(
    chunks_dir: str | Path | list[Path],
    logger: CustomLogger,
    model_size: str = "tiny",  # tiny, base, small, medium, large-v1...
    device: str = "cpu",
    compute_type: str = "int8",  # int8, int16, float16, float32
    language: str | None = None
) -> str:
    logger.debug(
        f"Loading Faster Whisper model: {model_size} on {device} with {compute_type}")

    model = WhisperModel(
        model_size,
        device=device,
        compute_type=compute_type,
        download_root=None,  # Uses default cache directory
        local_files_only=False
    )

    # Get chunk paths
    if isinstance(chunks_dir, list):
        chunk_paths = chunks_dir
    else:
        chunk_paths = sorted(Path(chunks_dir).glob("*.mp3"))

    logger.info(
        f"Found {len(chunk_paths)} audio chunks to transcribe locally.")

    transcriptions = []

    for i, chunk_path in enumerate(chunk_paths, 1):
        logger.debug(
            f"Processing chunk {i}/{len(chunk_paths)}: {chunk_path.name}")
        transcription = _transcribe_audio_chunk_local(
            model, chunk_path, logger, language)
        transcriptions.append(transcription)

    result = "\n".join(transcriptions)
    logger.info(
        f"Local transcription completed. Total length: {len(result)} chars")
    return result


class AudioExtractor:
    """Extracts Audio using Whisper model."""

    def __init__(self, logger: CustomLogger):
        self.logger = logger
        self.temp_dir: Path = Path("audio_dir")
        self.chunk_duration_ms: int = 30000

    def supports(self, source: Source) -> bool:
        return source.input_type.lower() == "audio"

    async def extract(self, source: Source) -> ExtractedContent:
        path = Path(source.location)

        if not path.exists():
            raise FileNotFoundError(f"Audio file {source} does not exist.")

        chunks = create_audio_chunks(
            audio_file=path,
            chunk_duration_ms=self.chunk_duration_ms,
            temp_dir = self.temp_dir,
            logger=self.logger,
        )
        self.logger.debug(f"Created {len(chunks)} audio chunks")

        text = transcribe_with_faster_whisper(
            chunks_dir=chunks,
            logger=self.logger,
        )

        self.logger.info(
            f"Transcription complete: {len(text)} chars from {len(chunks)} chunks"
        )

        return ExtractedContent(
            text=text,
            metadata={
                "source_file": path.name,
                "chunk_count": len(chunks),
            },
        )

