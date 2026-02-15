"""Qwen TTS Engine wrapper for vocal synthesis.

Provides a simplified interface to the main TTSEngine's Qwen3-TTS functionality
for use in the vocal synthesis pipeline.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import soundfile as sf

from app.pipeline.tts_engine import TTSEngine

logger = logging.getLogger(__name__)


class QwenTTSEngine:
    """Wrapper for Qwen3-TTS functionality from TTSEngine.

    Provides a synchronous interface for singing vocal synthesis with
    optional reference audio support.
    """

    def __init__(self) -> None:
        """Initialize the Qwen TTS engine wrapper."""
        self._tts_engine = TTSEngine()
        logger.debug("QwenTTSEngine wrapper initialized")

    def _create_default_reference(self) -> Path:
        """Create a simple default reference audio file.

        Generates a neutral voice sample for Qwen3-TTS when no reference is provided.

        Returns:
            Path to the generated reference audio file.
        """
        logger.info("Creating default reference audio for Qwen3-TTS")

        # Create a simple sine wave as placeholder reference
        # This will produce a synthetic voice, but allows synthesis to work
        import tempfile

        sample_rate = 24000
        duration = 3.0  # 3 seconds
        frequency = 200  # 200 Hz (low male-ish voice)

        # Generate time array
        t = np.linspace(0, duration, int(sample_rate * duration))

        # Generate sine wave with amplitude envelope
        audio = np.sin(2 * np.pi * frequency * t)

        # Apply fade in/out envelope to make it smoother
        fade_samples = int(0.1 * sample_rate)  # 0.1 second fade
        fade_in = np.linspace(0, 1, fade_samples)
        fade_out = np.linspace(1, 0, fade_samples)

        audio[:fade_samples] *= fade_in
        audio[-fade_samples:] *= fade_out

        # Normalize
        audio = audio * 0.3  # Reduce amplitude to 30%

        # Save to temp file
        tmp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp_path = Path(tmp_file.name)
        tmp_file.close()

        sf.write(str(tmp_path), audio.astype(np.float32), sample_rate)

        logger.info("Default reference audio created: %s", tmp_path)
        return tmp_path

    def synthesize(
        self,
        text: str,
        language: str = "en",
        reference_audio: Optional[Path] = None,
        ref_text: Optional[str] = None,
    ) -> Tuple[np.ndarray, int]:
        """Synthesize speech using Qwen3-TTS.

        Args:
            text: Text to synthesize.
            language: Language code (e.g., "en", "zh", "ja").
            reference_audio: Optional path to reference voice for cloning.
                            If None, a default reference will be generated.
            ref_text: Optional transcript of reference audio.

        Returns:
            Tuple of (audio_array, sample_rate).

        Raises:
            RuntimeError: If synthesis fails.
        """
        # Generate default reference if none provided
        temp_ref_created = False
        if reference_audio is None:
            logger.warning("No reference audio provided, creating default reference")
            reference_audio = self._create_default_reference()
            temp_ref_created = True
            ref_text = "Hello, this is a test."  # Default reference text

        logger.info(
            "Qwen synthesis: text=%d chars, language=%s, ref_audio=%s",
            len(text),
            language,
            reference_audio.name if reference_audio else "none"
        )

        try:
            # Create temporary output file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                tmp_path = Path(tmp_file.name)

            try:
                # Use synchronous synthesis (since we're in vocal_engine._synthesize_with_qwen)
                import asyncio

                # Map short language codes to full names if needed
                lang_map = {
                    "en": "English",
                    "zh": "Chinese",
                    "ja": "Japanese",
                    "ko": "Korean",
                    "es": "Spanish",
                    "fr": "French",
                    "de": "German",
                    "it": "Italian",
                    "pt": "Portuguese",
                    "ru": "Russian",
                }
                full_language = lang_map.get(language.lower(), language)

                # Run async synthesis in sync context
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(
                        self._tts_engine.synthesize(
                            text=text,
                            output_path=tmp_path,
                            reference_audio=reference_audio,
                            language=full_language,
                            tts_model="qwen3-tts",
                            ref_text=ref_text,
                        )
                    )
                finally:
                    loop.close()

                # Read back the generated audio
                audio, sr = sf.read(str(tmp_path), dtype="float32")

                # Ensure mono
                if audio.ndim == 2:
                    audio = audio.mean(axis=1)

                logger.info("Qwen synthesis complete: %.2fs at %d Hz", len(audio) / sr, sr)

                return audio.astype(np.float32), sr

            finally:
                # Clean up temp file
                if tmp_path.exists():
                    tmp_path.unlink()
                # Clean up temp reference if we created it
                if temp_ref_created and reference_audio and reference_audio.exists():
                    reference_audio.unlink()

        except Exception as exc:
            logger.error("Qwen synthesis failed: %s", exc)
            # Clean up temp reference on error
            if temp_ref_created and reference_audio and reference_audio.exists():
                try:
                    reference_audio.unlink()
                except:
                    pass
            raise RuntimeError(f"Qwen3-TTS synthesis error: {exc}") from exc
