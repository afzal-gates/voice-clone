"""Singing voice synthesis engine using DiffSinger.

Provides high-quality singing synthesis from lyrics and melody using
DiffSinger diffusion models with phoneme-based control.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Optional

import numpy as np
import soundfile as sf
import torch

from app.config import settings
from app.pipeline.melody_parser import MelodyParser, PitchContour
from app.pipeline.phoneme_converter import PhonemeConverter
from app.pipeline.vocal_engine import VocalEngine

logger = logging.getLogger(__name__)


class SingingEngine:
    """DiffSinger-based singing voice synthesis engine.

    Supports:
    - Text-to-singing with voice cloning
    - MIDI melody input
    - Simple notation melody input
    - Auto-melody generation
    - Multiple singing voice models
    """

    def __init__(self) -> None:
        """Initialize the singing engine with lazy model loading."""
        self._model: object | None = None
        self._vocoder: object | None = None
        self._vocal_engine: VocalEngine | None = None
        self._device: str = "cuda" if torch.cuda.is_available() else "cpu"
        self._phoneme_converter = PhonemeConverter()
        self._melody_parser = MelodyParser()
        self._sample_rate: int = 24000  # XTTS/Qwen typical output rate

        logger.debug(
            "SingingEngine created (device=%s)", self._device
        )

    def _ensure_model(self, voice_model: str = "default") -> None:
        """Load the VocalEngine on first call.

        Args:
            voice_model: Voice model identifier to load (for future use).

        Raises:
            RuntimeError: If VocalEngine initialization fails.
        """
        if self._vocal_engine is not None:
            return

        logger.info(
            "Initializing VocalEngine (XTTS v2 + Qwen3 fallback) on %s",
            self._device
        )

        try:
            # Initialize the VocalEngine with dual TTS backend
            self._vocal_engine = VocalEngine()

            logger.info("VocalEngine initialized successfully")

        except Exception as exc:
            logger.error("Failed to initialize VocalEngine: %s", exc)
            raise RuntimeError(
                f"Cannot initialize VocalEngine: {exc}"
            ) from exc

    def _synthesize_core(
        self,
        phonemes: list[str],
        pitch_contour: PitchContour,
        voice_model: str,
        lyrics: str,
        vocal_type: str = "ai",
        language: str = "en",
    ) -> tuple[np.ndarray, int]:
        """Core singing synthesis using VocalEngine (XTTS v2 + Qwen3 fallback).

        This is a synchronous blocking operation that runs in a thread.

        Args:
            phonemes: Phoneme sequence for lyrics (currently unused, for future enhancement).
            pitch_contour: Pitch contour for melody.
            voice_model: Voice model identifier (for future use).
            lyrics: Original lyrics text.
            vocal_type: Voice type (male, female, choir, ai).
            language: Language code.

        Returns:
            Tuple of (audio_array, sample_rate).
        """
        self._ensure_model(voice_model)

        logger.info(
            "Synthesizing singing: lyrics=%d chars, %d notes, vocal_type=%s",
            len(lyrics),
            len(pitch_contour.notes),
            vocal_type,
        )

        # Use VocalEngine for synthesis
        audio, sr = self._vocal_engine.synthesize_singing(
            lyrics=lyrics,
            pitch_contour=pitch_contour,
            vocal_type=vocal_type,
            language=language,
        )

        return audio, sr

    def _generate_mock_singing(
        self, duration: float, pitch_contour: PitchContour
    ) -> np.ndarray:
        """Generate mock singing audio for testing without DiffSinger.

        Creates synthesized singing-like audio based on the pitch contour.

        Args:
            duration: Duration in seconds.
            pitch_contour: Pitch contour for melody.

        Returns:
            Audio array (mono, float32).
        """
        num_samples = int(duration * self._sample_rate)
        audio = np.zeros(num_samples, dtype=np.float32)

        # Generate simple singing synthesis from notes
        for note in pitch_contour.notes:
            start_sample = int(note.start_time * self._sample_rate)
            end_sample = int(
                (note.start_time + note.duration) * self._sample_rate
            )

            if start_sample >= num_samples:
                break

            end_sample = min(end_sample, num_samples)
            note_samples = end_sample - start_sample

            if note_samples <= 0:
                continue

            # Convert MIDI to frequency
            freq = 440.0 * (2.0 ** ((note.pitch - 69) / 12.0))

            # Generate note audio with vibrato
            t = np.linspace(0, note.duration, note_samples, dtype=np.float32)
            vibrato = 5.0 * np.sin(2 * np.pi * 5.0 * t)  # 5 Hz vibrato
            tone = np.sin(2 * np.pi * (freq + vibrato) * t)

            # Apply amplitude envelope (ADSR-like)
            envelope = np.ones(note_samples, dtype=np.float32)
            attack_samples = min(int(0.05 * self._sample_rate), note_samples // 4)
            release_samples = min(int(0.1 * self._sample_rate), note_samples // 4)

            # Attack
            if attack_samples > 0:
                envelope[:attack_samples] = np.linspace(0, 1, attack_samples)

            # Release
            if release_samples > 0:
                envelope[-release_samples:] = np.linspace(1, 0, release_samples)

            # Apply envelope and add to audio
            audio[start_sample:end_sample] += tone * envelope * 0.3

        # Normalize
        max_amp = np.abs(audio).max()
        if max_amp > 0:
            audio = audio / max_amp * 0.8

        logger.info("Mock singing audio generated: %.2fs", duration)

        return audio

    def _apply_tempo_adjustment(
        self, audio: np.ndarray, current_tempo: float, target_tempo: float
    ) -> np.ndarray:
        """Adjust audio tempo using time-stretching.

        Args:
            audio: Input audio array.
            current_tempo: Current tempo in BPM.
            target_tempo: Target tempo in BPM.

        Returns:
            Time-stretched audio array.
        """
        if abs(current_tempo - target_tempo) < 1.0:
            return audio

        stretch_ratio = current_tempo / target_tempo

        logger.info(
            "Adjusting tempo: %.1f -> %.1f BPM (ratio=%.3f)",
            current_tempo,
            target_tempo,
            stretch_ratio,
        )

        import librosa

        return librosa.effects.time_stretch(audio, rate=stretch_ratio)

    def _apply_key_shift(
        self, audio: np.ndarray, semitones: int, sr: int
    ) -> np.ndarray:
        """Shift audio pitch by semitones.

        Args:
            audio: Input audio array.
            semitones: Number of semitones to shift (-12 to +12).
            sr: Sample rate.

        Returns:
            Pitch-shifted audio array.
        """
        if semitones == 0:
            return audio

        logger.info("Shifting pitch by %d semitones", semitones)

        import librosa

        return librosa.effects.pitch_shift(
            audio, sr=sr, n_steps=semitones
        )

    async def synthesize(
        self,
        lyrics: str,
        melody: Optional[str | Path] = None,
        voice_model: str = "default",
        tempo: int = 120,
        key_shift: int = 0,
        output_path: Path = None,
        language: str = "en",
        vocal_type: str = "ai",
    ) -> Path:
        """Synthesize singing audio from lyrics and melody.

        This is the main public interface for singing synthesis.

        Args:
            lyrics: Song lyrics text.
            melody: MIDI file path, notation string, or None for auto-generation.
            voice_model: Singing voice model identifier.
            tempo: Tempo in BPM (60-200).
            key_shift: Pitch shift in semitones (-12 to +12).
            output_path: Path where audio will be saved.
            language: Language code for phoneme conversion.
            vocal_type: Voice type (male, female, choir, ai). Default: ai.

        Returns:
            Path to the generated audio file.

        Raises:
            ValueError: If lyrics are empty or invalid.
            RuntimeError: If synthesis fails.
        """
        if not lyrics or not lyrics.strip():
            raise ValueError("Lyrics cannot be empty")

        lyrics = lyrics.strip()
        tempo = max(60, min(200, tempo))
        key_shift = max(-12, min(12, key_shift))

        logger.info(
            "Synthesizing singing: %d chars, tempo=%d BPM, key_shift=%d",
            len(lyrics),
            tempo,
            key_shift,
        )

        # Step 1: Convert lyrics to phonemes
        logger.info("Converting lyrics to phonemes (language=%s)", language)
        phonemes = await asyncio.to_thread(
            self._phoneme_converter.text_to_phonemes, lyrics, language
        )

        # Step 2: Parse or generate melody
        if melody is None:
            # Auto-generate melody
            logger.info("Auto-generating melody from text")
            pitch_contour = await asyncio.to_thread(
                self._melody_parser.generate_simple_melody,
                lyrics,
                tempo,
            )
        elif isinstance(melody, Path) and melody.exists():
            # Parse MIDI file
            logger.info("Parsing MIDI file: %s", melody.name)
            pitch_contour = await asyncio.to_thread(
                self._melody_parser.parse_midi, melody, tempo
            )
        elif isinstance(melody, str):
            # Parse notation string
            logger.info("Parsing melody notation")
            pitch_contour = await asyncio.to_thread(
                self._melody_parser.parse_simple_notation,
                melody,
                tempo,
            )
        else:
            raise ValueError(
                f"Invalid melody input: {melody}. "
                "Must be MIDI path, notation string, or None"
            )

        # Step 3: Synthesize singing using VocalEngine
        audio, sr = await asyncio.to_thread(
            self._synthesize_core,
            phonemes,
            pitch_contour,
            voice_model,
            lyrics,
            vocal_type,
            language,
        )

        # Step 4: Apply key shift if requested
        if key_shift != 0:
            audio = await asyncio.to_thread(
                self._apply_key_shift, audio, key_shift, sr
            )

        # Step 5: Save output
        output_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(output_path), audio, sr)

        duration = len(audio) / sr
        logger.info(
            "Singing synthesis complete: %s (%.2fs)",
            output_path.name,
            duration,
        )

        return output_path

    def list_available_models(self) -> list[dict]:
        """List available singing voice models.

        Returns:
            List of model info dictionaries with 'model_id', 'name', 'language', etc.
        """
        # TODO: Implement actual model discovery
        # This would scan the models directory and return available voices

        models = [
            {
                "model_id": "default",
                "name": "Default Voice",
                "language": "en",
                "gender": "neutral",
                "description": "Default singing voice model",
            },
        ]

        logger.info("Available singing models: %d", len(models))

        return models
