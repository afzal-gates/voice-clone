"""Audio merging and video rebuilding for the VoiceClone AI pipeline.

Combines regenerated speech segments with the separated background music
track, applies intelligent ducking so speech remains intelligible, and
optionally muxes the final audio back into the original video container.
"""

import asyncio
import logging
import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf

from app.config import settings

logger = logging.getLogger(__name__)


class AudioMerger:
    """Merge synthesized speech with background music and rebuild video.

    All public methods are ``async``.  CPU-bound DSP work runs on a thread
    via ``asyncio.to_thread``; FFmpeg operations run as async subprocesses.
    """

    # Ducking parameters
    _DUCK_FACTOR: float = 0.40  # music volume when speech is active
    _SPEECH_THRESHOLD_DB: float = -40.0  # amplitude below this is "silence"
    _CROSSFADE_DURATION: float = 0.015  # seconds, boundary crossfade length
    _NORMALIZATION_HEADROOM_DB: float = -1.0  # peak target after mixing

    # ------------------------------------------------------------------
    # Public: multi-segment merge with ducking
    # ------------------------------------------------------------------

    async def merge_speech_and_music(
        self,
        speech_segments: list[dict],
        music_path: Path,
        output_path: Path,
        total_duration: float,
    ) -> Path:
        """Merge multiple aligned speech segments with a background music track.

        Algorithm overview:

        1. Create a silent canvas of *total_duration* at ``settings.SAMPLE_RATE``.
        2. Load the music track (pad/trim to match canvas length).
        3. For each speech segment, load its audio and stamp it onto the
           canvas at the correct time offset (``target_start``).
        4. Build a ducking envelope: wherever speech amplitude exceeds
           ``_SPEECH_THRESHOLD_DB``, attenuate the music by ``_DUCK_FACTOR``.
        5. Mix: ``output = speech + ducked_music``.
        6. Normalize to ``_NORMALIZATION_HEADROOM_DB`` to prevent clipping.
        7. Write the result as WAV.

        Each segment dict must contain:

        * ``aligned_path`` (``Path``) -- WAV of the aligned speech.
        * ``target_start`` (``float``) -- start time in seconds.
        * ``target_end`` (``float``) -- end time in seconds.

        Args:
            speech_segments: List of segment dictionaries (see above).
            music_path: Path to the background music WAV file.
            output_path: Destination for the merged WAV.
            total_duration: Total output duration in seconds.

        Returns:
            *output_path* after writing the merged audio.
        """
        sr = settings.SAMPLE_RATE
        total_samples = int(total_duration * sr)

        result = await asyncio.to_thread(
            self._merge_speech_and_music_sync,
            speech_segments,
            music_path,
            total_samples,
            sr,
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(output_path), result, sr)
        logger.info(
            "Merged %d speech segments with music: %s (%.2fs)",
            len(speech_segments),
            output_path.name,
            total_duration,
        )
        return output_path

    def _merge_speech_and_music_sync(
        self,
        speech_segments: list[dict],
        music_path: Path,
        total_samples: int,
        sr: int,
    ) -> np.ndarray:
        """Synchronous implementation of the merge algorithm."""
        # 1. Empty canvas for speech
        speech_canvas = np.zeros(total_samples, dtype=np.float32)

        # 2. Load music
        music = self._load_and_fit(music_path, total_samples, sr)

        # 3. Stamp each speech segment onto the canvas
        fade_samples = max(1, int(self._CROSSFADE_DURATION * sr))
        for seg in speech_segments:
            aligned_path = Path(seg["aligned_path"])
            target_start: float = seg["target_start"]

            if not aligned_path.exists():
                logger.warning("Aligned file missing, skipping: %s", aligned_path)
                continue

            seg_audio, seg_sr = sf.read(str(aligned_path), dtype="float32")
            if seg_audio.ndim > 1:
                seg_audio = seg_audio.mean(axis=1)

            # Resample if needed
            if seg_sr != sr:
                import librosa  # noqa: WPS433
                seg_audio = librosa.resample(seg_audio, orig_sr=seg_sr, target_sr=sr)

            start_sample = int(target_start * sr)
            end_sample = start_sample + len(seg_audio)

            # Clamp to canvas bounds
            if start_sample < 0:
                seg_audio = seg_audio[-start_sample:]
                start_sample = 0
            if end_sample > total_samples:
                seg_audio = seg_audio[: total_samples - start_sample]
                end_sample = total_samples

            if len(seg_audio) == 0:
                continue

            # Apply short crossfade at boundaries to avoid clicks
            seg_audio = self._apply_boundary_fades(seg_audio, fade_samples)
            speech_canvas[start_sample:start_sample + len(seg_audio)] += seg_audio

        # 4. Build ducking envelope
        ducked_music = self._apply_ducking(speech_canvas, music, sr)

        # 5. Mix
        mixed = speech_canvas + ducked_music

        # 6. Normalize
        mixed = self._normalize(mixed, self._NORMALIZATION_HEADROOM_DB)

        return mixed

    # ------------------------------------------------------------------
    # Public: simple two-track merge
    # ------------------------------------------------------------------

    async def merge_simple(
        self,
        speech_path: Path,
        music_path: Path,
        output_path: Path,
    ) -> Path:
        """Mix a single speech track and a music track with basic ducking.

        Speech is kept at full volume; music is reduced to 40% wherever
        speech is active.

        Args:
            speech_path: Path to the speech WAV.
            music_path: Path to the music WAV.
            output_path: Destination WAV path.

        Returns:
            *output_path* after writing the mixed audio.
        """
        result = await asyncio.to_thread(
            self._merge_simple_sync, speech_path, music_path,
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(output_path), result, settings.SAMPLE_RATE)
        logger.info("Simple merge complete: %s", output_path.name)
        return output_path

    def _merge_simple_sync(
        self,
        speech_path: Path,
        music_path: Path,
    ) -> np.ndarray:
        """Synchronous simple merge."""
        sr = settings.SAMPLE_RATE

        speech, sp_sr = sf.read(str(speech_path), dtype="float32")
        if speech.ndim > 1:
            speech = speech.mean(axis=1)
        if sp_sr != sr:
            import librosa  # noqa: WPS433
            speech = librosa.resample(speech, orig_sr=sp_sr, target_sr=sr)

        total_samples = len(speech)
        music = self._load_and_fit(music_path, total_samples, sr)
        ducked_music = self._apply_ducking(speech, music, sr)
        mixed = speech + ducked_music
        return self._normalize(mixed, self._NORMALIZATION_HEADROOM_DB)

    # ------------------------------------------------------------------
    # Public: video rebuild
    # ------------------------------------------------------------------

    async def rebuild_video(
        self,
        original_video: Path,
        new_audio: Path,
        output_path: Path,
    ) -> Path:
        """Replace the audio track in a video file using FFmpeg.

        The video stream is copied without re-encoding (``-c:v copy``).  The
        new audio is encoded with the container's default audio codec.

        Args:
            original_video: Path to the source video file.
            new_audio: Path to the replacement audio (WAV).
            output_path: Destination path for the rebuilt video.

        Returns:
            *output_path* after FFmpeg completes.

        Raises:
            FileNotFoundError: If either input file is missing.
            RuntimeError: If FFmpeg returns a non-zero exit code.
        """
        if not original_video.exists():
            raise FileNotFoundError(f"Original video not found: {original_video}")
        if not new_audio.exists():
            raise FileNotFoundError(f"New audio not found: {new_audio}")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            settings.FFMPEG_PATH,
            "-y",
            "-i", str(original_video),
            "-i", str(new_audio),
            "-c:v", "copy",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",
            str(output_path),
        ]

        logger.info(
            "Rebuilding video: %s + %s -> %s",
            original_video.name,
            new_audio.name,
            output_path.name,
        )

        result = await asyncio.to_thread(
            subprocess.run, cmd, capture_output=True,
        )

        if result.returncode != 0:
            stderr_text = result.stderr.decode(errors="replace").strip()
            logger.error("FFmpeg video rebuild failed (rc=%d): %s", result.returncode, stderr_text)
            raise RuntimeError(
                f"FFmpeg video rebuild failed with exit code {result.returncode}: {stderr_text}"
            )

        logger.info("Video rebuild complete: %s", output_path.name)
        return output_path

    # ------------------------------------------------------------------
    # Public: export to multiple formats
    # ------------------------------------------------------------------

    async def export_formats(
        self,
        wav_path: Path,
        output_dir: Path,
    ) -> dict[str, Path]:
        """Export a WAV file to additional audio formats.

        Currently exports to MP3 using FFmpeg's ``libmp3lame`` encoder at
        VBR quality level 2 (~190 kbps).

        Args:
            wav_path: Source WAV file.
            output_dir: Directory for exported files.

        Returns:
            Mapping of format name to output path,
            e.g. ``{"wav": Path(...), "mp3": Path(...)}``.

        Raises:
            FileNotFoundError: If *wav_path* does not exist.
            RuntimeError: If FFmpeg encoding fails.
        """
        if not wav_path.exists():
            raise FileNotFoundError(f"WAV file not found: {wav_path}")

        output_dir.mkdir(parents=True, exist_ok=True)
        stem = wav_path.stem
        results: dict[str, Path] = {"wav": wav_path}

        # --- MP3 export ---------------------------------------------------
        mp3_path = output_dir / f"{stem}.mp3"
        cmd = [
            settings.FFMPEG_PATH,
            "-y",
            "-i", str(wav_path),
            "-codec:a", "libmp3lame",
            "-qscale:a", "2",
            str(mp3_path),
        ]

        logger.info("Exporting MP3: %s -> %s", wav_path.name, mp3_path.name)

        try:
            result = await asyncio.to_thread(
                subprocess.run, cmd, capture_output=True,
            )

            if result.returncode != 0:
                stderr_text = result.stderr.decode(errors="replace").strip()
                logger.warning("MP3 export failed (rc=%d): %s", result.returncode, stderr_text)
            else:
                results["mp3"] = mp3_path
                logger.info("MP3 export complete: %s", mp3_path.name)
        except FileNotFoundError:
            logger.warning(
                "FFmpeg not found at '%s' — skipping MP3 export. "
                "Install FFmpeg or set FFMPEG_PATH in .env",
                settings.FFMPEG_PATH,
            )

        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _load_and_fit(
        audio_path: Path,
        target_samples: int,
        sr: int,
    ) -> np.ndarray:
        """Load an audio file and pad or trim it to *target_samples*.

        Args:
            audio_path: Path to the audio file.
            target_samples: Desired number of samples.
            sr: Expected sample rate.

        Returns:
            1-D float32 array of exactly *target_samples* length.
        """
        if not audio_path.exists():
            logger.warning("Audio file not found, returning silence: %s", audio_path)
            return np.zeros(target_samples, dtype=np.float32)

        audio, file_sr = sf.read(str(audio_path), dtype="float32")
        if audio.ndim > 1:
            audio = audio.mean(axis=1)

        if file_sr != sr:
            import librosa  # noqa: WPS433
            audio = librosa.resample(audio, orig_sr=file_sr, target_sr=sr)

        current = len(audio)
        if current >= target_samples:
            return audio[:target_samples]

        # Pad with silence
        return np.concatenate([audio, np.zeros(target_samples - current, dtype=np.float32)])

    def _apply_ducking(
        self,
        speech: np.ndarray,
        music: np.ndarray,
        sr: int,
    ) -> np.ndarray:
        """Reduce music volume wherever speech is active.

        A binary speech-activity mask is computed by comparing the absolute
        amplitude of the speech signal against a threshold derived from
        ``_SPEECH_THRESHOLD_DB``.  The mask is smoothed with a short rolling
        window to avoid rapid on/off transitions.  Music samples under the
        mask are scaled by ``_DUCK_FACTOR``.

        Args:
            speech: 1-D float32 speech signal.
            music: 1-D float32 music signal (same length as *speech*).
            sr: Sample rate.

        Returns:
            A copy of *music* with ducking applied.
        """
        threshold = 10.0 ** (self._SPEECH_THRESHOLD_DB / 20.0)
        speech_active = np.abs(speech) > threshold

        # Smooth the mask with a short window to prevent rapid toggling.
        # Window size: ~20 ms at the given sample rate.
        window_size = max(1, int(0.02 * sr))
        if window_size > 1:
            kernel = np.ones(window_size, dtype=np.float32) / window_size
            smoothed = np.convolve(speech_active.astype(np.float32), kernel, mode="same")
            speech_active = smoothed > 0.3  # threshold after smoothing

        # Build gain envelope: 1.0 where silent, _DUCK_FACTOR where speech active
        gain = np.where(speech_active, self._DUCK_FACTOR, 1.0).astype(np.float32)

        return music * gain

    @staticmethod
    def _apply_boundary_fades(
        audio: np.ndarray,
        fade_samples: int,
    ) -> np.ndarray:
        """Apply short fade-in and fade-out to prevent clicks at segment edges.

        Args:
            audio: 1-D float32 audio array.
            fade_samples: Number of samples over which to fade.

        Returns:
            A copy of *audio* with fades applied.
        """
        audio = audio.copy()
        length = len(audio)
        fade_samples = min(fade_samples, length // 2)

        if fade_samples <= 0:
            return audio

        fade_in = np.linspace(0.0, 1.0, fade_samples, dtype=np.float32)
        fade_out = np.linspace(1.0, 0.0, fade_samples, dtype=np.float32)
        audio[:fade_samples] *= fade_in
        audio[-fade_samples:] *= fade_out
        return audio

    @staticmethod
    def _normalize(audio: np.ndarray, target_db: float = -1.0) -> np.ndarray:
        """Peak-normalize *audio* to *target_db* dBFS.

        Args:
            audio: 1-D float32 audio array.
            target_db: Target peak level in dB relative to full scale.

        Returns:
            A normalized copy of the audio. If the signal is silent,
            the original array is returned unchanged.
        """
        peak = np.max(np.abs(audio))
        if peak < 1e-8:
            return audio

        target_linear = 10.0 ** (target_db / 20.0)
        gain = target_linear / peak
        return audio * gain
