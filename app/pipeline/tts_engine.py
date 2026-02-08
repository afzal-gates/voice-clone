"""Text-to-speech engine with voice cloning via Qwen3-TTS.

Uses the official ``qwen-tts`` package (``pip install qwen-tts``) which provides
``Qwen3TTSModel`` — the native interface for Qwen3-TTS voice cloning.

Model variants:
    - Qwen/Qwen3-TTS-12Hz-1.7B-Base  (1.7B params, best quality)
    - Qwen/Qwen3-TTS-12Hz-0.6B-Base  (0.6B params, faster/lighter)

Voice cloning requires a reference audio file.  Optionally, a transcript of the
reference audio (``ref_text``) improves cloning quality — when not provided the
engine falls back to x-vector-only mode.

See: https://github.com/QwenLM/Qwen3-TTS
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional

import numpy as np
import soundfile as sf
import torch

from app.config import settings

logger = logging.getLogger(__name__)


class TTSEngine:
    """Text-to-speech engine with voice cloning via Qwen3-TTS.

    The model is loaded lazily on first use.  Public methods are ``async`` and
    delegate blocking inference to ``asyncio.to_thread``.
    """

    def __init__(self) -> None:
        self._model: object | None = None
        self._device: str = "cuda" if torch.cuda.is_available() else "cpu"
        self._model_sr: int = 0  # populated after model loads
        logger.debug(
            "TTSEngine created (device=%s, model=%s)",
            self._device,
            settings.QWEN_TTS_MODEL,
        )

    # ------------------------------------------------------------------
    # Lazy model loading
    # ------------------------------------------------------------------

    def _ensure_model(self) -> None:
        """Load the Qwen3-TTS model on first call.

        Uses ``qwen_tts.Qwen3TTSModel.from_pretrained``.

        Raises:
            RuntimeError: If the model cannot be loaded.
        """
        if self._model is not None:
            return

        logger.info("Loading TTS model: %s on %s", settings.QWEN_TTS_MODEL, self._device)

        try:
            from qwen_tts import Qwen3TTSModel  # noqa: WPS433

            dtype = torch.bfloat16 if self._device == "cuda" else torch.float32

            # Build kwargs — only pass flash_attention_2 on CUDA
            load_kwargs: dict = {
                "device_map": f"{self._device}:0" if self._device == "cuda" else self._device,
                "dtype": dtype,
            }
            if self._device == "cuda":
                try:
                    import flash_attn  # noqa: F401, WPS433
                    load_kwargs["attn_implementation"] = "flash_attention_2"
                    logger.info("FlashAttention2 available — enabled")
                except ImportError:
                    logger.info("FlashAttention2 not installed — using default attention")

            self._model = Qwen3TTSModel.from_pretrained(
                settings.QWEN_TTS_MODEL,
                **load_kwargs,
            )

            self._model_sr = 24_000  # Qwen3-TTS outputs at 24 kHz
            logger.info("TTS model loaded successfully")

        except ImportError:
            raise RuntimeError(
                "qwen-tts package not installed. Run: pip install qwen-tts"
            )
        except Exception as exc:
            logger.error("Failed to load TTS model: %s", exc)
            raise RuntimeError(
                f"Cannot load TTS model '{settings.QWEN_TTS_MODEL}': {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Reference audio handling
    # ------------------------------------------------------------------

    @staticmethod
    def _load_reference_audio(ref_path: Path) -> tuple[np.ndarray, int]:
        """Load and pre-process reference audio for voice cloning.

        Args:
            ref_path: Path to the reference audio file.

        Returns:
            Tuple of (audio_array, sample_rate).

        Raises:
            FileNotFoundError: If *ref_path* does not exist.
        """
        if not ref_path.exists():
            raise FileNotFoundError(f"Reference audio not found: {ref_path}")

        audio, sr = sf.read(str(ref_path), dtype="float32")

        # Stereo -> mono
        if audio.ndim > 1:
            audio = audio.mean(axis=1)

        return audio.astype(np.float32), sr

    # ------------------------------------------------------------------
    # Core synthesis (synchronous, run on thread)
    # ------------------------------------------------------------------

    def _synthesize_internal(
        self,
        text: str,
        ref_audio_path: Optional[str] = None,
        ref_text: Optional[str] = None,
    ) -> tuple[np.ndarray, int]:
        """Synchronous TTS inference via Qwen3TTSModel.

        Args:
            text: Text to synthesize.
            ref_audio_path: Path string to reference audio for cloning.
            ref_text: Optional transcript of reference audio (improves quality).

        Returns:
            Tuple of (audio_array, sample_rate).
        """
        self._ensure_model()

        if ref_audio_path is not None:
            # Voice cloning mode
            clone_kwargs: dict = {
                "text": text,
                "language": self._detect_language(text),
                "ref_audio": ref_audio_path,
            }

            if ref_text:
                clone_kwargs["ref_text"] = ref_text
                clone_kwargs["x_vector_only_mode"] = False
            else:
                # No transcript — use x-vector only (slightly lower quality)
                clone_kwargs["x_vector_only_mode"] = True

            wavs, sr = self._model.generate_voice_clone(**clone_kwargs)
        else:
            # Default voice mode (no cloning) — use generate with a built-in voice
            wavs, sr = self._model.generate_voice_clone(
                text=text,
                language=self._detect_language(text),
                ref_audio=None,
                x_vector_only_mode=True,
            )

        audio = wavs[0] if isinstance(wavs, list) else wavs
        if isinstance(audio, torch.Tensor):
            audio = audio.cpu().float().numpy()

        return np.asarray(audio, dtype=np.float32).squeeze(), sr

    @staticmethod
    def _detect_language(text: str) -> str:
        """Simple language detection based on character ranges.

        Returns a language string compatible with Qwen3-TTS.
        """
        # Check for CJK characters
        for char in text[:200]:
            cp = ord(char)
            if 0x4E00 <= cp <= 0x9FFF:
                return "Chinese"
            if 0x3040 <= cp <= 0x30FF:
                return "Japanese"
            if 0xAC00 <= cp <= 0xD7AF:
                return "Korean"

        return "English"

    # ------------------------------------------------------------------
    # Post-processing helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _apply_speed(audio: np.ndarray, speed: float) -> np.ndarray:
        """Time-stretch *audio* to match the requested *speed* multiplier."""
        if abs(speed - 1.0) <= 0.01:
            return audio
        import librosa  # noqa: WPS433
        return librosa.effects.time_stretch(audio, rate=speed)

    @staticmethod
    def _apply_pitch(audio: np.ndarray, pitch: float, sr: int) -> np.ndarray:
        """Pitch-shift *audio* by *pitch* ratio (1.0 = no change)."""
        if abs(pitch - 1.0) <= 0.01:
            return audio
        import librosa  # noqa: WPS433
        n_steps = 12.0 * np.log2(pitch)
        return librosa.effects.pitch_shift(audio, sr=sr, n_steps=n_steps)

    # ------------------------------------------------------------------
    # Public async interface
    # ------------------------------------------------------------------

    async def synthesize(
        self,
        text: str,
        output_path: Path,
        reference_audio: Optional[Path] = None,
        speed: float = 1.0,
        pitch: float = 1.0,
    ) -> Path:
        """Generate speech from text, optionally cloning a reference voice.

        Args:
            text: Text to synthesize.
            output_path: Destination WAV file path.
            reference_audio: Optional path to reference voice sample for cloning.
            speed: Speech speed multiplier (0.5-2.0).
            pitch: Pitch adjustment multiplier (0.5-2.0).

        Returns:
            *output_path* after the file has been written.
        """
        speed = max(0.5, min(2.0, speed))
        pitch = max(0.5, min(2.0, pitch))

        ref_path_str: Optional[str] = None
        if reference_audio is not None and reference_audio.exists():
            ref_path_str = str(reference_audio)
            logger.info("Using reference audio for cloning: %s", reference_audio.name)

        # Synthesize (blocking inference on thread)
        audio, sr = await asyncio.to_thread(
            self._synthesize_internal, text, ref_path_str
        )

        # Post-process speed and pitch
        if abs(speed - 1.0) > 0.01:
            audio = await asyncio.to_thread(self._apply_speed, audio, speed)
        if abs(pitch - 1.0) > 0.01:
            audio = await asyncio.to_thread(self._apply_pitch, audio, pitch, sr)

        # Write output
        output_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(output_path), audio, sr)
        duration = len(audio) / sr
        logger.info("Synthesized speech saved: %s (%.2fs)", output_path.name, duration)

        return output_path

    async def synthesize_segment(
        self,
        text: str,
        reference_audio: Path,
        output_path: Path,
        target_duration: float,
        speed: float = 1.0,
        pitch: float = 1.0,
    ) -> Path:
        """Synthesize a speech segment and time-stretch to match *target_duration*.

        Args:
            text: Text to synthesize.
            reference_audio: Path to reference voice sample.
            output_path: Destination WAV file path.
            target_duration: Desired segment duration in seconds.
            speed: Speech speed multiplier (0.5-2.0).
            pitch: Pitch adjustment multiplier (0.5-2.0).

        Returns:
            *output_path* after writing the (possibly stretched) audio.
        """
        await self.synthesize(text, output_path, reference_audio, speed, pitch)

        # Read back and measure actual duration
        info = sf.info(str(output_path))
        actual_duration = info.duration

        if actual_duration <= 0 or abs(actual_duration - target_duration) <= 0.1:
            return output_path

        # Time-stretch to match target
        stretch_ratio = actual_duration / target_duration
        stretch_ratio = max(0.5, min(2.0, stretch_ratio))

        audio, sr = sf.read(str(output_path), dtype="float32")
        import librosa  # noqa: WPS433
        audio = librosa.effects.time_stretch(audio, rate=stretch_ratio)
        sf.write(str(output_path), audio, sr)

        logger.info(
            "Time-stretched segment: %.2fs -> %.2fs (ratio=%.3f)",
            actual_duration,
            target_duration,
            stretch_ratio,
        )
        return output_path
