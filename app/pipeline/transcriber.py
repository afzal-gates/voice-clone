"""Speech transcription using faster-whisper.

Provides both segment-level transcription (aligned with diarization output)
and full-file transcription for TTS-only workflows.
"""

import asyncio
import logging
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf

from app.config import settings
from app.models import SpeakerSegment

logger = logging.getLogger(__name__)


class SpeechTranscriber:
    """Transcribe speech from audio using the faster-whisper engine.

    The Whisper model is lazily loaded on first use.  Device selection
    (CPU vs CUDA) is resolved at load time based on ``settings.WHISPER_DEVICE``
    and actual hardware availability.

    Typical usage::

        transcriber = SpeechTranscriber()
        segments = await transcriber.transcribe_segments(audio_path, diarized_segments)
    """

    def __init__(self) -> None:
        self._model = None

    # ------------------------------------------------------------------
    # Lazy model loading
    # ------------------------------------------------------------------

    def _ensure_model(self) -> None:
        """Load the faster-whisper model if not already initialised.

        When ``settings.WHISPER_DEVICE`` is ``"auto"``, the device is
        resolved to ``"cuda"`` if a CUDA-capable GPU is available and to
        ``"cpu"`` otherwise.  The ``compute_type`` is also adjusted: if
        the resolved device is ``"cpu"`` and the configured compute type
        requires a GPU (e.g. ``float16``), it is silently downgraded to
        ``"int8"`` to prevent runtime errors.

        Raises:
            RuntimeError: If the model fails to load.
        """
        if self._model is not None:
            return

        try:
            from faster_whisper import WhisperModel  # type: ignore[import-untyped]

            device = self._resolve_device()
            compute_type = self._resolve_compute_type(device)

            logger.info(
                "Loading faster-whisper model: %s (device=%s, compute_type=%s)",
                settings.WHISPER_MODEL,
                device,
                compute_type,
            )

            self._model = WhisperModel(
                settings.WHISPER_MODEL,
                device=device,
                compute_type=compute_type,
            )

            logger.info("Whisper model loaded successfully")

        except Exception as exc:
            logger.error("Failed to load Whisper model: %s", exc)
            raise RuntimeError(
                f"Could not load faster-whisper model: {exc}"
            ) from exc

    @staticmethod
    def _resolve_device() -> str:
        """Determine the compute device for Whisper inference.

        Returns:
            ``"cuda"`` when a GPU is available and the setting allows it,
            ``"cpu"`` otherwise.
        """
        configured = settings.WHISPER_DEVICE.lower().strip()

        if configured == "auto":
            try:
                import torch  # type: ignore[import-untyped]
                return "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                return "cpu"

        return configured

    @staticmethod
    def _resolve_compute_type(device: str) -> str:
        """Ensure the compute type is compatible with the chosen device.

        ``float16`` is not supported on CPU.  If the user configured
        ``float16`` but the resolved device is ``cpu``, we fall back to
        ``int8`` which provides a good speed/accuracy trade-off.

        Args:
            device: The resolved compute device string.

        Returns:
            A compute type string compatible with *device*.
        """
        compute_type = settings.WHISPER_COMPUTE_TYPE.lower().strip()
        cpu_incompatible = {"float16"}

        if device == "cpu" and compute_type in cpu_incompatible:
            logger.warning(
                "Compute type '%s' is not supported on CPU; "
                "falling back to 'int8'",
                compute_type,
            )
            return "int8"

        return compute_type

    # ------------------------------------------------------------------
    # Segment-level transcription
    # ------------------------------------------------------------------

    async def transcribe_segments(
        self,
        audio_path: Path,
        segments: list[SpeakerSegment],
    ) -> list[SpeakerSegment]:
        """Transcribe each diarized segment and populate its ``text`` field.

        For every segment in *segments*, the corresponding audio slice is
        extracted from *audio_path*, written to a temporary file, and
        passed through faster-whisper.  The resulting transcription is
        stored in ``segment.text``.

        Args:
            audio_path: Path to the source audio file (WAV).
            segments:   Diarization segments to transcribe.  Modified
                        in-place **and** returned.

        Returns:
            The same *segments* list with ``text`` fields filled in.

        Raises:
            FileNotFoundError: If *audio_path* does not exist.
            RuntimeError:      If transcription fails.
        """
        audio_path = Path(audio_path)

        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        if not segments:
            logger.warning("No segments provided for transcription")
            return segments

        self._ensure_model()

        logger.info(
            "Transcribing %d segments from %s",
            len(segments),
            audio_path.name,
        )

        # Read the full audio file once to avoid repeated disk I/O
        full_audio, sample_rate = await asyncio.to_thread(
            sf.read, str(audio_path), dtype="float32",
        )

        for idx, segment in enumerate(segments):
            try:
                text = await self._transcribe_segment(
                    full_audio, sample_rate, segment,
                )
                segment.text = text.strip()
            except Exception as exc:
                logger.warning(
                    "Failed to transcribe segment %d (%.2fs-%.2fs, %s): %s",
                    idx,
                    segment.start_time,
                    segment.end_time,
                    segment.speaker_id,
                    exc,
                )
                segment.text = ""

        transcribed_count = sum(1 for s in segments if s.text)
        logger.info(
            "Transcription complete: %d/%d segments produced text",
            transcribed_count,
            len(segments),
        )

        return segments

    async def _transcribe_segment(
        self,
        full_audio: np.ndarray,
        sample_rate: int,
        segment: SpeakerSegment,
    ) -> str:
        """Extract and transcribe a single segment.

        Args:
            full_audio:  The complete audio waveform as a numpy array.
            sample_rate: Sample rate of *full_audio*.
            segment:     The segment defining the time slice.

        Returns:
            The transcribed text for the segment.
        """
        start_sample = int(segment.start_time * sample_rate)
        end_sample = int(segment.end_time * sample_rate)

        # Clamp to valid range
        start_sample = max(0, start_sample)
        end_sample = min(len(full_audio), end_sample)

        if end_sample <= start_sample:
            return ""

        segment_audio = full_audio[start_sample:end_sample]

        def _run_transcription() -> str:
            """Write segment to temp file and run Whisper (blocking)."""
            with tempfile.NamedTemporaryFile(
                suffix=".wav", delete=False,
            ) as tmp:
                tmp_path = Path(tmp.name)

            try:
                sf.write(str(tmp_path), segment_audio, sample_rate)

                segments_iter, info = self._model.transcribe(
                    str(tmp_path),
                    beam_size=5,
                    vad_filter=True,
                )

                # Collect all text from the transcription segments
                text_parts: list[str] = []
                for tseg in segments_iter:
                    text_parts.append(tseg.text)

                return " ".join(text_parts)
            finally:
                # Clean up temporary file
                try:
                    tmp_path.unlink(missing_ok=True)
                except OSError:
                    pass

        return await asyncio.to_thread(_run_transcription)

    # ------------------------------------------------------------------
    # Full-file transcription
    # ------------------------------------------------------------------

    async def transcribe_full(
        self,
        audio_path: Path,
    ) -> tuple[str, list[dict]]:
        """Transcribe an entire audio file with word-level timing.

        Useful for TTS-only workflows where diarization is not needed.

        Args:
            audio_path: Path to the audio file (WAV recommended).

        Returns:
            A tuple of ``(full_text, word_segments)`` where *full_text*
            is the complete transcription and *word_segments* is a list
            of dictionaries with keys ``word``, ``start``, ``end``, and
            ``probability``.

        Raises:
            FileNotFoundError: If *audio_path* does not exist.
            RuntimeError:      If transcription fails.
        """
        audio_path = Path(audio_path)

        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        self._ensure_model()

        logger.info("Transcribing full audio: %s", audio_path.name)

        def _run() -> tuple[str, list[dict]]:
            """Blocking full-file transcription in a worker thread."""
            segments_iter, info = self._model.transcribe(
                str(audio_path),
                beam_size=5,
                word_timestamps=True,
                vad_filter=True,
            )

            text_parts: list[str] = []
            word_segments: list[dict] = []

            for segment in segments_iter:
                text_parts.append(segment.text)

                if segment.words:
                    for word in segment.words:
                        word_segments.append({
                            "word": word.word,
                            "start": word.start,
                            "end": word.end,
                            "probability": word.probability,
                        })

            full_text = " ".join(text_parts).strip()
            return full_text, word_segments

        try:
            full_text, word_segments = await asyncio.to_thread(_run)
        except Exception as exc:
            logger.error(
                "Full transcription failed for %s: %s", audio_path.name, exc,
            )
            raise RuntimeError(
                f"Full audio transcription failed: {exc}"
            ) from exc

        logger.info(
            "Full transcription complete: %d characters, %d words",
            len(full_text),
            len(word_segments),
        )

        return full_text, word_segments
