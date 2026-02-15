"""Music generation engine using Meta's AudioCraft MusicGen.

Provides text-to-music generation with optional style conditioning and
reference audio support. The model is lazily loaded on first use to avoid
startup delays and unnecessary memory allocation.
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

logger = logging.getLogger(__name__)

# Style-to-prompt templates for enhanced genre conditioning
STYLE_PROMPTS = {
    "pop": "catchy pop music with upbeat melody and vocals",
    "rock": "energetic rock music with electric guitars and drums",
    "electronic": "electronic dance music with synthesizers and beats",
    "classical": "orchestral classical music with strings and piano",
    "jazz": "smooth jazz with piano, saxophone and bass",
    "ambient": "atmospheric ambient soundscape with soft textures",
    "hip-hop": "hip-hop beat with bass, drums and rhythm",
    "country": "country music with acoustic guitar and fiddle",
    "folk": "folk music with acoustic instruments and storytelling",
    "cinematic": "cinematic orchestral soundtrack with drama",
}


class MusicEngine:
    """Music generation engine with lazy model loading.

    Uses Meta's AudioCraft MusicGen for generating music from text prompts,
    with optional style conditioning and reference audio melody guidance.

    Typical usage::

        engine = MusicEngine()
        await engine.generate(
            prompt="upbeat electronic dance music",
            output_path=Path("output.wav"),
            duration=10.0,
            style="electronic",
        )
    """

    def __init__(self) -> None:
        """Initialize the music engine with lazy model loading."""
        self._model: object | None = None
        self._device: str = (
            "cuda"
            if torch.cuda.is_available() and settings.MUSICGEN_USE_GPU
            else "cpu"
        )
        self._sample_rate: int = 32000  # MusicGen native sample rate

        logger.debug(
            "MusicEngine created (device=%s, model=%s)",
            self._device,
            settings.MUSICGEN_MODEL,
        )

    def _ensure_model(self) -> None:
        """Load the MusicGen model on first call.

        Raises:
            RuntimeError: If the audiocraft package is not installed or
                          model loading fails.
        """
        # Skip model loading in mock mode
        if settings.MUSICGEN_MOCK_MODE:
            logger.info("MOCK MODE: Skipping MusicGen model loading")
            return

        if self._model is not None:
            return

        logger.info(
            "Loading MusicGen model: %s on %s",
            settings.MUSICGEN_MODEL,
            self._device,
        )

        try:
            from audiocraft.models import MusicGen

            self._model = MusicGen.get_pretrained(
                settings.MUSICGEN_MODEL, device=self._device
            )

            # Set generation parameters for high quality output
            self._model.set_generation_params(
                use_sampling=True,
                top_k=250,
                top_p=0.0,
                temperature=1.0,
                cfg_coef=3.0,
            )

            logger.info("MusicGen model loaded successfully")

        except ImportError as exc:
            raise RuntimeError(
                "audiocraft package not installed. Run: pip install audiocraft"
            ) from exc
        except Exception as exc:
            logger.error("Failed to load MusicGen model: %s", exc)
            raise RuntimeError(
                f"Cannot load MusicGen model '{settings.MUSICGEN_MODEL}': {exc}"
            ) from exc

    def _generate_mock_music(
        self,
        prompt: str,
        duration: float,
        style: str | None = None,
    ) -> tuple[np.ndarray, int]:
        """Generate mock procedural audio for testing without AudioCraft.

        Creates simple synthesized audio based on style parameters.

        Args:
            prompt: Text description (used for logging only in mock mode).
            duration: Length of audio to generate in seconds.
            style: Optional genre/style for audio characteristics.

        Returns:
            A tuple of (audio_array, sample_rate) where audio_array is
            a 1D numpy array of float32 samples.
        """
        logger.info(
            "MOCK MODE: Generating procedural audio: duration=%.1fs, style=%s",
            duration,
            style or "generic",
        )

        num_samples = int(duration * self._sample_rate)
        t = np.linspace(0, duration, num_samples, dtype=np.float32)

        # Style-specific frequency and modulation patterns
        style_params = {
            "electronic": (440, 880, 2.0),  # (base_freq, mod_freq, mod_depth)
            "pop": (523, 1046, 1.5),
            "rock": (329, 659, 3.0),
            "classical": (261, 523, 0.8),
            "jazz": (349, 698, 1.2),
            "ambient": (220, 440, 0.5),
            "hip-hop": (110, 220, 2.5),
            "country": (392, 784, 1.3),
            "folk": (293, 587, 1.0),
            "cinematic": (196, 392, 2.2),
        }

        base_freq, mod_freq, mod_depth = style_params.get(
            style.lower() if style else "generic", (440, 880, 1.5)
        )

        # Generate multi-layered tone with modulation
        audio = np.zeros(num_samples, dtype=np.float32)

        # Base tone
        audio += 0.3 * np.sin(2 * np.pi * base_freq * t)

        # Harmonic
        audio += 0.15 * np.sin(2 * np.pi * (base_freq * 1.5) * t)

        # Modulation (vibrato effect)
        modulation = mod_depth * np.sin(2 * np.pi * 4 * t)
        audio += 0.2 * np.sin(2 * np.pi * (base_freq + modulation) * t)

        # Add some rhythmic element (beat)
        beat_freq = 2.0  # 120 BPM
        beat = 0.25 * np.sin(2 * np.pi * beat_freq * t) * (
            np.sin(2 * np.pi * 80 * t) ** 2
        )
        audio += beat

        # Apply envelope (fade in/out)
        fade_samples = int(0.1 * self._sample_rate)  # 100ms fade
        fade_in = np.linspace(0, 1, fade_samples, dtype=np.float32)
        fade_out = np.linspace(1, 0, fade_samples, dtype=np.float32)

        audio[:fade_samples] *= fade_in
        audio[-fade_samples:] *= fade_out

        # Normalize to prevent clipping
        max_amp = np.abs(audio).max()
        if max_amp > 0:
            audio = audio / max_amp * 0.8  # Leave some headroom

        logger.info("MOCK MODE: Procedural audio generated: %.2fs", duration)

        return audio, self._sample_rate

    def _generate_music(
        self,
        prompt: str,
        duration: float,
        style: str | None = None,
        ref_audio_path: Path | None = None,
    ) -> tuple[np.ndarray, int]:
        """Synchronous music generation via MusicGen.

        This method runs in a worker thread via asyncio.to_thread().

        Args:
            prompt: Text description of the desired music.
            duration: Length of audio to generate in seconds.
            style: Optional genre/style for prompt enhancement.
            ref_audio_path: Optional reference audio for melody conditioning.

        Returns:
            A tuple of (audio_array, sample_rate) where audio_array is
            a 1D numpy array of float32 samples.
        """
        # Use mock mode if enabled
        if settings.MUSICGEN_MOCK_MODE:
            return self._generate_mock_music(prompt, duration, style)

        self._ensure_model()

        # Enhance prompt with style template if provided
        enhanced_prompt = prompt
        if style and style.lower() in STYLE_PROMPTS:
            style_template = STYLE_PROMPTS[style.lower()]
            enhanced_prompt = f"{style_template}, {prompt}"

        logger.info(
            "MusicGen generating: duration=%.1fs, style=%s, prompt='%s'",
            duration,
            style or "none",
            enhanced_prompt[:50],
        )

        # Update model duration parameter
        self._model.set_generation_params(duration=duration)

        # Generate with or without melody conditioning
        if ref_audio_path and ref_audio_path.exists():
            logger.info(
                "Using reference audio for conditioning: %s", ref_audio_path.name
            )

            # Load and preprocess reference audio
            ref_audio, ref_sr = sf.read(str(ref_audio_path), dtype="float32")

            # Resample to MusicGen's native rate if needed
            if ref_sr != self._sample_rate:
                import librosa

                ref_audio = librosa.resample(
                    ref_audio, orig_sr=ref_sr, target_sr=self._sample_rate
                )

            # Ensure correct shape (channels, samples)
            if ref_audio.ndim == 1:
                ref_audio = ref_audio[np.newaxis, :]
            elif ref_audio.ndim == 2:
                ref_audio = ref_audio.T

            # Convert to tensor and move to device
            ref_tensor = torch.from_numpy(ref_audio).to(self._device)

            # Generate with melody conditioning
            with torch.no_grad():
                output = self._model.generate_with_chroma(
                    descriptions=[enhanced_prompt],
                    melody_wavs=ref_tensor.unsqueeze(0),
                    melody_sample_rate=self._sample_rate,
                    progress=False,
                )
        else:
            # Generate without conditioning
            with torch.no_grad():
                output = self._model.generate(
                    descriptions=[enhanced_prompt], progress=False
                )

        # Extract audio from model output
        audio = output[0].cpu().float().numpy()

        # Ensure mono output (channels, samples) → (samples,)
        if audio.ndim == 2:
            audio = audio.T
            if audio.shape[1] == 2:
                # Stereo → mono (average channels)
                audio = audio.mean(axis=1)

        # Final cleanup: ensure 1D float32 array
        audio = np.asarray(audio, dtype=np.float32).squeeze()

        actual_duration = len(audio) / self._sample_rate
        logger.info("Music generation complete: %.2fs", actual_duration)

        return audio, self._sample_rate

    async def generate(
        self,
        prompt: str,
        output_path: Path,
        duration: float = 10.0,
        style: str | None = None,
        ref_audio_path: Path | None = None,
    ) -> Path:
        """Generate music from a text prompt.

        This is the main public interface for music generation. It delegates
        the blocking model inference to a worker thread to avoid blocking
        the event loop.

        Args:
            prompt: Text description of the desired music.
            output_path: Path where the generated audio will be saved.
            duration: Length of audio to generate in seconds (5-30s).
            style: Optional genre/style preset for enhanced generation.
            ref_audio_path: Optional reference audio for melody conditioning.

        Returns:
            The output_path where the audio was saved.

        Raises:
            RuntimeError: If model loading or generation fails.
        """
        # Clamp duration to configured maximum
        duration = max(5.0, min(settings.MUSICGEN_MAX_DURATION, duration))

        logger.info(
            "Generating music: prompt='%s...', duration=%.1fs, style=%s",
            prompt[:30],
            duration,
            style or "none",
        )

        # Run blocking generation in worker thread
        audio, sr = await asyncio.to_thread(
            self._generate_music, prompt, duration, style, ref_audio_path
        )

        # Save to disk
        output_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(output_path), audio, sr)

        actual_duration = len(audio) / sr
        logger.info("Music saved: %s (%.2fs)", output_path.name, actual_duration)

        return output_path
