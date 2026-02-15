"""Complete song generation orchestrator.

Coordinates all pipeline components to generate complete songs with instrumentals,
vocals, mixing, MIDI export, and video generation.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Dict, Optional

import soundfile as sf

from app.pipeline.audio_mixer import AudioMixer
from app.pipeline.midi_exporter import MIDIExporter
from app.pipeline.music_engine import MusicEngine
from app.pipeline.singing_engine import SingingEngine
from app.pipeline.video_generator import VideoGenerator

logger = logging.getLogger(__name__)


class SongGenerator:
    """Complete AI song generation orchestrator.

    Coordinates all pipeline components to generate professional songs from
    lyrics and musical parameters, producing mixed audio, separate tracks,
    MIDI files, and optional music videos.

    Pipeline stages:
    1. Generate instrumental music (MusicEngine)
    2. Generate singing vocals (SingingEngine)
    3. Mix instrumental + vocals (AudioMixer)
    4. Export MP3 formats (format conversion)
    5. Export MIDI melody (MIDIExporter)
    6. Generate music video (VideoGenerator) - optional

    Typical usage::

        generator = SongGenerator()
        outputs = await generator.generate_complete_song(
            lyrics="Your song lyrics here",
            genre="pop",
            mood="happy",
            bpm=120,
            instruments=["piano", "guitar"],
            vocal_type="female",
            language="en",
            output_dir=Path("output/"),
            song_title="My Song",
            artist_name="AI Artist",
            generate_video=True
        )
    """

    def __init__(self) -> None:
        """Initialize the song generator with all pipeline components."""
        self.music_engine = MusicEngine()
        self.singing_engine = SingingEngine()
        self.audio_mixer = AudioMixer()
        self.midi_exporter = MIDIExporter()
        self.video_generator = VideoGenerator()

        logger.debug("SongGenerator initialized")

    async def generate_complete_song(
        self,
        lyrics: str,
        genre: str,
        mood: str,
        bpm: int,
        instruments: Optional[list[str]],
        vocal_type: str,
        language: str,
        output_dir: Path,
        song_title: str = "Untitled Song",
        artist_name: str = "AI Artist",
        generate_video: bool = False,
        duration: float = 30.0,
    ) -> Dict[str, Path]:
        """Generate complete AI song with all outputs.

        Orchestrates the full pipeline from lyrics to finished song with
        instrumental, vocals, mixed audio, MIDI, and optional video.

        Args:
            lyrics: Song lyrics text.
            genre: Music genre (pop, rock, edm, etc.).
            mood: Emotional mood (happy, sad, energetic, etc.).
            bpm: Tempo in beats per minute (60-200).
            instruments: List of instruments to feature (optional).
            vocal_type: Voice type (male, female, choir, ai).
            language: Language code for vocals (en, es, fr, etc.).
            output_dir: Directory where all outputs will be saved.
            song_title: Song title for metadata and video. Default: "Untitled Song".
            artist_name: Artist name for metadata and video. Default: "AI Artist".
            generate_video: Whether to generate music video. Default: False.
            duration: Song duration in seconds (5-60). Default: 30.

        Returns:
            Dictionary mapping output types to file paths:
            {
                "instrumental_wav": Path,
                "instrumental_mp3": Path,
                "vocals_wav": Path,
                "vocals_mp3": Path,
                "mixed_song_wav": Path,
                "mixed_song_mp3": Path,
                "midi": Path,
                "video": Path  # only if generate_video=True
            }

        Raises:
            ValueError: If inputs are invalid.
            RuntimeError: If any generation step fails.
        """
        logger.info(
            "Starting complete song generation: '%s' by %s (%s, %s, %d BPM)",
            song_title,
            artist_name,
            genre,
            mood,
            bpm,
        )

        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)

        outputs: Dict[str, Path] = {}

        try:
            # ===================================================================
            # STEP 1: Generate Instrumental
            # ===================================================================
            logger.info("[1/6] Generating instrumental music...")

            instrumental_path = output_dir / "instrumental.wav"

            await self.music_engine.generate(
                prompt="",  # Enhanced prompt built from genre/mood/bpm/instruments
                output_path=instrumental_path,
                duration=duration,
                genre=genre,
                mood=mood,
                bpm=bpm,
                instruments=instruments,
            )

            outputs["instrumental_wav"] = instrumental_path
            logger.info("[1/6] Instrumental generated: %s", instrumental_path.name)

            # ===================================================================
            # STEP 2: Generate Vocals
            # ===================================================================
            logger.info("[2/6] Generating singing vocals...")

            vocals_path = output_dir / "vocals.wav"

            await self.singing_engine.synthesize(
                lyrics=lyrics,
                melody=None,  # Auto-generate melody
                tempo=bpm,
                output_path=vocals_path,
                language=language,
                vocal_type=vocal_type,
            )

            outputs["vocals_wav"] = vocals_path
            logger.info("[2/6] Vocals generated: %s", vocals_path.name)

            # ===================================================================
            # STEP 3: Mix Tracks
            # ===================================================================
            logger.info("[3/6] Mixing instrumental and vocals...")

            mixed_path = output_dir / "mixed_song.wav"

            await self.audio_mixer.mix(
                tts_audio_path=vocals_path,
                music_audio_path=instrumental_path,
                output_path=mixed_path,
                tts_volume=0.85,  # Vocals louder
                music_volume=0.40,  # Instrumental as backing
            )

            outputs["mixed_song_wav"] = mixed_path
            logger.info("[3/6] Tracks mixed: %s", mixed_path.name)

            # ===================================================================
            # STEP 4: Export MP3 Formats
            # ===================================================================
            logger.info("[4/6] Converting to MP3 format...")

            for track_name in ["instrumental", "vocals", "mixed_song"]:
                wav_path = outputs[f"{track_name}_wav"]
                mp3_path = wav_path.with_suffix(".mp3")

                await asyncio.to_thread(self._convert_to_mp3, wav_path, mp3_path)

                outputs[f"{track_name}_mp3"] = mp3_path
                logger.debug("Converted to MP3: %s", mp3_path.name)

            logger.info("[4/6] MP3 conversion complete")

            # ===================================================================
            # STEP 5: Export MIDI
            # ===================================================================
            logger.info("[5/6] Exporting MIDI file...")

            midi_path = output_dir / "melody.mid"

            # Get the pitch contour from the singing engine's melody parser
            # TODO: Implement pitch contour retrieval from singing engine
            try:
                pitch_contour = getattr(self.singing_engine._melody_parser, 'get_last_pitch_contour', lambda: None)()
            except Exception as e:
                logger.warning("Could not retrieve pitch contour: %s", e)
                pitch_contour = None

            if pitch_contour and hasattr(pitch_contour, 'notes') and len(pitch_contour.notes) > 0:
                await asyncio.to_thread(
                    self.midi_exporter.export_midi,
                    pitch_contour,
                    midi_path,
                    tempo=bpm,
                )

                outputs["midi"] = midi_path
                logger.info("[5/6] MIDI exported: %s", midi_path.name)
            else:
                logger.warning("[5/6] No melody available, skipping MIDI export")

            # ===================================================================
            # STEP 6: Generate Video (Optional)
            # ===================================================================
            if generate_video:
                logger.info("[6/6] Generating music video...")

                video_path = output_dir / "music_video.mp4"

                await asyncio.to_thread(
                    self.video_generator.generate_video,
                    audio_path=mixed_path,
                    output_path=video_path,
                    title=song_title,
                    artist=artist_name,
                )

                outputs["video"] = video_path
                logger.info("[6/6] Music video generated: %s", video_path.name)
            else:
                logger.info("[6/6] Skipping video generation (not requested)")

            # ===================================================================
            # Complete
            # ===================================================================
            logger.info(
                "Song generation complete: %d outputs generated",
                len(outputs),
            )

            return outputs

        except Exception as exc:
            logger.error("Song generation failed: %s", exc)
            raise RuntimeError(f"Cannot generate complete song: {exc}") from exc

    def _convert_to_mp3(self, wav_path: Path, mp3_path: Path, bitrate: str = "192k") -> None:
        """Convert WAV to MP3 using pydub/ffmpeg.

        Args:
            wav_path: Input WAV file path.
            mp3_path: Output MP3 file path.
            bitrate: MP3 bitrate (e.g., "192k", "320k"). Default: "192k".

        Raises:
            RuntimeError: If conversion fails.
        """
        try:
            from pydub import AudioSegment

            # Load WAV
            audio = AudioSegment.from_wav(str(wav_path))

            # Export as MP3
            audio.export(
                str(mp3_path),
                format="mp3",
                bitrate=bitrate,
                parameters=["-q:a", "2"],  # VBR quality setting (0-9, 2 is good)
            )

            logger.debug(
                "Converted %s -> %s (%s)",
                wav_path.name,
                mp3_path.name,
                bitrate,
            )

        except Exception as exc:
            logger.error("MP3 conversion failed: %s", exc)
            raise RuntimeError(f"Cannot convert to MP3: {exc}") from exc

    async def generate_instrumental_only(
        self,
        genre: str,
        mood: str,
        bpm: int,
        instruments: Optional[list[str]],
        output_dir: Path,
        duration: float = 30.0,
    ) -> Dict[str, Path]:
        """Generate instrumental music only (no vocals).

        Simplified pipeline for background music generation.

        Args:
            genre: Music genre.
            mood: Emotional mood.
            bpm: Tempo.
            instruments: List of instruments.
            output_dir: Output directory.
            duration: Duration in seconds (5-60). Default: 30.

        Returns:
            Dictionary with "instrumental_wav" and "instrumental_mp3" paths.
        """
        logger.info("Generating instrumental only: %s %s at %d BPM", mood, genre, bpm)

        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate instrumental
        wav_path = output_dir / "instrumental.wav"
        await self.music_engine.generate(
            prompt="",
            output_path=wav_path,
            duration=duration,
            genre=genre,
            mood=mood,
            bpm=bpm,
            instruments=instruments,
        )

        # Convert to MP3
        mp3_path = wav_path.with_suffix(".mp3")
        await asyncio.to_thread(self._convert_to_mp3, wav_path, mp3_path)

        return {
            "instrumental_wav": wav_path,
            "instrumental_mp3": mp3_path,
        }

    async def generate_vocals_only(
        self,
        lyrics: str,
        bpm: int,
        vocal_type: str,
        language: str,
        output_dir: Path,
    ) -> Dict[str, Path]:
        """Generate singing vocals only (no instrumental).

        Simplified pipeline for acapella generation.

        Args:
            lyrics: Song lyrics.
            bpm: Tempo.
            vocal_type: Voice type.
            language: Language code.
            output_dir: Output directory.

        Returns:
            Dictionary with "vocals_wav", "vocals_mp3", and "midi" paths.
        """
        logger.info("Generating vocals only: %s voice, language=%s", vocal_type, language)

        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate vocals
        wav_path = output_dir / "vocals.wav"
        await self.singing_engine.synthesize(
            lyrics=lyrics,
            melody=None,
            tempo=bpm,
            output_path=wav_path,
            language=language,
            vocal_type=vocal_type,
        )

        # Convert to MP3
        mp3_path = wav_path.with_suffix(".mp3")
        await asyncio.to_thread(self._convert_to_mp3, wav_path, mp3_path)

        # Export MIDI
        outputs = {
            "vocals_wav": wav_path,
            "vocals_mp3": mp3_path,
        }

        pitch_contour = self.singing_engine._melody_parser.get_last_pitch_contour()
        if pitch_contour and len(pitch_contour.notes) > 0:
            midi_path = output_dir / "melody.mid"
            await asyncio.to_thread(
                self.midi_exporter.export_midi,
                pitch_contour,
                midi_path,
                tempo=bpm,
            )
            outputs["midi"] = midi_path

        return outputs
