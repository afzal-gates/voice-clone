"""Standalone audio utility functions for the VoiceClone AI platform.

Provides reusable helpers for loading, saving, trimming, normalizing,
fade processing, silence detection, format conversion, and signal analysis.
All functions are stateless and operate on numpy arrays or file paths.
"""

from __future__ import annotations

import asyncio
import logging
import subprocess
from pathlib import Path
from typing import Optional

import numpy as np
import soundfile as sf

from app.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------


async def load_audio(
    path: Path,
    sr: Optional[int] = None,
) -> tuple[np.ndarray, int]:
    """Load an audio file and optionally resample.

    Stereo files are automatically down-mixed to mono.  If *sr* is given and
    differs from the file's native sample rate, the audio is resampled using
    ``librosa``.

    Args:
        path: Path to the audio file (WAV, FLAC, OGG, etc.).
        sr: Target sample rate.  ``None`` keeps the native rate.

    Returns:
        A tuple of ``(audio, sample_rate)`` where *audio* is a 1-D float32
        numpy array.

    Raises:
        FileNotFoundError: If *path* does not exist.
    """
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {path}")

    audio, native_sr = await asyncio.to_thread(sf.read, str(path), "float32")

    # Stereo -> mono
    if audio.ndim > 1:
        audio = audio.mean(axis=1)

    # Resample
    if sr is not None and sr != native_sr:
        import librosa  # noqa: WPS433
        audio = await asyncio.to_thread(
            librosa.resample, audio, orig_sr=native_sr, target_sr=sr,
        )
        native_sr = sr

    return audio.astype(np.float32), native_sr


async def save_audio(
    audio: np.ndarray,
    path: Path,
    sr: int,
) -> Path:
    """Save a numpy audio array as a WAV file.

    Parent directories are created automatically if they do not exist.

    Args:
        audio: 1-D float32 audio array.
        path: Destination WAV file path.
        sr: Sample rate.

    Returns:
        *path* after writing the file.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    await asyncio.to_thread(sf.write, str(path), audio, sr)
    logger.debug("Saved audio: %s (%d samples, %d Hz)", path.name, len(audio), sr)
    return path


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


def get_duration(path: Path) -> float:
    """Return the duration of an audio file in seconds.

    Uses ``soundfile.info`` which reads only the file header, so this is
    very fast even for large files.

    Args:
        path: Path to the audio file.

    Returns:
        Duration in seconds.  Returns ``0.0`` if the file cannot be read.
    """
    try:
        info = sf.info(str(path))
        return info.duration
    except Exception as exc:
        logger.warning("Could not read duration for %s: %s", path, exc)
        return 0.0


# ---------------------------------------------------------------------------
# Format conversion
# ---------------------------------------------------------------------------


def convert_format(input_path: Path, output_path: Path) -> Path:
    """Convert between audio formats using FFmpeg.

    The output format is inferred from the *output_path* extension.  This is
    a synchronous blocking call -- wrap in ``asyncio.to_thread`` if calling
    from async code.

    Args:
        input_path: Source audio file.
        output_path: Destination file (extension determines codec).

    Returns:
        *output_path* on success.

    Raises:
        FileNotFoundError: If *input_path* does not exist.
        RuntimeError: If FFmpeg returns a non-zero exit code.
    """
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        settings.FFMPEG_PATH,
        "-y",
        "-i", str(input_path),
        str(output_path),
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        logger.error("FFmpeg conversion failed (rc=%d): %s", result.returncode, result.stderr)
        raise RuntimeError(
            f"FFmpeg conversion failed with exit code {result.returncode}: {result.stderr}"
        )

    logger.info("Converted: %s -> %s", input_path.name, output_path.name)
    return output_path


# ---------------------------------------------------------------------------
# Array operations
# ---------------------------------------------------------------------------


def trim_audio(
    audio: np.ndarray,
    start: float,
    end: float,
    sr: int,
) -> np.ndarray:
    """Extract a time range from an audio array.

    Args:
        audio: 1-D audio array.
        start: Start time in seconds (inclusive).
        end: End time in seconds (exclusive).
        sr: Sample rate.

    Returns:
        The extracted slice as a new array.  If the requested range exceeds
        the audio length, the slice is clamped to the available data.
    """
    start_sample = max(0, int(start * sr))
    end_sample = min(len(audio), int(end * sr))

    if start_sample >= end_sample:
        logger.warning(
            "trim_audio: empty result (start=%.3fs, end=%.3fs, audio_len=%.3fs)",
            start, end, len(audio) / sr,
        )
        return np.array([], dtype=audio.dtype)

    return audio[start_sample:end_sample].copy()


def normalize_audio(
    audio: np.ndarray,
    target_db: float = -3.0,
) -> np.ndarray:
    """Peak-normalize audio to a target dB level.

    The signal is scaled so that its peak amplitude matches *target_db* dBFS.
    If the signal is silent (peak below ``1e-8``), it is returned unchanged.

    Args:
        audio: 1-D float32 audio array.
        target_db: Target peak level in dB relative to full scale.
                   Default is -3.0 dBFS, leaving headroom for downstream
                   processing.

    Returns:
        A normalized copy of the audio array.
    """
    peak = np.max(np.abs(audio))
    if peak < 1e-8:
        return audio.copy()

    target_linear = 10.0 ** (target_db / 20.0)
    gain = target_linear / peak

    normalized = audio * gain

    # Hard-clip as safety net (should not be needed if target_db < 0)
    return np.clip(normalized, -1.0, 1.0).astype(np.float32)


def apply_fade(
    audio: np.ndarray,
    sr: int,
    fade_in: float = 0.01,
    fade_out: float = 0.01,
) -> np.ndarray:
    """Apply fade-in and fade-out to an audio array to prevent clicks.

    Args:
        audio: 1-D float32 audio array.
        sr: Sample rate.
        fade_in: Fade-in duration in seconds.
        fade_out: Fade-out duration in seconds.

    Returns:
        A copy of the audio with fades applied.
    """
    audio = audio.copy()
    length = len(audio)

    fade_in_samples = min(int(fade_in * sr), length // 2)
    fade_out_samples = min(int(fade_out * sr), length // 2)

    if fade_in_samples > 0:
        fade_in_curve = np.linspace(0.0, 1.0, fade_in_samples, dtype=np.float32)
        audio[:fade_in_samples] *= fade_in_curve

    if fade_out_samples > 0:
        fade_out_curve = np.linspace(1.0, 0.0, fade_out_samples, dtype=np.float32)
        audio[-fade_out_samples:] *= fade_out_curve

    return audio


# ---------------------------------------------------------------------------
# Signal analysis
# ---------------------------------------------------------------------------


def compute_rms(audio: np.ndarray) -> float:
    """Compute the root-mean-square energy of an audio signal.

    Args:
        audio: 1-D audio array.

    Returns:
        RMS value as a float.  Returns ``0.0`` for empty arrays.
    """
    if len(audio) == 0:
        return 0.0
    return float(np.sqrt(np.mean(audio.astype(np.float64) ** 2)))


def detect_silence(
    audio: np.ndarray,
    sr: int,
    threshold_db: float = -40.0,
    min_duration: float = 0.1,
) -> list[tuple[float, float]]:
    """Detect contiguous silent regions in an audio signal.

    A region is considered "silent" when its frame-level RMS energy stays
    below *threshold_db* for at least *min_duration* seconds.  Analysis is
    performed in non-overlapping frames of 10 ms.

    Args:
        audio: 1-D audio array.
        sr: Sample rate.
        threshold_db: Silence threshold in dBFS (default -40 dB).
        min_duration: Minimum duration in seconds for a region to be
                      reported as silence.

    Returns:
        A list of ``(start_seconds, end_seconds)`` tuples for each detected
        silent region, sorted by start time.
    """
    if len(audio) == 0:
        return []

    threshold_linear = 10.0 ** (threshold_db / 20.0)
    frame_size = max(1, int(0.01 * sr))  # 10 ms frames
    min_frames = max(1, int(min_duration / 0.01))

    num_frames = len(audio) // frame_size
    if num_frames == 0:
        return []

    # Compute per-frame RMS
    trimmed = audio[: num_frames * frame_size]
    frames = trimmed.reshape(num_frames, frame_size)
    frame_rms = np.sqrt(np.mean(frames.astype(np.float64) ** 2, axis=1))

    # Find silent frames
    is_silent = frame_rms < threshold_linear

    # Group contiguous silent frames into regions
    silent_regions: list[tuple[float, float]] = []
    region_start: int | None = None

    for i, silent in enumerate(is_silent):
        if silent:
            if region_start is None:
                region_start = i
        else:
            if region_start is not None:
                region_length = i - region_start
                if region_length >= min_frames:
                    start_sec = region_start * frame_size / sr
                    end_sec = i * frame_size / sr
                    silent_regions.append((start_sec, end_sec))
                region_start = None

    # Handle trailing silence
    if region_start is not None:
        region_length = num_frames - region_start
        if region_length >= min_frames:
            start_sec = region_start * frame_size / sr
            end_sec = num_frames * frame_size / sr
            silent_regions.append((start_sec, end_sec))

    return silent_regions
