from pathlib import Path
from typing import Literal

import yt_dlp
from yt_dlp.utils import DownloadError

from notes_ai.interfaces.exceptions import ExtractionError
from notes_ai.loggers import CustomLogger

DownloadType = Literal["audio", "video"]
AudioFormat = Literal["mp3", "m4a", "wav", "opus"]
AudioQuality = Literal["128", "192", "256", "320"]


def _build_outtmpl(output_dir: Path, name: str | None) -> str:
    filename_template = f"{name}.%(ext)s" if name else "%(title)s.%(ext)s"
    return str(output_dir / filename_template)


def _build_ydl_opts(
    download_type: DownloadType,
    audio_format: AudioFormat,
    audio_quality: AudioQuality,
    outtmpl: str,
    player_client: str | None = None,
) -> dict:
    base = {
        "outtmpl": outtmpl,
        "restrictfilenames": True,
    }
    if player_client:
        base["extractor_args"] = {"youtube": {"player_client": [player_client]}}

    if download_type == "audio":
        # without FFMPEG re-encoding, some formats may not respect the quality setting
        base.update(
            {
                "format": f"bestaudio[ext={audio_format}]/bestaudio/best",
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": audio_format,
                        "preferredquality": audio_quality,
                    }
                ],
            }
        )
    else:  # video
        base.update(
            {
                "format": "bestvideo[ext=mp4]+bestaudio/best/best",
                "merge_output_format": "mp4",
            }
        )
    return base


def _get_final_path(
    result: dict,
    ydl: yt_dlp.YoutubeDL,
    download_type: DownloadType,
    audio_format: AudioFormat,
    output_dir: Path,
    name: str | None,
) -> Path:
    if name:
        ext = audio_format if download_type == "audio" else "mp4"
        return output_dir / f"{name}.{ext}"
    base_filename = ydl.prepare_filename(result)  # type: ignore
    if download_type == "audio":
        return Path(base_filename).with_suffix(f".{audio_format}")
    return Path(base_filename)


def yt_dlp_download(
    yt_url: str,
    *,
    logger: CustomLogger,
    output_dir: Path | None = None,
    name: str | None = None,
    download_type: DownloadType = "audio",
    audio_format: AudioFormat = "mp3",
    audio_quality: AudioQuality = "320",
    player_clients: tuple[str, ...] = ("android", "ios", "web", "android_vr"),
) -> Path:
    """
    Download from YouTube via yt-dlp.

    Args:
        yt_url: Source URL.
        logger: App logger.
        output_dir: Target directory (must exist or will be created).
        name: Custom base filename without extension. If None, use video title.
        download_type: "audio" or "video".
        audio_format: Audio format if download_type == "audio".
        audio_quality: Audio bitrate in kbps.
        player_clients: Preferred YouTube player clients to try.

    Returns:
        Path: Final downloaded file path.
    """
    # if not provided, use current working directory
    if output_dir is None:
        output_dir = Path.cwd()

    output_dir.mkdir(parents=True, exist_ok=True)
    outtmpl = _build_outtmpl(output_dir, name)

    last_error: Exception | None = None
    for client in player_clients:
        ydl_opts = _build_ydl_opts(
            download_type, audio_format, audio_quality, outtmpl, player_client=client
        )
        logger.debug(f"yt-dlp: client={client}, type={download_type}, out='{outtmpl}'")
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # type: ignore
                result = ydl.extract_info(yt_url, download=True)
                final_path = _get_final_path(
                    result, ydl, download_type, audio_format, output_dir, name
                )  # type: ignore
                if final_path.exists():
                    logger.debug(f"yt-dlp: saved to {final_path}")
                    return final_path
                raise FileNotFoundError(f"Expected output file not found: {final_path}")
        except DownloadError as e:
            last_error = e
            logger.warning(f"yt-dlp client '{client}' failed: {e}")
        except Exception as e:
            last_error = e
            logger.error(f"yt-dlp unexpected error: {e}")

    raise ExtractionError(
        f"All clients failed: {player_clients}. Last error: {last_error}"
    ) from last_error
