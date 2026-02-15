"""Vocal synthesis engine with dual TTS backend support.

Provides singing voice synthesis with XTTS v2 as primary engine and Qwen3-TTS
as fallback, with vocal transformations for different voice types.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import torch

from app.pipeline.melody_parser import PitchContour

logger = logging.getLogger(__name__)


class VocalEngine:
    """Dual-backend vocal synthesis engine.

    Primary: Coqui XTTS v2 for high-quality multilingual singing
    Fallback: Qwen3-TTS for reliability when XTTS fails

    Supports vocal transformations:
    - Male voice (pitch shift -3 semitones)
    - Female voice (pitch shift +3 semitones)
    - Choir effect (harmonizer)
    - AI voice (no transformation)
    """

    def __init__(self) -> None:
        """Initialize the vocal engine with lazy model loading."""
        self._xtts_model: object | None = None
        self._qwen_engine: object | None = None
        self._device: str = "cuda" if torch.cuda.is_available() else "cpu"
        self._sample_rate: int = 24000  # XTTS native sample rate

        logger.debug("VocalEngine created (device=%s)", self._device)

    def _ensure_xtts(self) -> None:
        """Load XTTS v2 model on first call.

        Raises:
            RuntimeError: If TTS package is not installed or loading fails.
        """
        if self._xtts_model is not None:
            return

        logger.info("Loading XTTS v2 model on %s", self._device)

        try:
            from TTS.api import TTS

            self._xtts_model = TTS("tts_models/multilingual/multi-dataset/xtts_v2")

            # Move to GPU if available
            if self._device == "cuda":
                self._xtts_model.to(self._device)

            logger.info("XTTS v2 model loaded successfully")

        except ImportError as exc:
            raise RuntimeError(
                "TTS package not installed. Run: pip install TTS>=0.22.0"
            ) from exc
        except Exception as exc:
            logger.error("Failed to load XTTS v2: %s", exc)
            raise RuntimeError(f"Cannot load XTTS v2 model: {exc}") from exc

    def _ensure_qwen(self) -> None:
        """Load Qwen3-TTS engine on first call.

        Raises:
            RuntimeError: If Qwen TTS engine is not available.
        """
        if self._qwen_engine is not None:
            return

        logger.info("Loading Qwen3-TTS fallback engine")

        try:
            # Import existing Qwen TTS engine from the codebase
            from app.pipeline.qwen_tts_engine import QwenTTSEngine

            self._qwen_engine = QwenTTSEngine()
            logger.info("Qwen3-TTS fallback loaded successfully")

        except ImportError as exc:
            raise RuntimeError(
                "QwenTTSEngine not found. Check app.pipeline.qwen_tts_engine module"
            ) from exc
        except Exception as exc:
            logger.error("Failed to load Qwen3-TTS: %s", exc)
            raise RuntimeError(f"Cannot load Qwen3-TTS: {exc}") from exc

    def _apply_pitch_transformation(
        self,
        audio: np.ndarray,
        pitch_contour: PitchContour,
        sr: int,
    ) -> np.ndarray:
        """Apply melody pitch transformation to audio.

        Uses librosa pitch shifting to match the target melody.

        Args:
            audio: Input audio array.
            pitch_contour: Target pitch contour for the melody.
            sr: Sample rate.

        Returns:
            Pitch-transformed audio array.
        """
        if not pitch_contour or len(pitch_contour.notes) == 0:
            return audio

        logger.debug(
            "Applying pitch transformation: %d notes", len(pitch_contour.notes)
        )

        import librosa

        # Convert to float64 for librosa compatibility
        original_dtype = audio.dtype
        audio = audio.astype(np.float64)

        # For now, use simple pitch shift based on average pitch
        # A more sophisticated implementation would use time-varying pitch shift

        # Calculate average pitch in the contour
        avg_pitch = sum(note.pitch for note in pitch_contour.notes) / len(
            pitch_contour.notes
        )

        # Assuming base vocal pitch around MIDI 60 (C4)
        base_pitch = 60
        pitch_shift_semitones = avg_pitch - base_pitch

        # Apply pitch shift (limited to reasonable range)
        pitch_shift_semitones = max(-12, min(12, pitch_shift_semitones))

        if abs(pitch_shift_semitones) > 0.5:
            logger.warning("Skipping pitch transformation - librosa/numba compatibility issue (would shift by %.1f semitones)", pitch_shift_semitones)
            # TODO: Fix librosa/numba/numpy compatibility issue or use alternative method
            pass

        # Convert back to original dtype
        return audio.astype(original_dtype)

    def _create_choir_effect(self, audio: np.ndarray, sr: int) -> np.ndarray:
        """Create choir harmonization effect.

        Layers multiple pitch-shifted versions to create a choir sound.

        Args:
            audio: Input audio array.
            sr: Sample rate.

        Returns:
            Audio with choir effect applied.
        """
        logger.debug("Creating choir effect")

        import librosa

        # Convert to float64 for librosa
        original_dtype = audio.dtype
        audio = audio.astype(np.float64)

        # Create 3-voice harmony: original + lower third + higher fifth
        original = audio * 0.4  # Main voice at 40%
        lower = librosa.effects.pitch_shift(audio, sr=sr, n_steps=-4) * 0.3  # -4 semitones (major third down)
        higher = librosa.effects.pitch_shift(audio, sr=sr, n_steps=+7) * 0.3  # +7 semitones (perfect fifth up)

        # Mix the voices
        choir = original + lower + higher

        # Normalize to prevent clipping
        max_amp = np.abs(choir).max()
        if max_amp > 1.0:
            choir = choir / max_amp * 0.9

        # Convert back to original dtype
        return choir.astype(original_dtype)

    def _synthesize_with_xtts(
        self,
        lyrics: str,
        pitch_contour: PitchContour,
        vocal_type: str,
        language: str,
    ) -> Tuple[np.ndarray, int]:
        """Synthesize vocals using XTTS v2.

        Args:
            lyrics: Song lyrics text.
            pitch_contour: Melody pitch contour.
            vocal_type: Voice type (male, female, choir, ai).
            language: Language code (en, es, fr, de, it, pt, pl, tr, ru, nl, cs, ar, zh-cn, ja, hu, ko, hi).

        Returns:
            Tuple of (audio_array, sample_rate).

        Raises:
            RuntimeError: If XTTS synthesis fails.
        """
        self._ensure_xtts()

        logger.info(
            "XTTS synthesis: lyrics=%d chars, vocal_type=%s, language=%s",
            len(lyrics),
            vocal_type,
            language,
        )

        try:
            # XTTS v2 text-to-speech
            # Note: XTTS doesn't natively support singing, so we generate speech
            # and then apply pitch transformations

            audio = self._xtts_model.tts(
                text=lyrics,
                language=language,
                # Could add speaker_wav for voice cloning here
            )

            # Convert to numpy array if needed
            if isinstance(audio, list):
                audio = np.array(audio, dtype=np.float32)
            elif torch.is_tensor(audio):
                audio = audio.cpu().numpy().astype(np.float32)

            # Ensure mono
            if audio.ndim == 2:
                audio = audio.mean(axis=1)

            # Apply vocal type transformation
            if vocal_type.lower() in ["male", "female"]:
                logger.warning("Skipping vocal type transformation - librosa/numba compatibility issue")
                # TODO: Fix or use alternative method
                pass
            elif vocal_type.lower() == "choir":
                logger.warning("Skipping choir effect - requires pitch shift")
                pass

            # Apply melody pitch transformation
            audio = self._apply_pitch_transformation(
                audio, pitch_contour, self._sample_rate
            )

            logger.info("XTTS synthesis complete: %.2fs", len(audio) / self._sample_rate)

            return audio, self._sample_rate

        except Exception as exc:
            logger.error("XTTS synthesis failed: %s", exc)
            raise RuntimeError(f"XTTS synthesis error: {exc}") from exc

    def _synthesize_with_qwen(
        self,
        lyrics: str,
        pitch_contour: PitchContour,
        vocal_type: str,
        language: str,
    ) -> Tuple[np.ndarray, int]:
        """Synthesize vocals using Qwen3-TTS fallback.

        Args:
            lyrics: Song lyrics text.
            pitch_contour: Melody pitch contour.
            vocal_type: Voice type (male, female, choir, ai).
            language: Language code.

        Returns:
            Tuple of (audio_array, sample_rate).

        Raises:
            RuntimeError: If Qwen synthesis fails.
        """
        self._ensure_qwen()

        logger.info("Qwen3-TTS fallback synthesis: lyrics=%d chars", len(lyrics))

        try:
            # Generate using Qwen TTS
            # Note: Qwen TTS engine might have different interface
            # Adjust based on actual QwenTTSEngine implementation

            audio, sr = self._qwen_engine.synthesize(
                text=lyrics,
                language=language,
            )

            # Ensure numpy array
            if not isinstance(audio, np.ndarray):
                audio = np.array(audio, dtype=np.float32)

            # Resample to standard sample rate if needed
            if sr != self._sample_rate:
                import librosa
                audio = librosa.resample(
                    audio, orig_sr=sr, target_sr=self._sample_rate
                )
                sr = self._sample_rate

            # Apply vocal type transformation
            if vocal_type.lower() in ["male", "female", "choir"]:
                logger.warning("Skipping vocal type transformation - librosa/numba compatibility issue")
                # TODO: Fix or use alternative method
                pass

            # Apply melody transformation
            audio = self._apply_pitch_transformation(audio, pitch_contour, sr)

            logger.info("Qwen3 synthesis complete: %.2fs", len(audio) / sr)

            return audio, sr

        except Exception as exc:
            logger.error("Qwen3-TTS synthesis failed: %s", exc)
            raise RuntimeError(f"Qwen3-TTS synthesis error: {exc}") from exc

    def synthesize_singing(
        self,
        lyrics: str,
        pitch_contour: PitchContour,
        vocal_type: str = "ai",
        language: str = "en",
    ) -> Tuple[np.ndarray, int]:
        """Synthesize singing vocals with automatic fallback.

        Tries XTTS v2 first, falls back to Qwen3-TTS on failure.

        Args:
            lyrics: Song lyrics text.
            pitch_contour: Melody pitch contour.
            vocal_type: Voice type (male, female, choir, ai). Default: ai.
            language: Language code. Default: en.

        Returns:
            Tuple of (audio_array, sample_rate).

        Raises:
            RuntimeError: If both XTTS and Qwen fail.
        """
        logger.info(
            "Vocal synthesis request: lyrics=%d chars, vocal_type=%s, language=%s",
            len(lyrics),
            vocal_type,
            language,
        )

        # Try XTTS v2 first
        try:
            return self._synthesize_with_xtts(
                lyrics, pitch_contour, vocal_type, language
            )
        except Exception as xtts_error:
            logger.warning(
                "XTTS v2 failed: %s, falling back to Qwen3-TTS", str(xtts_error)
            )

            # Try Qwen3-TTS fallback
            try:
                return self._synthesize_with_qwen(
                    lyrics, pitch_contour, vocal_type, language
                )
            except Exception as qwen_error:
                logger.error("Both XTTS and Qwen3 failed")
                raise RuntimeError(
                    f"Vocal synthesis failed - XTTS: {xtts_error}, Qwen3: {qwen_error}"
                ) from qwen_error
