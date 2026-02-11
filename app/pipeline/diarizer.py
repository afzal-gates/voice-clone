"""Speaker diarization using pyannote.audio.

Identifies *who* speaks *when* in an audio file, producing time-stamped
speaker segments that downstream modules (transcription, TTS) consume.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from app.config import settings
from app.models import Speaker, SpeakerSegment

logger = logging.getLogger(__name__)


class SpeakerDiarizer:
    """Detect and segment speakers in audio using pyannote.audio.

    The diarization pipeline is lazily loaded on first use to avoid long
    import times and GPU memory allocation at module-import time.

    Typical usage::

        diarizer = SpeakerDiarizer()
        segments = await diarizer.diarize(audio_path)
        speakers = diarizer.get_speakers(segments)
    """

    def __init__(self) -> None:
        self._pipeline = None

    # ------------------------------------------------------------------
    # Lazy pipeline loading
    # ------------------------------------------------------------------

    def _ensure_pipeline(self) -> None:
        """Load the pyannote diarization pipeline if not already initialised.

        Requires a valid Hugging Face token (``settings.HF_TOKEN``) when the
        model is gated.

        Raises:
            RuntimeError: If the pipeline cannot be loaded.
        """
        if self._pipeline is not None:
            return

        try:
            from pyannote.audio import Pipeline  # type: ignore[import-untyped]

            logger.info(
                "Loading pyannote diarization pipeline: %s",
                settings.PYANNOTE_MODEL,
            )

            hf_token = settings.HF_TOKEN or None
            self._pipeline = Pipeline.from_pretrained(
                settings.PYANNOTE_MODEL,
                use_auth_token=hf_token,
            )

            # Move to GPU when available
            try:
                import torch  # type: ignore[import-untyped]

                if torch.cuda.is_available():
                    self._pipeline = self._pipeline.to(torch.device("cuda"))
                    logger.info("Diarization pipeline moved to CUDA")
            except ImportError:
                pass

            logger.info("Diarization pipeline loaded successfully")

        except Exception as exc:
            logger.error("Failed to load diarization pipeline: %s", exc)
            raise RuntimeError(
                f"Could not load pyannote diarization pipeline: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Diarization
    # ------------------------------------------------------------------

    async def diarize(
        self,
        audio_path: Path,
        min_speakers: int | None = None,
        max_speakers: int | None = None,
    ) -> list[SpeakerSegment]:
        """Run speaker diarization on *audio_path*.

        Args:
            audio_path:   Path to the audio file (WAV recommended).
            min_speakers: Minimum expected speaker count.  Falls back to
                          ``settings.MIN_SPEAKERS`` when ``None``.
            max_speakers: Maximum expected speaker count.  Falls back to
                          ``settings.MAX_SPEAKERS`` when ``None``.

        Returns:
            A list of :class:`SpeakerSegment` instances sorted by
            ``start_time``.

        Raises:
            FileNotFoundError: If *audio_path* does not exist.
            RuntimeError:      If diarization fails.
        """
        audio_path = Path(audio_path)

        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        min_s = min_speakers if min_speakers is not None else settings.MIN_SPEAKERS
        max_s = max_speakers if max_speakers is not None else settings.MAX_SPEAKERS

        logger.info(
            "Diarizing %s (min_speakers=%d, max_speakers=%d)",
            audio_path.name,
            min_s,
            max_s,
        )

        self._ensure_pipeline()

        def _run_diarization() -> list[SpeakerSegment]:
            """Blocking diarization executed in a worker thread."""
            diarization = self._pipeline(
                str(audio_path),
                min_speakers=min_s,
                max_speakers=max_s,
            )

            segments: list[SpeakerSegment] = []
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                segment = SpeakerSegment(
                    speaker_id=speaker,
                    start_time=turn.start,
                    end_time=turn.end,
                )
                segments.append(segment)

            # Sort by start time for consistent downstream processing
            segments.sort(key=lambda s: s.start_time)
            return segments

        try:
            segments = await asyncio.to_thread(_run_diarization)
        except Exception as exc:
            logger.error("Diarization failed for %s: %s", audio_path.name, exc)
            raise RuntimeError(
                f"Speaker diarization failed: {exc}"
            ) from exc

        logger.info(
            "Diarization complete: %d segments from %s",
            len(segments),
            audio_path.name,
        )
        return segments

    # ------------------------------------------------------------------
    # Speaker aggregation
    # ------------------------------------------------------------------

    @staticmethod
    def get_speakers(segments: list[SpeakerSegment]) -> list[Speaker]:
        """Aggregate diarization segments into per-speaker summaries.

        For each unique ``speaker_id`` found in *segments*, a
        :class:`Speaker` object is created with segment count and total
        speaking duration.  Speakers are assigned human-friendly labels
        (``"Speaker 1"``, ``"Speaker 2"``, ...) in order of first
        appearance.

        Args:
            segments: Diarization segments produced by :meth:`diarize`.

        Returns:
            A list of :class:`Speaker` objects ordered by first appearance.
        """
        if not segments:
            return []

        # Preserve first-appearance ordering
        speaker_stats: dict[str, dict] = {}
        appearance_order: list[str] = []

        for segment in segments:
            sid = segment.speaker_id
            if sid not in speaker_stats:
                speaker_stats[sid] = {
                    "segment_count": 0,
                    "total_duration": 0.0,
                }
                appearance_order.append(sid)

            speaker_stats[sid]["segment_count"] += 1
            speaker_stats[sid]["total_duration"] += (
                segment.end_time - segment.start_time
            )

        speakers: list[Speaker] = []
        for idx, sid in enumerate(appearance_order):
            stats = speaker_stats[sid]
            speaker = Speaker(
                speaker_id=sid,
                label=f"Speaker {idx + 1}",
                segment_count=stats["segment_count"],
                total_duration=stats["total_duration"],
            )
            speakers.append(speaker)

        logger.debug(
            "Identified %d speakers: %s",
            len(speakers),
            ", ".join(s.label for s in speakers),
        )
        return speakers

    # ------------------------------------------------------------------
    # Segment post-processing
    # ------------------------------------------------------------------

    @staticmethod
    def merge_short_segments(
        segments: list[SpeakerSegment],
        min_duration: float = 0.5,
        gap_threshold: float = 0.3,
    ) -> list[SpeakerSegment]:
        """Merge adjacent same-speaker segments and filter short fragments.

        Two consecutive segments from the same speaker are merged when the
        gap between them is smaller than *gap_threshold* seconds.  After
        merging, any segment shorter than *min_duration* is discarded.

        Args:
            segments:      Input segments sorted by ``start_time``.
            min_duration:  Minimum segment duration in seconds.  Segments
                           shorter than this are dropped.
            gap_threshold: Maximum inter-segment gap in seconds for merging.

        Returns:
            A new list of :class:`SpeakerSegment` objects, sorted by
            ``start_time``.
        """
        if not segments:
            return []

        # Ensure input is sorted
        sorted_segments = sorted(segments, key=lambda s: s.start_time)

        merged: list[SpeakerSegment] = []
        current = SpeakerSegment(
            speaker_id=sorted_segments[0].speaker_id,
            start_time=sorted_segments[0].start_time,
            end_time=sorted_segments[0].end_time,
            text=sorted_segments[0].text or "",
        )

        for segment in sorted_segments[1:]:
            gap = segment.start_time - current.end_time
            same_speaker = segment.speaker_id == current.speaker_id

            if same_speaker and gap <= gap_threshold:
                # Merge: extend current segment
                current.end_time = max(current.end_time, segment.end_time)
                # Concatenate text if present
                if segment.text:
                    existing_text = current.text or ""
                    separator = " " if existing_text else ""
                    current.text = existing_text + separator + segment.text
            else:
                # Finalise current and start a new one
                merged.append(current)
                current = SpeakerSegment(
                    speaker_id=segment.speaker_id,
                    start_time=segment.start_time,
                    end_time=segment.end_time,
                    text=segment.text or "",
                )

        # Don't forget the last segment
        merged.append(current)

        # Filter out segments shorter than min_duration
        filtered = [
            seg for seg in merged
            if (seg.end_time - seg.start_time) >= min_duration
        ]

        logger.debug(
            "Segment merging: %d -> %d merged -> %d after filtering "
            "(min_duration=%.2fs, gap_threshold=%.2fs)",
            len(sorted_segments),
            len(merged),
            len(filtered),
            min_duration,
            gap_threshold,
        )

        return filtered
