"""Multi-model text-to-speech engine.

Supports two TTS backends:

1. **Qwen3-TTS** (``qwen-tts`` package) — multilingual with voice cloning.
   Model: ``Qwen/Qwen3-TTS-12Hz-1.7B-Base`` (24 kHz output).

2. **Meta MMS-TTS Bengali** (``transformers`` VitsModel) — Bengali-focused,
   no voice cloning.  Model: ``facebook/mms-tts-ben`` (16 kHz output).

Both models are loaded lazily on first use.  Public methods are ``async`` and
delegate blocking inference to ``asyncio.to_thread``.
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

# --- pydub FFmpeg discovery ---
# pydub (used by f5_tts for audio preprocessing) requires FFmpeg.
# The binary may not be on PATH; imageio-ffmpeg bundles it for all platforms.
try:
    import imageio_ffmpeg
    import pydub.utils

    _ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    pydub.utils.FFMPEG_PATH = _ffmpeg_exe          # used internally by pydub
    # Also make AudioSegment.converter aware
    from pydub import AudioSegment
    AudioSegment.converter = _ffmpeg_exe
    logger.debug("pydub FFmpeg set to %s", _ffmpeg_exe)
except Exception:
    pass  # If neither package is available, pydub will try the system FFmpeg

# Model identifier constants used throughout the API / frontend.
MODEL_QWEN = "qwen3-tts"
MODEL_MMS = "mms-tts-ben"
MODEL_INDICF5 = "indicf5"
AVAILABLE_MODELS = [MODEL_QWEN, MODEL_MMS, MODEL_INDICF5]


class TTSEngine:
    """Multi-model TTS engine with lazy model loading.

    Public methods are ``async`` and delegate blocking inference to
    ``asyncio.to_thread``.
    """

    def __init__(self) -> None:
        self._qwen_model: object | None = None
        self._mms_model: object | None = None
        self._mms_tokenizer: object | None = None
        self._indicf5_model: object | None = None
        self._indicf5_vocoder: object | None = None
        self._device: str = "cuda" if torch.cuda.is_available() else "cpu"
        logger.debug(
            "TTSEngine created (device=%s, qwen=%s, mms=%s, indicf5=%s)",
            self._device,
            settings.QWEN_TTS_MODEL,
            settings.MMS_TTS_MODEL,
            settings.INDICF5_MODEL,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_to_local(model_id: str) -> str:
        """Resolve a HF model ID to its local cache snapshot path.

        When models have been pre-downloaded (``MODELS_DIR`` is set),
        ``from_pretrained`` must receive a *local directory path* rather
        than a remote repo ID.  Passing a directory makes the
        ``transformers`` library skip network calls (e.g. the
        ``model_info`` check inside ``_patch_mistral_regex``).

        Scans the HF cache directory structure directly to avoid any
        network calls that ``snapshot_download`` might trigger even
        with ``local_files_only=True`` when ``HF_HUB_OFFLINE=1``.

        Returns the local path when found in cache, or *model_id*
        unchanged when no local copy exists.
        """
        import os as _os
        hf_home = _os.environ.get("HF_HOME", "")
        if not hf_home:
            return model_id

        # HF cache structure: {HF_HOME}/hub/models--{org}--{name}/snapshots/{hash}/
        cache_dir_name = "models--" + model_id.replace("/", "--")
        snapshots_dir = Path(hf_home) / "hub" / cache_dir_name / "snapshots"
        if not snapshots_dir.is_dir():
            return model_id

        # Pick the first (usually only) snapshot hash directory
        snapshot_dirs = [d for d in snapshots_dir.iterdir() if d.is_dir()]
        if snapshot_dirs:
            resolved = str(snapshot_dirs[0])
            logger.info("Resolved %s -> %s", model_id, resolved)
            return resolved

        return model_id

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

            model_path = self._resolve_to_local(settings.QWEN_TTS_MODEL)
            self._qwen_model = Qwen3TTSModel.from_pretrained(
                model_path,
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

            model_path = self._resolve_to_local(settings.MMS_TTS_MODEL)
            self._mms_tokenizer = AutoTokenizer.from_pretrained(model_path)
            self._mms_model = VitsModel.from_pretrained(model_path).to(self._device)
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

    def _ensure_indicf5_model(self) -> None:
        """Load the IndicF5 model on first call.

        Loads model components directly via ``f5_tts`` and
        ``huggingface_hub``.  The HuggingFace ``model.py`` shipped
        with ``ai4bharat/IndicF5`` has two bugs:

        1. Missing ``ckpt_path`` argument in the ``load_model()`` call.
        2. Weights were saved from ``torch.compile``-wrapped modules,
           so every key carries a ``_orig_mod.`` prefix.

        This loader side-steps both issues by downloading the
        safetensors file, stripping the ``_orig_mod.`` prefix, and
        loading the DiT + Vocos weights separately.

        CPU inference is used to avoid a known meta-tensor crash in
        the Vocos vocoder when transferring to GPU.
        """
        if self._indicf5_model is not None:
            return

        logger.info("Loading IndicF5 model: %s", settings.INDICF5_MODEL)

        try:
            from huggingface_hub import hf_hub_download  # noqa: WPS433
            from safetensors.torch import load_file  # noqa: WPS433
            from f5_tts.model import DiT  # noqa: WPS433
            from f5_tts.infer.utils_infer import (  # noqa: WPS433
                load_vocoder,
                get_tokenizer,
            )
            from f5_tts.model.cfm import CFM  # noqa: WPS433
            from f5_tts.infer.utils_infer import (  # noqa: WPS433
                n_mel_channels,
                n_fft,
                hop_length,
                win_length,
                target_sample_rate,
            )

            repo_id = settings.INDICF5_MODEL
            token = settings.HF_TOKEN or None

            # 1. Download vocab + safetensors from HuggingFace
            logger.info("Downloading IndicF5 vocab and checkpoint...")
            vocab_path = hf_hub_download(
                repo_id, filename="checkpoints/vocab.txt", token=token,
            )
            safetensors_path = hf_hub_download(
                repo_id, filename="model.safetensors", token=token,
            )

            # 2. Load the Vocos vocoder structure (patched for meta
            #    tensor bug) — weights will be overwritten from safetensors
            logger.info("Loading Vocos vocoder for IndicF5...")
            self._indicf5_vocoder = load_vocoder(
                vocoder_name="vocos", is_local=False, device="cpu",
            )

            # 3. Build the CFM / DiT model structure (no weights yet)
            logger.info("Building IndicF5 DiT model structure...")
            vocab_char_map, vocab_size = get_tokenizer(vocab_path, "custom")

            model_cfg = dict(
                dim=1024, depth=22, heads=16, ff_mult=2,
                text_dim=512, conv_layers=4,
            )
            cfm_model = CFM(
                transformer=DiT(
                    **model_cfg,
                    text_num_embeds=vocab_size,
                    mel_dim=n_mel_channels,
                ),
                mel_spec_kwargs=dict(
                    n_fft=n_fft,
                    hop_length=hop_length,
                    win_length=win_length,
                    n_mel_channels=n_mel_channels,
                    target_sample_rate=target_sample_rate,
                    mel_spec_type="vocos",
                ),
                odeint_kwargs=dict(method="euler"),
                vocab_char_map=vocab_char_map,
            ).to("cpu")

            # 4. Load safetensors and strip _orig_mod. prefix
            logger.info("Loading IndicF5 weights from safetensors...")
            full_state = load_file(safetensors_path, device="cpu")

            # Separate DiT keys from vocoder keys; strip _orig_mod.
            dit_state: dict = {}
            voc_state: dict = {}
            for key, val in full_state.items():
                clean = key.replace("_orig_mod.", "")
                if clean.startswith("vocoder."):
                    voc_state[clean[len("vocoder."):]] = val
                else:
                    dit_state[clean] = val

            # 5. Load weights into the models
            cfm_model.load_state_dict(dit_state, strict=False)
            cfm_model = cfm_model.eval()
            self._indicf5_model = cfm_model

            if voc_state:
                self._indicf5_vocoder.load_state_dict(voc_state, strict=False)
                self._indicf5_vocoder = self._indicf5_vocoder.eval()

            logger.info("IndicF5 model loaded successfully (CPU inference)")

        except ImportError:
            raise RuntimeError(
                "Required packages not installed. "
                "Run: pip install f5-tts vocos x_transformers "
                "torchdiffeq ema_pytorch pypinyin jieba cached_path"
            )
        except Exception as exc:
            logger.error("Failed to load IndicF5 model: %s", exc)
            raise RuntimeError(
                f"Cannot load IndicF5 model '{settings.INDICF5_MODEL}': {exc}"
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

        if ref_audio_path is None:
            raise ValueError(
                "Qwen3-TTS requires a reference voice for synthesis. "
                "Please select a saved voice or upload a reference audio file."
            )

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
    # Core synthesis — IndicF5 (synchronous, run on thread)
    # ------------------------------------------------------------------

    @staticmethod
    def _torchaudio_load_sf(filepath, **kwargs):
        """Replacement for ``torchaudio.load`` using soundfile.

        torchaudio >= 2.10 removed the soundfile backend and requires
        FFmpeg shared libraries (torchcodec) which may not be available
        on all platforms.  This drop-in replacement lets ``f5_tts`` work
        without FFmpeg.
        """
        audio_np, sr = sf.read(str(filepath), dtype="float32")
        if audio_np.ndim == 1:
            audio_np = audio_np[np.newaxis, :]       # (1, samples)
        else:
            audio_np = audio_np.T                     # (channels, samples)
        return torch.from_numpy(audio_np), sr

    def _synthesize_indicf5(
        self,
        text: str,
        ref_audio_path: Optional[str] = None,
        ref_text: Optional[str] = None,
    ) -> tuple[np.ndarray, int]:
        """Synchronous TTS inference via IndicF5 (ai4bharat/IndicF5).

        Uses ``f5_tts.infer.utils_infer.infer_process`` directly with
        the pre-loaded DiT model and Vocos vocoder.  Temporarily patches
        ``torchaudio.load`` to use soundfile (avoids FFmpeg DLL
        requirement on Windows).
        """
        self._ensure_indicf5_model()

        if ref_audio_path is None:
            raise ValueError(
                "IndicF5 requires a reference voice for synthesis. "
                "Please upload a reference audio file."
            )

        import torchaudio  # noqa: WPS433
        from f5_tts.infer.utils_infer import (  # noqa: WPS433
            infer_process,
            preprocess_ref_audio_text,
        )

        logger.info("IndicF5 synthesizing %d chars with ref=%s", len(text), ref_audio_path)

        # Preprocess reference audio and text
        ref_audio, ref_text_processed = preprocess_ref_audio_text(
            ref_audio_path, ref_text or "",
        )

        # Monkeypatch torchaudio.load so f5_tts uses soundfile
        # instead of torchcodec (which needs FFmpeg shared libraries).
        _orig_load = torchaudio.load
        torchaudio.load = self._torchaudio_load_sf
        try:
            audio, sr, _ = infer_process(
                ref_audio,
                ref_text_processed,
                text,
                self._indicf5_model,
                self._indicf5_vocoder,
                mel_spec_type="vocos",
                speed=1.0,
                device="cpu",
            )
        finally:
            torchaudio.load = _orig_load

        if isinstance(audio, torch.Tensor):
            audio = audio.cpu().float().numpy()

        return np.asarray(audio, dtype=np.float32).squeeze(), sr

    # ------------------------------------------------------------------
    # Language detection
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_language(text: str) -> str:
        """Simple language detection based on Unicode character ranges.

        Detects languages supported by Qwen3-TTS (Chinese, English, French,
        German, Italian, Japanese, Korean, Portuguese, Russian, Spanish)
        and Indian languages supported by IndicF5 (Assamese, Bengali,
        Gujarati, Hindi, Kannada, Malayalam, Marathi, Odia, Punjabi,
        Tamil, Telugu).

        Falls back to ``"English"`` for Latin-script text.
        """
        for char in text[:200]:
            cp = ord(char)
            # East Asian
            if 0x4E00 <= cp <= 0x9FFF:
                return "Chinese"
            if 0x3040 <= cp <= 0x30FF or 0x31F0 <= cp <= 0x31FF:
                return "Japanese"
            if 0xAC00 <= cp <= 0xD7AF or 0x1100 <= cp <= 0x11FF:
                return "Korean"
            # Cyrillic
            if 0x0400 <= cp <= 0x04FF:
                return "Russian"
            # Indian scripts
            if 0x0980 <= cp <= 0x09FF:
                return "Bengali"
            if 0x0900 <= cp <= 0x097F:
                return "Hindi"
            if 0x0A80 <= cp <= 0x0AFF:
                return "Gujarati"
            if 0x0B80 <= cp <= 0x0BFF:
                return "Tamil"
            if 0x0C00 <= cp <= 0x0C7F:
                return "Telugu"
            if 0x0C80 <= cp <= 0x0CFF:
                return "Kannada"
            if 0x0D00 <= cp <= 0x0D7F:
                return "Malayalam"
            if 0x0B00 <= cp <= 0x0B7F:
                return "Odia"
            if 0x0A00 <= cp <= 0x0A7F:
                return "Punjabi"

        # Latin-script languages fall back to English for auto-detect.
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
        ref_text: Optional[str] = None,
    ) -> Path:
        """Generate speech from text using the selected model.

        Args:
            text: Text to synthesize.
            output_path: Destination WAV file path.
            reference_audio: Optional path to reference voice sample.
            speed: Speech speed multiplier (0.5-2.0).
            pitch: Pitch adjustment multiplier (0.5-2.0).
            language: Explicit language (e.g. "English", "Bengali").
            tts_model: Model to use — ``"qwen3-tts"``, ``"mms-tts-ben"``,
                       or ``"indicf5"``.
            ref_text: Transcript of the reference audio (used by IndicF5
                      and optionally by Qwen3-TTS).

        Returns:
            *output_path* after the file has been written.
        """
        speed = max(0.5, min(2.0, speed))
        pitch = max(0.5, min(2.0, pitch))

        ref_path_str: Optional[str] = None
        if reference_audio is not None and reference_audio.exists():
            ref_path_str = str(reference_audio)

        if tts_model == MODEL_MMS:
            # MMS-TTS Bengali — no voice cloning support
            audio, sr = await asyncio.to_thread(self._synthesize_mms, text)
        elif tts_model == MODEL_INDICF5:
            # IndicF5 — Indian languages with voice cloning
            if ref_path_str:
                logger.info("Using reference audio for IndicF5: %s", reference_audio.name)
            audio, sr = await asyncio.to_thread(
                self._synthesize_indicf5, text, ref_path_str, ref_text
            )
        else:
            # Qwen3-TTS — supports voice cloning
            if ref_path_str:
                logger.info("Using reference audio for cloning: %s", reference_audio.name)
            audio, sr = await asyncio.to_thread(
                self._synthesize_qwen, text, ref_path_str, ref_text, language
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
