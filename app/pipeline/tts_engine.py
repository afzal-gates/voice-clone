"""Multi-model text-to-speech engine.

Supports two TTS backends:

1. **Qwen3-TTS** (``qwen-tts`` package) — multilingual with voice cloning.
   Model: ``Qwen/Qwen3-TTS-12Hz-1.7B-Base`` (24 kHz output).

2. **Meta MMS-TTS Bengali** (``transformers`` VitsModel) — Bengali-focused,
   no voice cloning.  Model: ``facebook/mms-tts-ben`` (16 kHz output).

Both models are loaded lazily on first use.  Public methods are ``async`` and
delegate blocking inference to ``asyncio.to_thread``.
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

# Model identifier constants used throughout the API / frontend.
MODEL_QWEN = "qwen3-tts"
MODEL_MMS = "mms-tts-ben"
AVAILABLE_MODELS = [MODEL_QWEN, MODEL_MMS]


class TTSEngine:
    """Multi-model TTS engine with lazy model loading.

    Public methods are ``async`` and delegate blocking inference to
    ``asyncio.to_thread``.
    """

    def __init__(self) -> None:
        self._qwen_model: object | None = None
        self._mms_model: object | None = None
        self._mms_tokenizer: object | None = None
        self._device: str = "cuda" if torch.cuda.is_available() else "cpu"
        logger.debug(
            "TTSEngine created (device=%s, qwen=%s, mms=%s)",
            self._device,
            settings.QWEN_TTS_MODEL,
            settings.MMS_TTS_MODEL,
        )

    # ------------------------------------------------------------------
    # Lazy model loading
    # ------------------------------------------------------------------

    def _ensure_qwen_model(self) -> None:
        """Load the Qwen3-TTS model on first call."""
        if self._qwen_model is not None:
            return

        logger.info("Loading Qwen3-TTS model: %s on %s", settings.QWEN_TTS_MODEL, self._device)

        try:
            from qwen_tts import Qwen3TTSModel  # noqa: WPS433

            dtype = torch.bfloat16 if self._device == "cuda" else torch.float32

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

            self._qwen_model = Qwen3TTSModel.from_pretrained(
                settings.QWEN_TTS_MODEL,
                **load_kwargs,
            )
            logger.info("Qwen3-TTS model loaded successfully")

        except ImportError:
            raise RuntimeError(
                "qwen-tts package not installed. Run: pip install qwen-tts"
            )
        except Exception as exc:
            logger.error("Failed to load Qwen3-TTS model: %s", exc)
            raise RuntimeError(
                f"Cannot load Qwen3-TTS model '{settings.QWEN_TTS_MODEL}': {exc}"
            ) from exc

    def _ensure_mms_model(self) -> None:
        """Load the Meta MMS-TTS Bengali model on first call."""
        if self._mms_model is not None:
            return

        logger.info("Loading MMS-TTS model: %s on %s", settings.MMS_TTS_MODEL, self._device)

        try:
            from transformers import VitsModel, AutoTokenizer  # noqa: WPS433

            self._mms_tokenizer = AutoTokenizer.from_pretrained(settings.MMS_TTS_MODEL)
            self._mms_model = VitsModel.from_pretrained(settings.MMS_TTS_MODEL).to(self._device)
            logger.info("MMS-TTS model loaded successfully")

        except ImportError:
            raise RuntimeError(
                "transformers package not installed. Run: pip install transformers"
            )
        except Exception as exc:
            logger.error("Failed to load MMS-TTS model: %s", exc)
            raise RuntimeError(
                f"Cannot load MMS-TTS model '{settings.MMS_TTS_MODEL}': {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Reference audio handling
    # ------------------------------------------------------------------

    @staticmethod
    def _load_reference_audio(ref_path: Path) -> tuple[np.ndarray, int]:
        """Load and pre-process reference audio for voice cloning."""
        if not ref_path.exists():
            raise FileNotFoundError(f"Reference audio not found: {ref_path}")

        audio, sr = sf.read(str(ref_path), dtype="float32")

        # Stereo -> mono
        if audio.ndim > 1:
            audio = audio.mean(axis=1)

        return audio.astype(np.float32), sr

    # ------------------------------------------------------------------
    # Core synthesis — Qwen3-TTS (synchronous, run on thread)
    # ------------------------------------------------------------------

    def _synthesize_qwen(
        self,
        text: str,
        ref_audio_path: Optional[str] = None,
        ref_text: Optional[str] = None,
        language: Optional[str] = None,
    ) -> tuple[np.ndarray, int]:
        """Synchronous TTS inference via Qwen3TTSModel."""
        self._ensure_qwen_model()

        lang = language if language else self._detect_language(text)
        logger.info("Qwen3-TTS language: %s", lang)

        if ref_audio_path is not None:
            clone_kwargs: dict = {
                "text": text,
                "language": lang,
                "ref_audio": ref_audio_path,
            }
            if ref_text:
                clone_kwargs["ref_text"] = ref_text
                clone_kwargs["x_vector_only_mode"] = False
            else:
                clone_kwargs["x_vector_only_mode"] = True

            wavs, sr = self._qwen_model.generate_voice_clone(**clone_kwargs)
        else:
            wavs, sr = self._qwen_model.generate_voice_clone(
                text=text,
                language=lang,
                ref_audio=None,
                x_vector_only_mode=True,
            )

        audio = wavs[0] if isinstance(wavs, list) else wavs
        if isinstance(audio, torch.Tensor):
            audio = audio.cpu().float().numpy()

        return np.asarray(audio, dtype=np.float32).squeeze(), sr

    # ------------------------------------------------------------------
    # Core synthesis — MMS-TTS Bengali (synchronous, run on thread)
    # ------------------------------------------------------------------

    def _synthesize_mms(self, text: str) -> tuple[np.ndarray, int]:
        """Synchronous TTS inference via Meta MMS-TTS Bengali (VitsModel)."""
        self._ensure_mms_model()

        logger.info("MMS-TTS synthesizing %d chars", len(text))

        inputs = self._mms_tokenizer(text, return_tensors="pt").to(self._device)

        with torch.no_grad():
            output = self._mms_model(**inputs)

        audio = output.waveform[0].cpu().float().numpy()
        sr = self._mms_model.config.sampling_rate  # 16000

        return np.asarray(audio, dtype=np.float32).squeeze(), sr

    # ------------------------------------------------------------------
    # Language detection
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_language(text: str) -> str:
        """Simple language detection based on character ranges."""
        for char in text[:200]:
            cp = ord(char)
            if 0x4E00 <= cp <= 0x9FFF:
                return "Chinese"
            if 0x3040 <= cp <= 0x30FF:
                return "Japanese"
            if 0xAC00 <= cp <= 0xD7AF:
                return "Korean"
            if 0x0980 <= cp <= 0x09FF:
                return "Bengali"

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
        language: Optional[str] = None,
        tts_model: str = MODEL_QWEN,
    ) -> Path:
        """Generate speech from text using the selected model.

        Args:
            text: Text to synthesize.
            output_path: Destination WAV file path.
            reference_audio: Optional path to reference voice sample (Qwen only).
            speed: Speech speed multiplier (0.5-2.0).
            pitch: Pitch adjustment multiplier (0.5-2.0).
            language: Explicit language (e.g. "English", "Bengali").
            tts_model: Model to use — ``"qwen3-tts"`` or ``"mms-tts-ben"``.

        Returns:
            *output_path* after the file has been written.
        """
        speed = max(0.5, min(2.0, speed))
        pitch = max(0.5, min(2.0, pitch))

        if tts_model == MODEL_MMS:
            # MMS-TTS Bengali — no voice cloning support
            audio, sr = await asyncio.to_thread(self._synthesize_mms, text)
        else:
            # Qwen3-TTS — supports voice cloning
            ref_path_str: Optional[str] = None
            if reference_audio is not None and reference_audio.exists():
                ref_path_str = str(reference_audio)
                logger.info("Using reference audio for cloning: %s", reference_audio.name)

            audio, sr = await asyncio.to_thread(
                self._synthesize_qwen, text, ref_path_str, None, language
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
        logger.info("Synthesized speech saved: %s (%.2fs, model=%s)", output_path.name, duration, tts_model)

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

        Uses Qwen3-TTS (voice cloning) for pipeline voice replacement.
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
