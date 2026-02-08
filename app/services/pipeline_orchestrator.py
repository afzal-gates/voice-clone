"""Pipeline orchestration for the VoiceClone AI processing workflow.

Coordinates all pipeline modules (extraction, separation, diarization,
transcription, TTS, alignment, merging) through a multi-stage async
workflow driven by :class:`JobManager` state transitions.
"""

import logging
from pathlib import Path

from app.config import settings
from app.models import JobStatus, VoiceAssignment
from app.pipeline.aligner import AudioAligner
from app.pipeline.audio_extractor import AudioExtractor
from app.pipeline.diarizer import SpeakerDiarizer
from app.pipeline.merger import AudioMerger
from app.pipeline.separator import AudioSeparator
from app.pipeline.transcriber import SpeechTranscriber
from app.pipeline.tts_engine import TTSEngine
from app.services.job_manager import JobManager
from app.utils.audio_utils import get_duration

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """Orchestrate the full voice-clone processing pipeline.

    Each public method drives a distinct workflow (upload analysis,
    voice replacement, standalone TTS).  They are designed to be launched
    as fire-and-forget background tasks and communicate progress
    exclusively through :class:`JobManager` state updates.
    """

    def __init__(self, job_manager: JobManager) -> None:
        self.job_manager = job_manager

        self.extractor = AudioExtractor()
        self.separator = AudioSeparator()
        self.diarizer = SpeakerDiarizer()
        self.transcriber = SpeechTranscriber()
        self.tts_engine = TTSEngine()
        self.aligner = AudioAligner()
        self.merger = AudioMerger()

    # ------------------------------------------------------------------
    # Upload analysis pipeline
    # ------------------------------------------------------------------

    async def process_upload(self, job_id: str, file_path: Path) -> None:
        """Run the full analysis pipeline on an uploaded media file.

        Stages: extract audio -> separate vocals/music -> diarize speakers
        -> transcribe segments.  On completion the job enters
        ``AWAITING_VOICE_ASSIGNMENT`` so the user can map speakers to
        reference voices.

        This method is intended to be launched as a background task.

        Args:
            job_id:    The job identifier.
            file_path: Path to the uploaded media file saved on disk.
        """
        try:
            job = self.job_manager.get_job(job_id)
            if job is None:
                logger.error("process_upload: job %s not found", job_id)
                return

            job_dir = self.job_manager.get_job_dir(job_id)

            # --- 1. Extract / convert audio ---------------------------------
            self.job_manager.update_job(
                job_id,
                status=JobStatus.EXTRACTING_AUDIO,
                progress=0.05,
            )

            audio_wav = job_dir / "input" / "audio.wav"

            if self.extractor.is_video(file_path):
                logger.info("Job %s: extracting audio from video", job_id)
                await self.extractor.extract_audio(file_path, audio_wav)
            else:
                logger.info("Job %s: converting audio to WAV", job_id)
                await self.extractor.convert_to_wav(
                    file_path, audio_wav, sample_rate=settings.SAMPLE_RATE
                )

            # --- 2. Separate vocals and music -------------------------------
            self.job_manager.update_job(
                job_id,
                status=JobStatus.SEPARATING,
                progress=0.15,
            )

            vocals_dir = job_dir / "vocals"
            music_dir = job_dir / "music"
            vocals_dir.mkdir(parents=True, exist_ok=True)
            music_dir.mkdir(parents=True, exist_ok=True)

            logger.info("Job %s: separating vocals and music", job_id)
            vocals_path, accompaniment_path = await self.separator.separate(
                audio_wav, job_dir
            )

            # --- 3. Speaker diarization ------------------------------------
            self.job_manager.update_job(
                job_id,
                status=JobStatus.DIARIZING,
                progress=0.35,
            )

            logger.info("Job %s: running speaker diarization", job_id)
            segments = await self.diarizer.diarize(
                vocals_path,
                min_speakers=settings.MIN_SPEAKERS,
                max_speakers=settings.MAX_SPEAKERS,
            )

            segments = self.diarizer.merge_short_segments(
                segments,
                min_duration=0.5,
                gap_threshold=0.3,
            )

            # --- 4. Transcription ------------------------------------------
            self.job_manager.update_job(
                job_id,
                status=JobStatus.TRANSCRIBING,
                progress=0.50,
            )

            logger.info("Job %s: transcribing %d segments", job_id, len(segments))
            segments = await self.transcriber.transcribe_segments(
                vocals_path, segments
            )

            # --- 5. Build speaker list and finalise -------------------------
            speakers = self.diarizer.get_speakers(segments)

            self.job_manager.update_job(
                job_id,
                speakers=speakers,
                segments=segments,
                status=JobStatus.AWAITING_VOICE_ASSIGNMENT,
                progress=0.65,
            )

            logger.info(
                "Job %s: analysis complete -- %d speakers, %d segments",
                job_id,
                len(speakers),
                len(segments),
            )

        except Exception as exc:
            logger.exception("Job %s: upload processing failed", job_id)
            self.job_manager.update_job(
                job_id,
                status=JobStatus.FAILED,
                error=str(exc),
            )

    # ------------------------------------------------------------------
    # Voice replacement pipeline
    # ------------------------------------------------------------------

    async def process_voice_replacement(
        self,
        job_id: str,
        assignments: list[VoiceAssignment],
    ) -> None:
        """Replace detected speaker voices with TTS-generated speech.

        Stages: generate speech per segment -> time-align to original
        timing -> merge with original background music -> (optionally)
        rebuild video.

        This method is intended to be launched as a background task.

        Args:
            job_id:      The job identifier.
            assignments: Speaker-to-reference-voice mappings provided by
                         the user.
        """
        try:
            job = self.job_manager.get_job(job_id)
            if job is None:
                logger.error("process_voice_replacement: job %s not found", job_id)
                return

            job_dir = self.job_manager.get_job_dir(job_id)

            # --- 1. Prepare reference voice mapping -------------------------
            self.job_manager.update_job(
                job_id,
                status=JobStatus.GENERATING_SPEECH,
                progress=0.70,
            )

            ref_map: dict[str, Path] = {}
            for assignment in assignments:
                ref_path = job_dir / "references" / assignment.reference_audio_filename
                ref_map[assignment.speaker_id] = ref_path

            # --- 2. Synthesise speech for every segment ---------------------
            segments = job.segments
            total_segments = len(segments)
            speech_segment_dicts: list[dict] = []

            for idx, segment in enumerate(segments):
                ref_audio = ref_map.get(segment.speaker_id)
                if ref_audio is None:
                    logger.warning(
                        "Job %s: no reference audio for speaker %s, skipping segment %d",
                        job_id,
                        segment.speaker_id,
                        idx,
                    )
                    continue

                target_duration = segment.end_time - segment.start_time
                seg_output = job_dir / "segments" / f"{idx}.wav"

                logger.debug(
                    "Job %s: synthesising segment %d/%d (speaker=%s, duration=%.2fs)",
                    job_id,
                    idx + 1,
                    total_segments,
                    segment.speaker_id,
                    target_duration,
                )

                await self.tts_engine.synthesize_segment(
                    text=segment.text,
                    reference_audio=ref_audio,
                    output_path=seg_output,
                    target_duration=target_duration,
                )

                speech_segment_dicts.append(
                    {
                        "audio_path": str(seg_output),
                        "target_start": segment.start_time,
                        "target_end": segment.end_time,
                        "speaker_id": segment.speaker_id,
                        "target_duration": target_duration,
                    }
                )

                # Progress: 0.70 -> 0.85 across segments.
                if total_segments > 0:
                    seg_progress = 0.70 + (0.15 * (idx + 1) / total_segments)
                    self.job_manager.update_job(job_id, progress=seg_progress)

            # --- 3. Align segments to original timing -----------------------
            self.job_manager.update_job(
                job_id,
                status=JobStatus.ALIGNING,
                progress=0.85,
            )

            segments_dir = job_dir / "segments"
            logger.info("Job %s: aligning %d segments", job_id, len(speech_segment_dicts))
            aligned_segments = await self.aligner.align_all_segments(
                speech_segment_dicts, segments_dir
            )

            # --- 4. Merge aligned speech with background music --------------
            self.job_manager.update_job(
                job_id,
                status=JobStatus.MERGING,
                progress=0.90,
            )

            original_audio = job_dir / "input" / "audio.wav"
            total_duration = get_duration(original_audio)

            # Locate the music / accompaniment track.
            music_path = self._find_music_path(job_dir)

            output_dir = job_dir / "output"
            output_dir.mkdir(parents=True, exist_ok=True)
            final_wav = output_dir / "final.wav"

            logger.info("Job %s: merging speech and music", job_id)
            await self.merger.merge_speech_and_music(
                speech_segments=aligned_segments,
                music_path=music_path,
                output_path=final_wav,
                total_duration=total_duration,
            )

            # --- 5. Rebuild video if the original input was video -----------
            output_file = str(final_wav)
            input_file = self._find_original_input(job_dir)

            if input_file is not None and self.extractor.is_video(input_file):
                final_video = output_dir / "final.mp4"
                logger.info("Job %s: rebuilding video with new audio", job_id)
                await self.merger.rebuild_video(
                    input_file, final_wav, final_video
                )
                output_file = str(final_video)

            # --- 6. Export additional formats --------------------------------
            logger.info("Job %s: exporting additional formats", job_id)
            await self.merger.export_formats(final_wav, output_dir)

            # --- 7. Mark complete -------------------------------------------
            self.job_manager.update_job(
                job_id,
                status=JobStatus.COMPLETED,
                progress=1.0,
                output_file=output_file,
            )

            logger.info("Job %s: voice replacement complete", job_id)

        except Exception as exc:
            logger.exception("Job %s: voice replacement failed", job_id)
            self.job_manager.update_job(
                job_id,
                status=JobStatus.FAILED,
                error=str(exc),
            )

    # ------------------------------------------------------------------
    # Standalone TTS
    # ------------------------------------------------------------------

    async def process_tts(
        self,
        job_id: str,
        text: str,
        ref_audio_path: Path | None = None,
        speed: float = 1.0,
        pitch: float = 1.0,
    ) -> Path:
        """Run a simple text-to-speech synthesis without the full pipeline.

        Args:
            job_id:         The job identifier.
            text:           Text to synthesise.
            ref_audio_path: Optional reference audio for voice cloning.
            speed:          Playback speed multiplier.
            pitch:          Pitch shift multiplier.

        Returns:
            Path to the generated audio file.

        Raises:
            Exception: Re-raised after marking the job as ``FAILED``.
        """
        try:
            job_dir = self.job_manager.get_job_dir(job_id)
            output_dir = job_dir / "output"
            output_dir.mkdir(parents=True, exist_ok=True)

            output_path = output_dir / "tts_output.wav"

            self.job_manager.update_job(
                job_id,
                status=JobStatus.GENERATING_SPEECH,
                progress=0.30,
            )

            logger.info("Job %s: synthesising TTS (%d chars)", job_id, len(text))
            await self.tts_engine.synthesize(
                text=text,
                output_path=output_path,
                reference_audio=ref_audio_path,
                speed=speed,
                pitch=pitch,
            )

            # Export to MP3 as well.
            await self.merger.export_formats(output_path, output_dir)

            self.job_manager.update_job(
                job_id,
                status=JobStatus.COMPLETED,
                progress=1.0,
                output_file=str(output_path),
            )

            logger.info("Job %s: TTS complete -> %s", job_id, output_path)
            return output_path

        except Exception as exc:
            logger.exception("Job %s: TTS processing failed", job_id)
            self.job_manager.update_job(
                job_id,
                status=JobStatus.FAILED,
                error=str(exc),
            )
            raise

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _find_music_path(job_dir: Path) -> Path:
        """Locate the accompaniment/music track inside the job directory.

        The separator may place the file under ``music/`` or ``vocals/``
        with varying names.  This helper performs a best-effort search.

        Args:
            job_dir: Root directory of the job.

        Returns:
            Path to the music/accompaniment audio file.

        Raises:
            FileNotFoundError: If no accompaniment file can be found.
        """
        candidates = [
            job_dir / "music",
            job_dir / "vocals",
            job_dir,
        ]

        for parent in candidates:
            if not parent.exists():
                continue
            for child in parent.iterdir():
                name_lower = child.name.lower()
                if child.is_file() and (
                    "accompaniment" in name_lower
                    or "music" in name_lower
                    or "no_vocals" in name_lower
                ):
                    return child

        # Fallback: look for any WAV file inside music/.
        music_dir = job_dir / "music"
        if music_dir.exists():
            for child in music_dir.iterdir():
                if child.suffix.lower() == ".wav":
                    return child

        raise FileNotFoundError(
            f"No accompaniment/music track found in {job_dir}"
        )

    @staticmethod
    def _find_original_input(job_dir: Path) -> Path | None:
        """Return the first non-WAV file in the job's ``input/`` folder.

        The original upload is saved with its original filename.  The
        pipeline also creates ``audio.wav`` in the same folder, so we
        skip that file.

        Args:
            job_dir: Root directory of the job.

        Returns:
            Path to the original upload, or ``None`` if not found.
        """
        input_dir = job_dir / "input"
        if not input_dir.exists():
            return None

        for child in input_dir.iterdir():
            if child.is_file() and child.name != "audio.wav":
                return child

        return None
