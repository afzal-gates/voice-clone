"""Audio mixing engine for combining TTS narration with background music.

Provides intelligent audio mixing capabilities for blending text-to-speech
generated voice with instrumental background music. Supports volume control,
timing offsets, crossfade effects, and automatic resampling.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import numpy as np
import soundfile as sf

from app.config import settings

logger = logging.getLogger(__name__)


class AudioMixer:
    """Audio mixer for combining TTS narration with background music.

    Lazily loads audio files on demand and provides mixing capabilities
    with adjustable volume levels, timing offsets, and fade effects.

    All public methods are async. CPU-bound DSP work runs on a thread
    via asyncio.to_thread to avoid blocking the event loop.

    Typical usage::

        mixer = AudioMixer()
        await mixer.mix(
            tts_audio_path=Path("narration.wav"),
            music_audio_path=Path("background.wav"),
            output_path=Path("mixed.wav"),
            tts_volume=0.9,
            music_volume=0.3,
            music_delay=1.0,
        )
    """

    # Default mixing parameters
    _DEFAULT_TTS_VOLUME: float = 0.85
    _DEFAULT_MUSIC_VOLUME: float = 0.30
    _DEFAULT_MUSIC_DELAY: float = 0.0
    _CROSSFADE_DURATION: float = 0.5  # seconds
    _NORMALIZATION_HEADROOM_DB: float = -1.0

    def __init__(self) -> None:
        """Initialize the audio mixer."""
        self._sample_rate: int = settings.SAMPLE_RATE
        logger.debug("AudioMixer created (sample_rate=%d)", self._sample_rate)

    async def mix(
        self,
        tts_audio_path: Path,
        music_audio_path: Path,
        output_path: Path,
        tts_volume: float = _DEFAULT_TTS_VOLUME,
        music_volume: float = _DEFAULT_MUSIC_VOLUME,
        music_delay: float = _DEFAULT_MUSIC_DELAY,
    ) -> Path:
        """Mix TTS audio with background music.

        Algorithm overview:

        1. Load TTS audio and resample to target sample rate if needed.
        2. Load music audio and resample to target sample rate if needed.
        3. Apply timing offset to music (delay music start).
        4. Extend or trim music to match TTS duration.
        5. Apply volume adjustments to both tracks.
        6. Apply crossfade at music start/end boundaries.
        7. Mix: output = (tts * tts_volume) + (music * music_volume).
        8. Normalize to prevent clipping.
        9. Write result as WAV.

        Args:
            tts_audio_path: Path to TTS narration audio file (WAV or MP3).
            music_audio_path: Path to background music audio file (WAV or MP3).
            output_path: Destination for mixed audio output.
            tts_volume: TTS volume level (0.0-1.0). Default: 0.85.
            music_volume: Music volume level (0.0-1.0). Default: 0.30.
            music_delay: Delay before music starts in seconds. Default: 0.0.

        Returns:
            output_path after writing the mixed audio.

        Raises:
            FileNotFoundError: If either input file does not exist.
            ValueError: If volume levels are out of range [0.0, 1.0].
        """
        # Validate inputs
        if not tts_audio_path.exists():
            raise FileNotFoundError(f"TTS audio file not found: {tts_audio_path}")
        if not music_audio_path.exists():
            raise FileNotFoundError(f"Music audio file not found: {music_audio_path}")

        if not 0.0 <= tts_volume <= 1.0:
            raise ValueError(
                f"TTS volume must be in range [0.0, 1.0], got: {tts_volume}"
            )
        if not 0.0 <= music_volume <= 1.0:
            raise ValueError(
                f"Music volume must be in range [0.0, 1.0], got: {music_volume}"
            )
        if music_delay < 0.0:
            raise ValueError(
                f"Music delay must be non-negative, got: {music_delay}"
            )

        logger.info(
            "Mixing audio: tts=%s, music=%s, tts_vol=%.2f, music_vol=%.2f, delay=%.2fs",
            tts_audio_path.name,
            music_audio_path.name,
            tts_volume,
            music_volume,
            music_delay,
        )

        # Run blocking mixing operation in worker thread
        mixed_audio = await asyncio.to_thread(
            self._mix_sync,
            tts_audio_path,
            music_audio_path,
            tts_volume,
            music_volume,
            music_delay,
        )

        # Save to disk
        output_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(output_path), mixed_audio, self._sample_rate)

        duration = len(mixed_audio) / self._sample_rate
        logger.info("Mixed audio saved: %s (%.2fs)", output_path.name, duration)

        return output_path

    def _mix_sync(
        self,
        tts_audio_path: Path,
        music_audio_path: Path,
        tts_volume: float,
        music_volume: float,
        music_delay: float,
    ) -> np.ndarray:
        """Synchronous implementation of the mixing algorithm.

        Args:
            tts_audio_path: Path to TTS audio file.
            music_audio_path: Path to music audio file.
            tts_volume: TTS volume multiplier (0.0-1.0).
            music_volume: Music volume multiplier (0.0-1.0).
            music_delay: Music start delay in seconds.

        Returns:
            1-D float32 array of mixed audio samples.
        """
        # 1. Load TTS audio
        tts_audio = self._load_audio(tts_audio_path, self._sample_rate)
        tts_duration = len(tts_audio) / self._sample_rate

        logger.debug(
            "Loaded TTS audio: %d samples (%.2fs)",
            len(tts_audio),
            tts_duration,
        )

        # 2. Load music audio
        music_audio = self._load_audio(music_audio_path, self._sample_rate)
        music_duration = len(music_audio) / self._sample_rate

        logger.debug(
            "Loaded music audio: %d samples (%.2fs)",
            len(music_audio),
            music_duration,
        )

        # 3. Calculate target duration (TTS duration + any music delay)
        target_duration = tts_duration
        target_samples = len(tts_audio)

        # 4. Apply music delay and fit to target duration
        delay_samples = int(music_delay * self._sample_rate)
        music_fitted = self._apply_delay_and_fit(
            music_audio, delay_samples, target_samples
        )

        # 5. Apply crossfade to music at start and end
        music_with_fade = self._apply_crossfade(
            music_fitted, delay_samples, self._sample_rate
        )

        # 6. Apply volume adjustments
        tts_adjusted = tts_audio * tts_volume
        music_adjusted = music_with_fade * music_volume

        # 7. Mix tracks
        mixed = tts_adjusted + music_adjusted

        # 8. Normalize to prevent clipping
        mixed = self._normalize(mixed, self._NORMALIZATION_HEADROOM_DB)

        logger.info(
            "Audio mixed successfully: %d samples (%.2fs)",
            len(mixed),
            len(mixed) / self._sample_rate,
        )

        return mixed

    @staticmethod
    def _load_audio(audio_path: Path, target_sr: int) -> np.ndarray:
        """Load audio file and convert to mono at target sample rate.

        Args:
            audio_path: Path to audio file (WAV or MP3).
            target_sr: Target sample rate for resampling.

        Returns:
            1-D float32 array of audio samples at target sample rate.
        """
        audio, file_sr = sf.read(str(audio_path), dtype="float32")

        # Convert stereo to mono if needed
        if audio.ndim > 1:
            audio = audio.mean(axis=1)

        # Resample if sample rate doesn't match
        if file_sr != target_sr:
            logger.debug(
                "Resampling audio from %d Hz to %d Hz",
                file_sr,
                target_sr,
            )
            import librosa

            audio = librosa.resample(audio, orig_sr=file_sr, target_sr=target_sr)

        return audio.astype(np.float32)

    @staticmethod
    def _apply_delay_and_fit(
        audio: np.ndarray,
        delay_samples: int,
        target_samples: int,
    ) -> np.ndarray:
        """Apply timing delay and fit audio to target length.

        Args:
            audio: Input audio samples.
            delay_samples: Number of samples to delay the start.
            target_samples: Target total length in samples.

        Returns:
            Audio with delay applied and fitted to target length.
        """
        if delay_samples <= 0:
            # No delay, just fit to target length
            if len(audio) >= target_samples:
                return audio[:target_samples]
            # Pad with silence
            padding = np.zeros(target_samples - len(audio), dtype=np.float32)
            return np.concatenate([audio, padding])

        # Apply delay: prepend silence
        silence_prefix = np.zeros(delay_samples, dtype=np.float32)
        delayed_audio = np.concatenate([silence_prefix, audio])

        # Fit to target length
        if len(delayed_audio) >= target_samples:
            return delayed_audio[:target_samples]

        # Pad with silence at the end
        padding = np.zeros(target_samples - len(delayed_audio), dtype=np.float32)
        return np.concatenate([delayed_audio, padding])

    def _apply_crossfade(
        self,
        audio: np.ndarray,
        start_offset: int,
        sr: int,
    ) -> np.ndarray:
        """Apply fade-in and fade-out to music track.

        Args:
            audio: Input audio samples.
            start_offset: Sample position where actual music begins (after silence).
            sr: Sample rate.

        Returns:
            Audio with crossfade effects applied.
        """
        audio = audio.copy()
        fade_samples = int(self._CROSSFADE_DURATION * sr)

        # Fade-in at start (after delay)
        if start_offset < len(audio):
            fade_end = min(start_offset + fade_samples, len(audio))
            fade_length = fade_end - start_offset

            if fade_length > 0:
                fade_in = np.linspace(0.0, 1.0, fade_length, dtype=np.float32)
                audio[start_offset:fade_end] *= fade_in

        # Fade-out at end
        if len(audio) > fade_samples:
            fade_out = np.linspace(1.0, 0.0, fade_samples, dtype=np.float32)
            audio[-fade_samples:] *= fade_out

        return audio

    @staticmethod
    def _normalize(audio: np.ndarray, target_db: float = -1.0) -> np.ndarray:
        """Peak-normalize audio to target dB level.

        Args:
            audio: Input audio samples.
            target_db: Target peak level in dB relative to full scale.

        Returns:
            Normalized audio. If signal is silent, returns unchanged.
        """
        peak = np.max(np.abs(audio))
        if peak < 1e-8:
            return audio

        target_linear = 10.0 ** (target_db / 20.0)
        gain = target_linear / peak
        return audio * gain
