from notes_ai.interfaces.extractor import TextExtractor
from notes_ai.models import ExtractedContent, Source, YouTubeExtractionMetadata


import re
import html
from pathlib import Path

import yt_dlp
import webvtt

from io import StringIO
from time import sleep

from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from notes_ai.adapters.extractors.downloader import yt_dlp_download
from notes_ai.adapters.extractors.audio import create_audio_chunks, transcribe_with_faster_whisper
from notes_ai.config import get_config
from notes_ai.loggers import CustomLogger
from notes_ai.interfaces.exceptions import ExtractionError
from notes_ai.interfaces.extractor import TextExtractor

class YouTubeExtractor(TextExtractor):
    def __init__(
        self,
        logger: CustomLogger,
        temp_audio_dir: str | Path | None = None,
    ):
        self.logger = logger
        self.temp_audio_dir = Path(temp_audio_dir or get_config().temp_audio_dir)
    def supports(self, source: Source) -> bool:
        return source.input_type == "youtube"

    
    def _strip_vtt_markup_preserve_text(self, line: str) -> str:
        """Remove WebVTT inline timing/markup while preserving human text and punctuation."""
        t = line
        # Remove inline timing tags like <00:00:03.360>
        t = re.sub(r"<\d{2}:\d{2}:\d{2}\.\d{3}>", " ", t)
        # Remove <c> class tags but keep inner text (already extracted as raw line)
        t = re.sub(r"</?c[^>]*>", " ", t)
        # Remove any remaining angle-bracket tags (rare), keep text
        t = re.sub(r"<[^>]+>", " ", t)
        # Remove known directive tokens that can leak
        t = re.sub(r"\balign:\w+\b", " ", t)
        t = re.sub(r"\bposition:\d+%?\b", " ", t)
        # Collapse whitespace
        t = re.sub(r"\s+", " ", t).strip()
        return t


    def _normalize_for_duplicate_check(self, line: str) -> str:
        """Normalize line for duplicate detection: lowercase, remove punctuation, collapse spaces."""
        t = line.lower()
        # Remove punctuation but keep letters/numbers/spaces (Latin+Cyrillic friendly)
        t = re.sub(r"[^0-9a-zа-яё\s]", " ", t, flags=re.IGNORECASE)
        t = re.sub(r"\s+", " ", t).strip()
        return t


    def _normalize_whitespace(self, text: str, keep_newlines: bool = True) -> str:
        """Decode HTML entities, replace NBSPs with regular spaces, collapse spaces."""
        # 1) Decode HTML entities like &nbsp;, &amp;, &quot;, etc.
        t = html.unescape(text)

        # 2) Replace various Unicode whitespace characters with regular spaces
        t = (
            t.replace("\u00A0", " ")   # NO-BREAK SPACE
            .replace("\u202F", " ")   # NARROW NO-BREAK SPACE
            .replace("\u2009", " ")   # THIN SPACE
            .replace("\u200A", " ")   # HAIR SPACE
            .replace("\u2007", " ")   # FIGURE SPACE
            .replace("\u2008", " ")   # PUNCTUATION SPACE
            .replace("\ufeff", "")    # ZERO WIDTH NO-BREAK SPACE (BOM)
            .replace("\u200B", "")    # ZERO WIDTH SPACE
            .replace("\u200C", "")    # ZERO WIDTH NON-JOINER
            .replace("\u200D", "")    # ZERO WIDTH JOINER
        )

        # 3) Remove other control characters except newlines/tabs (if keeping newlines)
        if keep_newlines:
            # Remove control chars except \n and \t
            t = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", t)
        else:
            # Remove all control characters
            t = re.sub(r"[\x00-\x1F\x7F]", " ", t)

        # 4) Normalize whitespace based on keep_newlines flag
        if keep_newlines:
            # Collapse runs of spaces/tabs on each line, preserve single newlines
            lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in t.splitlines()]
            # Remove empty lines and join
            t = "\n".join(ln for ln in lines if ln)
            # Collapse multiple consecutive newlines to max 2 (paragraph breaks)
            t = re.sub(r"\n{3,}", "\n\n", t)
        else:
            # Collapse all whitespace (spaces, tabs, newlines) to single spaces
            t = re.sub(r"\s+", " ", t).strip()

        return t


    def _clean_vtt_transcript(self, vtt_content: str) -> str:
        """Parse VTT, strip markup, preserve punctuation, and collapse consecutive duplicates."""
        vtt = webvtt.read_buffer(StringIO(vtt_content))
        lines: list[str] = []
        last_norm: str = ""

        for cue in vtt:
            # Split multi-line cue texts and process each line
            for raw in cue.text.split("\n"):
                # Step 1: Strip VTT markup (timing tags, class tags, etc.)
                cleaned = self._strip_vtt_markup_preserve_text(raw)
                if not cleaned:
                    continue

                # Step 2: Normalize whitespace (decode HTML entities, fix Unicode spaces)
                cleaned = self._normalize_whitespace(cleaned, keep_newlines=False)
                if not cleaned:
                    continue

                # Step 3: Check for duplicates using normalized form
                norm = self._normalize_for_duplicate_check(cleaned)
                if norm and norm == last_norm:
                    continue

                lines.append(cleaned)
                last_norm = norm

        # Join with single newlines, collapse extra blank lines
        text = "\n".join(lines)
        # Final pass: normalize the whole transcript, keeping line structure
        text = self._normalize_whitespace(text, keep_newlines=True)
        return text


    def _get_yt_lang(self, url: str, logger: CustomLogger) -> str | None:
        """Extract the language code from a YouTube URL if present."""
        info_opt = {
            'quiet': True,
            'skip_download': True,  # IMPORTANT: we need only metadata
        }

        logger.debug(f"Extracting video info for language detection from URL: {url}")

        lang = None
        try:
            with yt_dlp.YoutubeDL(info_opt) as ydl:  # type: ignore
                info_dict = ydl.extract_info(url, download=False)
                manual_subs = info_dict.get('subtitles', {}) # subtitles added by video owner
                auto_subs = info_dict.get('automatic_captions', {}) # auto-generated subtitles

                if manual_subs:
                    # pick the first manual subtitle language (often it is the first)
                    lang = next(iter(manual_subs.keys()), None)
                    logger.debug(f"Found manual subtitles in language: {lang}")
                elif auto_subs:
                    # pick the first auto-generated subtitle language
                    lang = next(iter(auto_subs.keys()), None)
                    logger.debug(f"Found automatic subtitles in language: {lang}")
                else:
                    logger.warning("No subtitles found in the YouTube video.")
                    return None
        except Exception as e:
            logger.error(f"Error extracting video info for language detection: {e}")
            return None


    def _get_video_id_from_url(self, url: str) -> str:
        """Extract the YouTube video ID from a URL."""
        # Patterns to match various YouTube URL formats
        patterns = [
            r"(?:v=|\/)([0-9A-Za-z_-]{11}).*",  # Standard YouTube URL
            r"youtu\.be\/([0-9A-Za-z_-]{11})",  # Shortened youtu.be URL
            r"youtube\.com\/shorts\/([0-9A-Za-z_-]{11})",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        raise ExtractionError("Invalid YouTube URL: Unable to extract video ID.")

    def get_yt_transcript(self,source: Source, logger: CustomLogger) -> ExtractedContent | None:
        """
        Download YouTube subtitles.

        Args:
            url (str): YouTube video URL.
            logger (CustomLogger): Logger instance for logging.

        Returns:
            tuple[str, str] | None: A tuple containing the transcript text and language code, or None if not available.
        """
        url = source.location
        ytt_api = YouTubeTranscriptApi()

        try:
            # 1. Get ID from URL
            video_id = self._get_video_id_from_url(url)
            logger.debug(f"Extracted video ID: {video_id}")

            # 2. Get the list of available transcripts
            transcript_list = ytt_api.list(video_id)
            logger.debug(f"Available transcripts: {[t.language_code for t in transcript_list]}")

            # 3. Try to find a suitable transcript
            try:
                # Prefer manually created transcripts
                transcript = transcript_list.find_manually_created_transcript(
                    ["en", "uk", "ru"]
                )
                logger.debug("Using manually created transcript.")

            except NoTranscriptFound:
                transcript = next(iter(transcript_list))
            
            logger.debug(f"Found transcript! Language: {transcript.language_code}. Auto-generated: {transcript.is_generated}")

            # 4. Fetch the transcript data
            transcript_data = transcript.fetch()

            # 5. Convert to single string
            # transcript_data now is a list of FetchedTranscriptSnippet objects with 'text', 'start', 'duration' attributes
            full_text = " ".join(item.text for item in transcript_data)

            return ExtractedContent(
                text=full_text,
                metadata=YouTubeExtractionMetadata(
                    method="subtitles",
                    language_code=transcript.language_code,
                ),
            )

        except TranscriptsDisabled:
            logger.warning("Transcripts are disabled for this video.")
            return None

        except Exception as e:
            logger.error(f"Error downloading YouTube transcript: {e}")
            return None


    


    async def extract(
        self,
        source: Source,
        chunk_duration_ms: int = 100000,
        force_whisper: bool = True,
    ) -> ExtractedContent:
        """
        Generate a transcription for a YouTube video URL.

        Args:
            yt_url (str): The YouTube video URL.
            chunk_duration_ms (int, optional): Duration of each audio chunk in milliseconds. Defaults to 10 minutes.

        Returns:
            str: The full transcription of the YouTube video.
        """
        yt_url = source.location
        logger = self.logger

        logger.info(f"Starting transcription for YouTube URL: {yt_url}")
        # 1. Attempt to get the transcript directly (if force_whisper is False)
        if not force_whisper:
            result =  self.get_yt_transcript(source, logger)
            if result and type(result.metadata) == YouTubeExtractionMetadata:
                logger.info(
                    "Transcript extracted via YT subtitles. Language: %s",
                    result.metadata.language_code,
                )
                return result
        # If transcript extraction fails, download the audio
        audio_file = yt_dlp_download(
            yt_url, logger=logger, output_dir=self.temp_audio_dir)
        logger.debug(f"Downloaded audio file: {audio_file}")

        chunks = create_audio_chunks(
            audio_file, chunk_duration_ms, temp_dir=self.temp_audio_dir, logger=logger)
        logger.debug(f"Created {len(chunks)} audio chunks.")

        transcription = transcribe_with_faster_whisper(chunks, logger)
        logger.info("Completed transcription.")

        return ExtractedContent(
            text=transcription,
            metadata=YouTubeExtractionMetadata(method="whisper"),
        )
