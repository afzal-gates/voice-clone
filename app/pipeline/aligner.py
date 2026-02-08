"""Time-alignment of synthesized speech segments to original timing.

Provides utilities to stretch, pad, trim, and crossfade generated speech
segments so they occupy exactly the same time-slots as the original audio.
This ensures lip-sync accuracy and seamless integration with the background
music track during the merge stage.
"""

import asyncio
import logging
from pathlib import Path

import numpy as np
import soundfile as sf

from app.config import settings

logger = logging.getLogger(__name__)


class AudioAligner:
    """Align synthesized speech segments to match original segment timing.

    All public methods are ``async`` and delegate blocking audio I/O and DSP
    operations to a thread pool so the event loop is never blocked.
    """

    # Stretch ratio bounds -- beyond these the audio quality degrades
    # unacceptably, so we pad/trim instead.
    _MIN_STRETCH: float = 0.5
    _MAX_STRETCH: float = 2.5

    # Duration tolerance in seconds: segments within this margin are
    # considered "close enough" and are not re-processed.
    _DURATION_TOLERANCE: float = 0.05

    # Default fade duration (seconds) used to prevent clicks when
    # padding or trimming.
    _FADE_DURATION: float = 0.01

    # ------------------------------------------------------------------
    # Public: single-segment alignment
    # ------------------------------------------------------------------

    async def align_segment(
        self,
        audio_path: Path,
        target_duration: float,
        output_path: Path,
    ) -> Path:
        """Time-align a single audio file to *target_duration* seconds.

        The method reads the audio, compares its duration to *target_duration*,
        and -- if the difference exceeds ``_DURATION_TOLERANCE`` -- applies one
        of the following:

        * **Time-stretch** via ``librosa.effects.time_stretch`` when the
          required ratio falls within ``[0.5, 2.5]``.
        * **Pad with silence** when the audio is too short and the stretch
          ratio would be below the lower bound.
        * **Truncate** (with a short fade-out) when the audio is too long
          and the stretch ratio would exceed the upper bound.

        Args:
            audio_path: Path to the source WAV file.
            target_duration: Desired duration in seconds.
            output_path: Destination path for the aligned WAV file.

        Returns:
            *output_path* after writing the aligned audio.

        Raises:
            FileNotFoundError: If *audio_path* does not exist.
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        audio, sr = await asyncio.to_thread(sf.read, str(audio_path), "float32")
        if audio.ndim > 1:
            audio = audio.mean(axis=1)

        actual_duration = len(audio) / sr
        target_samples = int(target_duration * sr)

        if abs(actual_duration - target_duration) <= self._DURATION_TOLERANCE:
            # Close enough -- just ensure exact sample count
            audio = self.pad_or_trim(audio, target_samples, sr)
        else:
            stretch_ratio = actual_duration / target_duration

            if self._MIN_STRETCH <= stretch_ratio <= self._MAX_STRETCH:
                audio = await asyncio.to_thread(
                    self._time_stretch, audio, stretch_ratio,
                )
                # After stretching, enforce exact sample count
                audio = self.pad_or_trim(audio, target_samples, sr)
                logger.debug(
                    "Stretched %s: %.3fs -> %.3fs (ratio=%.3f)",
                    audio_path.name,
                    actual_duration,
                    target_duration,
                    stretch_ratio,
                )
            else:
                # Ratio outside safe bounds -- fall back to pad/trim
                audio = self.pad_or_trim(audio, target_samples, sr)
                logger.warning(
                    "Stretch ratio %.3f out of bounds [%.1f, %.1f] for %s; "
                    "falling back to pad/trim (%.3fs -> %.3fs)",
                    stretch_ratio,
                    self._MIN_STRETCH,
                    self._MAX_STRETCH,
                    audio_path.name,
                    actual_duration,
                    target_duration,
                )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(output_path), audio, sr)
        logger.info("Aligned segment saved: %s (%.3fs)", output_path.name, target_duration)
        return output_path

    # ------------------------------------------------------------------
    # Public: batch alignment
    # ------------------------------------------------------------------

    async def align_all_segments(
        self,
        segments: list[dict],
        output_dir: Path,
    ) -> list[dict]:
        """Align a batch of speech segments to their target timings.

        Each dictionary in *segments* must contain:

        * ``audio_path`` (``Path``) -- source WAV file.
        * ``target_start`` (``float``) -- desired start time in seconds.
        * ``target_end`` (``float``) -- desired end time in seconds.
        * ``speaker_id`` (``str``) -- speaker identifier (used for filenames).

        After alignment, each dictionary is updated in-place with an
        ``aligned_path`` key pointing to the aligned WAV file in *output_dir*.

        Args:
            segments: List of segment dictionaries.
            output_dir: Directory where aligned files are written.

        Returns:
            The same *segments* list with ``aligned_path`` added to each item.
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        for idx, seg in enumerate(segments):
            audio_path = Path(seg["audio_path"])
            target_start: float = seg["target_start"]
            target_end: float = seg["target_end"]
            speaker_id: str = seg.get("speaker_id", "unknown")
            target_duration = target_end - target_start

            if target_duration <= 0:
                logger.warning(
                    "Segment %d (%s) has non-positive duration (%.3f); skipping",
                    idx, speaker_id, target_duration,
                )
                seg["aligned_path"] = audio_path
                continue

            aligned_name = f"aligned_{speaker_id}_{idx:04d}.wav"
            aligned_path = output_dir / aligned_name

            try:
                await self.align_segment(audio_path, target_duration, aligned_path)
                seg["aligned_path"] = aligned_path
            except Exception as exc:
                logger.error(
                    "Failed to align segment %d (%s): %s",
                    idx, speaker_id, exc,
                )
                # Fall back to unaligned audio so the pipeline can continue
                seg["aligned_path"] = audio_path

        logger.info("Aligned %d segments into %s", len(segments), output_dir)
        return segments

    # ------------------------------------------------------------------
    # Public: pad / trim
    # ------------------------------------------------------------------

    def pad_or_trim(
        self,
        audio: np.ndarray,
        target_length: int,
        sr: int,
    ) -> np.ndarray:
        """Pad with silence or truncate *audio* to exactly *target_length* samples.

        When truncating, a short fade-out is applied at the cut point to
        prevent audible clicks.  When padding, silence (zeros) is appended.

        Args:
            audio: 1-D float32 audio array.
            target_length: Desired number of samples.
            sr: Sample rate (used to compute fade duration).

        Returns:
            A new 1-D float32 array of exactly *target_length* samples.
        """
        current_length = len(audio)

        if current_length == target_length:
            return audio

        if current_length > target_length:
            # Truncate with fade-out at cut point
            trimmed = audio[:target_length].copy()
            fade_samples = min(int(self._FADE_DURATION * sr), target_length)
            if fade_samples > 0:
                fade_curve = np.linspace(1.0, 0.0, fade_samples, dtype=np.float32)
                trimmed[-fade_samples:] *= fade_curve
            return trimmed

        # Pad with silence
        padding = np.zeros(target_length - current_length, dtype=np.float32)
        return np.concatenate([audio, padding])

    # ------------------------------------------------------------------
    # Public: crossfade
    # ------------------------------------------------------------------

    def apply_crossfade(
        self,
        audio1: np.ndarray,
        audio2: np.ndarray,
        fade_duration: float,
        sr: int,
    ) -> np.ndarray:
        """Crossfade between two contiguous audio arrays.

        The last *fade_duration* seconds of *audio1* are linearly blended with
        the first *fade_duration* seconds of *audio2* to create a smooth
        transition.  The resulting array is shorter than the simple
        concatenation by exactly ``fade_samples`` samples.

        Args:
            audio1: First audio segment (1-D float32).
            audio2: Second audio segment (1-D float32).
            fade_duration: Duration of the crossfade region in seconds.
            sr: Sample rate.

        Returns:
            A new 1-D float32 array with the two segments joined by a
            crossfade.
        """
        fade_samples = int(fade_duration * sr)
        fade_samples = min(fade_samples, len(audio1), len(audio2))

        if fade_samples <= 0:
            return np.concatenate([audio1, audio2])

        # Build linear fade curves
        fade_out = np.linspace(1.0, 0.0, fade_samples, dtype=np.float32)
        fade_in = np.linspace(0.0, 1.0, fade_samples, dtype=np.float32)

        # Overlap region
        overlap = audio1[-fade_samples:] * fade_out + audio2[:fade_samples] * fade_in

        # Assemble: non-overlap head + overlap + non-overlap tail
        result = np.concatenate([
            audio1[:-fade_samples],
            overlap,
            audio2[fade_samples:],
        ])
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _time_stretch(audio: np.ndarray, rate: float) -> np.ndarray:
        """Wrapper around ``librosa.effects.time_stretch`` for thread dispatch."""
        import librosa  # noqa: WPS433 -- deferred import for optional dep
        return librosa.effects.time_stretch(audio, rate=rate)
