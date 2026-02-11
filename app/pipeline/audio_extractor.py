"""Audio extraction and media information utilities.

Provides FFmpeg-based audio extraction from video files, media probing,
and format conversion for the VoiceClone AI pipeline.
"""

import asyncio
import json
import logging
import subprocess
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

VIDEO_EXTENSIONS: frozenset[str] = frozenset({
    ".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv",
})


class AudioExtractor:
    """Extract audio from video files and inspect media metadata using FFmpeg.

    All heavy operations run as async subprocesses so they never block the
    event loop.  Output is always single-channel PCM WAV at the project's
    configured sample rate unless overridden.
    """

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    @staticmethod
    def is_video(file_path: Path) -> bool:
        """Return ``True`` when *file_path* has a recognised video extension.

        The check is case-insensitive and based solely on the file suffix.

        Args:
            file_path: Path to the media file.

        Returns:
            ``True`` for video files, ``False`` otherwise.
        """
        return file_path.suffix.lower() in VIDEO_EXTENSIONS

    # ------------------------------------------------------------------
    # Audio extraction
    # ------------------------------------------------------------------

    async def extract_audio(
        self,
        input_path: Path,
        output_path: Path,
    ) -> Path:
        """Extract the audio stream from a video file as mono WAV.

        Uses FFmpeg to demux the audio track, re-encode it to 16-bit PCM,
        and down-mix to a single channel at ``settings.SAMPLE_RATE``.

        Args:
            input_path:  Path to the source video file.
            output_path: Destination path for the extracted WAV file.

        Returns:
            The *output_path* on success.

        Raises:
            FileNotFoundError: If *input_path* does not exist.
            RuntimeError:      If FFmpeg returns a non-zero exit code.
        """
        input_path = Path(input_path)
        output_path = Path(output_path)

        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            settings.FFMPEG_PATH,
            "-y",
            "-i", str(input_path),
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", str(settings.SAMPLE_RATE),
            "-ac", "1",
            str(output_path),
        ]

        logger.info(
            "Extracting audio: %s -> %s (sample_rate=%d)",
            input_path.name,
            output_path.name,
            settings.SAMPLE_RATE,
        )

        result = await asyncio.to_thread(
            subprocess.run, cmd, capture_output=True,
        )

        if result.returncode != 0:
            stderr_text = result.stderr.decode(errors="replace").strip()
            logger.error("FFmpeg extraction failed (rc=%d): %s", result.returncode, stderr_text)
            raise RuntimeError(
                f"FFmpeg audio extraction failed with exit code {result.returncode}: {stderr_text}"
            )

        logger.info("Audio extraction complete: %s", output_path.name)
        return output_path

    # ------------------------------------------------------------------
    # Media information
    # ------------------------------------------------------------------

    async def get_media_info(self, file_path: Path) -> dict:
        """Probe *file_path* with FFprobe and return structured metadata.

        The returned dictionary contains:

        * ``duration``    -- float, total duration in seconds (0.0 if unknown).
        * ``codec``       -- str, audio codec name (empty string if absent).
        * ``sample_rate`` -- int, audio sample rate in Hz (0 if absent).
        * ``channels``    -- int, number of audio channels (0 if absent).
        * ``has_video``   -- bool, ``True`` when at least one video stream exists.
        * ``has_audio``   -- bool, ``True`` when at least one audio stream exists.

        Args:
            file_path: Path to the media file to inspect.

        Returns:
            A metadata dictionary as described above.

        Raises:
            FileNotFoundError: If *file_path* does not exist.
            RuntimeError:      If FFprobe returns a non-zero exit code.
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"Media file not found: {file_path}")

        cmd = [
            settings.FFPROBE_PATH,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(file_path),
        ]

        logger.debug("Probing media: %s", file_path.name)

        result = await asyncio.to_thread(
            subprocess.run, cmd, capture_output=True,
        )

        if result.returncode != 0:
            stderr_text = result.stderr.decode(errors="replace").strip()
            logger.error("FFprobe failed (rc=%d): %s", result.returncode, stderr_text)
            raise RuntimeError(
                f"FFprobe failed with exit code {result.returncode}: {stderr_text}"
            )

        try:
            probe_data = json.loads(result.stdout.decode())
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse FFprobe JSON output: %s", exc)
            raise RuntimeError(f"FFprobe returned invalid JSON: {exc}") from exc

        return self._parse_probe_data(probe_data)

    # ------------------------------------------------------------------
    # Format conversion
    # ------------------------------------------------------------------

    async def convert_to_wav(
        self,
        input_path: Path,
        output_path: Path,
        sample_rate: int | None = None,
    ) -> Path:
        """Convert any audio format to single-channel 16-bit PCM WAV.

        Args:
            input_path:  Path to the source audio file.
            output_path: Destination path for the WAV file.
            sample_rate: Target sample rate in Hz.  Defaults to
                         ``settings.SAMPLE_RATE`` when ``None``.

        Returns:
            The *output_path* on success.

        Raises:
            FileNotFoundError: If *input_path* does not exist.
            RuntimeError:      If FFmpeg returns a non-zero exit code.
        """
        input_path = Path(input_path)
        output_path = Path(output_path)

        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")

        target_sr = sample_rate if sample_rate is not None else settings.SAMPLE_RATE
        output_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            settings.FFMPEG_PATH,
            "-y",
            "-i", str(input_path),
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", str(target_sr),
            "-ac", "1",
            str(output_path),
        ]

        logger.info(
            "Converting audio: %s -> %s (sample_rate=%d)",
            input_path.name,
            output_path.name,
            target_sr,
        )

        result = await asyncio.to_thread(
            subprocess.run, cmd, capture_output=True,
        )

        if result.returncode != 0:
            stderr_text = result.stderr.decode(errors="replace").strip()
            logger.error("FFmpeg conversion failed (rc=%d): %s", result.returncode, stderr_text)
            raise RuntimeError(
                f"FFmpeg audio conversion failed with exit code {result.returncode}: {stderr_text}"
            )

        logger.info("Audio conversion complete: %s", output_path.name)
        return output_path

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_probe_data(probe_data: dict) -> dict:
        """Distill raw FFprobe JSON into a clean metadata dictionary."""
        streams = probe_data.get("streams", [])
        format_info = probe_data.get("format", {})

        has_video = False
        has_audio = False
        audio_codec = ""
        audio_sample_rate = 0
        audio_channels = 0

        for stream in streams:
            codec_type = stream.get("codec_type", "")
            if codec_type == "video":
                has_video = True
            elif codec_type == "audio":
                has_audio = True
                if not audio_codec:
                    audio_codec = stream.get("codec_name", "")
                    audio_sample_rate = int(stream.get("sample_rate", 0))
                    audio_channels = int(stream.get("channels", 0))

        duration_str = format_info.get("duration", "0")
        try:
            duration = float(duration_str)
        except (ValueError, TypeError):
            duration = 0.0

        return {
            "duration": duration,
            "codec": audio_codec,
            "sample_rate": audio_sample_rate,
            "channels": audio_channels,
            "has_video": has_video,
            "has_audio": has_audio,
        }
