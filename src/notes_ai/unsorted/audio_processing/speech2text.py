import re
import shutil
from time import sleep
from pathlib import Path
from warnings import deprecated
from pydub import AudioSegment
from faster_whisper import WhisperModel
from groq import Groq

from notes_ai.utils.logging_config import CustomLogger


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


def _parse_retry_delay_seconds(message: str) -> float:
    """Extract 'Please try again in XmYs' from RateLimitError message."""
    # Examples: 'Please try again in 4m52.5s' or 'Please try again in 35s'
    m = re.search(r"Please try again in\s*(?:(\d+)m)?([\d\.]+)s", message)
    if not m:
        return 60.0  # fallback 60s
    minutes = float(m.group(1) or 0)
    seconds = float(m.group(2))
    return minutes * 60 + seconds


@deprecated("This function is using Groq's API which may be slow due to rate limiting. Consider using local transcription _transcribe_audio_chunk_local() instead.")
def _transcribe_audio_chunk(client: Groq, chunk_path: str | Path, logger: CustomLogger, model="whisper-large-v3") -> str:
    chunk_name = Path(chunk_path).name
    with open(chunk_path, "rb") as audio_file:
        try:
            result = client.audio.transcriptions.create(
                file=(chunk_name, audio_file.read()),
                model=model,
            )
        except Exception as e:
            msg = str(e)
            logger.debug(f"Full exception message: {msg}")
            wait_sec = _parse_retry_delay_seconds(msg) + 10
            logger.warning(
                f"Rate limit hit for {model}. Waiting {wait_sec:.1f}s. Message: {msg}")
            sleep(wait_sec)
            audio_file.seek(0)
            result = client.audio.transcriptions.create(
                file=(chunk_name, audio_file.read()),
                model=model,
            )
    transcription = result.text
    logger.debug(f"Transcribed chunk {chunk_name}: {transcription[:10]}...")
    return transcription


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


@deprecated("Use transcribe_with_groq instead")
def transcribe_with_groq(chunks_dir: str | Path | list[Path], logger: CustomLogger) -> str:
    """
    Transcribing audio chunks using Groq's speech-to-text model.

    Args:
        chunks_dir (str | Path | list[Path]): Directory containing audio chunks or a list of chunk paths.

    Returns:
        str: The combined transcription of all audio chunks.
    """
    client = Groq()

    # check if chunks_dir is a list of Paths
    if isinstance(chunks_dir, list):
        chunk_paths = chunks_dir
    # otherwise, assume it's a directory
    else:
        chunk_paths = sorted(Path(chunks_dir).glob("*.mp3"))
    logger.debug(f"Found {len(chunk_paths)} audio chunks to transcribe.")

    transcriptions = []
    for chunk_path in chunk_paths:
        try:
            transcription = _transcribe_audio_chunk(client, chunk_path, logger)
        except Exception as e:
            # Redundant safety: if error surfaces here, wait and retry once
            msg = str(e)
            wait_sec = _parse_retry_delay_seconds(msg) + 10.0
            logger.warning(
                f"Rate limit (OUTER) for {chunk_path}. Waiting {wait_sec:.1f}s. Message: {msg}")
            sleep(wait_sec)
            transcription = _transcribe_audio_chunk(client, chunk_path, logger)
        transcriptions.append(transcription)

    logger.debug(
        f"Transcriptions for all chunks: {transcriptions[:10]}...{transcriptions[-10:]}")
    return "\n".join(transcriptions)


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
