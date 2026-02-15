"""Music video generation engine with waveform visualization.

Provides video generation from audio files with animated waveform displays,
progress bars, and metadata overlays.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import soundfile as sf

logger = logging.getLogger(__name__)


class VideoGenerator:
    """Music video generation engine.

    Creates animated music videos with waveform visualizations, progress bars,
    and text overlays from audio files. Uses OpenCV for rendering and FFmpeg
    for final audio/video merging.

    Typical usage::

        generator = VideoGenerator()
        generator.generate_video(
            audio_path=Path("song.wav"),
            output_path=Path("video.mp4"),
            title="My Song",
            artist="AI Artist",
            style="waveform"
        )
    """

    def __init__(self, fps: int = 30, resolution: tuple[int, int] = (1920, 1080)) -> None:
        """Initialize the video generator.

        Args:
            fps: Video frame rate (frames per second). Default: 30.
            resolution: Video resolution (width, height). Default: 1920x1080.
        """
        self._fps = fps
        self._width, self._height = resolution
        self._bg_color = (20, 20, 30)  # Dark blue background
        self._waveform_color = (100, 200, 255)  # Light blue
        self._progress_color = (255, 100, 100)  # Red
        self._text_color = (255, 255, 255)  # White

        logger.debug(
            "VideoGenerator created (fps=%d, resolution=%dx%d)",
            fps,
            self._width,
            self._height,
        )

    def generate_video(
        self,
        audio_path: Path,
        output_path: Path,
        title: str = "Untitled",
        artist: str = "Unknown Artist",
        style: str = "waveform",
    ) -> Path:
        """Generate music video with visualization.

        Creates an animated video with waveform visualization, progress bar,
        and metadata text overlays, then merges with audio using FFmpeg.

        Args:
            audio_path: Path to the audio file (WAV, MP3, etc.).
            output_path: Path where video will be saved (.mp4).
            title: Song title for display. Default: "Untitled".
            artist: Artist name for display. Default: "Unknown Artist".
            style: Visualization style. Currently supports: "waveform".
                  Default: "waveform".

        Returns:
            Path to the generated video file.

        Raises:
            FileNotFoundError: If audio file doesn't exist.
            RuntimeError: If video generation or FFmpeg merging fails.
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        logger.info(
            "Generating music video: %s -> %s (style=%s)",
            audio_path.name,
            output_path.name,
            style,
        )

        try:
            # Load audio file
            audio, sr = sf.read(str(audio_path), dtype="float32")

            # Handle stereo audio (convert to mono for visualization)
            if audio.ndim == 2:
                audio = audio.mean(axis=1)

            duration = len(audio) / sr
            total_frames = int(duration * self._fps)

            logger.info(
                "Audio loaded: %.2fs, sr=%d Hz, %d frames to generate",
                duration,
                sr,
                total_frames,
            )

            # Create temporary video file (without audio)
            temp_video = output_path.with_suffix(".temp.mp4")

            # Initialize video writer
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(
                str(temp_video),
                fourcc,
                self._fps,
                (self._width, self._height),
            )

            if not writer.isOpened():
                raise RuntimeError("Failed to initialize video writer")

            # Generate frames
            logger.info("Rendering %d frames...", total_frames)

            for frame_idx in range(total_frames):
                time_sec = frame_idx / self._fps

                # Generate frame based on style
                if style == "waveform":
                    frame = self._generate_waveform_frame(
                        audio, sr, time_sec, duration, title, artist
                    )
                else:
                    logger.warning("Unknown style '%s', using waveform", style)
                    frame = self._generate_waveform_frame(
                        audio, sr, time_sec, duration, title, artist
                    )

                writer.write(frame)

                # Log progress
                if (frame_idx + 1) % (self._fps * 5) == 0:  # Every 5 seconds
                    progress = (frame_idx + 1) / total_frames * 100
                    logger.info("Rendering progress: %.1f%%", progress)

            writer.release()
            logger.info("Video rendering complete: %s", temp_video.name)

            # Merge audio and video using FFmpeg
            logger.info("Merging audio and video with FFmpeg...")
            self._merge_audio_video(audio_path, temp_video, output_path)

            # Clean up temporary file
            if temp_video.exists():
                temp_video.unlink()
                logger.debug("Temporary video deleted: %s", temp_video.name)

            file_size = output_path.stat().st_size / (1024 * 1024)  # MB
            logger.info(
                "Music video generated: %s (%.2f MB, %.2fs)",
                output_path.name,
                file_size,
                duration,
            )

            return output_path

        except Exception as exc:
            logger.error("Video generation failed: %s", exc)
            raise RuntimeError(f"Cannot generate video: {exc}") from exc

    def _generate_waveform_frame(
        self,
        audio: np.ndarray,
        sr: int,
        time_sec: float,
        total_duration: float,
        title: str,
        artist: str,
    ) -> np.ndarray:
        """Generate single waveform visualization frame.

        Creates a frame with animated waveform, progress bar, and text overlays.

        Args:
            audio: Audio samples array (mono, float32).
            sr: Sample rate.
            time_sec: Current time position in seconds.
            total_duration: Total audio duration in seconds.
            title: Song title text.
            artist: Artist name text.

        Returns:
            BGR image frame (numpy array, uint8, shape=(height, width, 3)).
        """
        # Create blank frame with background color
        frame = np.full(
            (self._height, self._width, 3),
            self._bg_color,
            dtype=np.uint8,
        )

        # Calculate waveform window (1 second of audio centered on current time)
        window_duration = 1.0  # seconds
        window_samples = int(window_duration * sr)
        center_sample = int(time_sec * sr)
        start_sample = max(0, center_sample - window_samples // 2)
        end_sample = min(len(audio), center_sample + window_samples // 2)

        # Extract waveform segment
        waveform = audio[start_sample:end_sample]

        # Draw waveform
        if len(waveform) > 0:
            # Calculate x and y coordinates for waveform line
            x_coords = np.linspace(0, self._width, len(waveform), dtype=np.int32)
            y_center = self._height // 2
            y_scale = 300  # Amplitude scaling factor
            y_coords = (y_center - waveform * y_scale).astype(np.int32)

            # Clip y coordinates to valid range
            y_coords = np.clip(y_coords, 0, self._height - 1)

            # Draw waveform line
            for i in range(len(x_coords) - 1):
                cv2.line(
                    frame,
                    (x_coords[i], y_coords[i]),
                    (x_coords[i + 1], y_coords[i + 1]),
                    self._waveform_color,
                    2,
                )

        # Draw progress bar
        progress = time_sec / total_duration if total_duration > 0 else 0
        bar_y = self._height - 50
        bar_height = 20
        bar_width = self._width - 100
        bar_x = 50

        # Background bar (gray)
        cv2.rectangle(
            frame,
            (bar_x, bar_y),
            (bar_x + bar_width, bar_y + bar_height),
            (60, 60, 70),
            -1,
        )

        # Progress bar (colored)
        progress_width = int(bar_width * progress)
        if progress_width > 0:
            cv2.rectangle(
                frame,
                (bar_x, bar_y),
                (bar_x + progress_width, bar_y + bar_height),
                self._progress_color,
                -1,
            )

        # Draw time indicators
        current_time_str = self._format_time(time_sec)
        total_time_str = self._format_time(total_duration)
        time_text = f"{current_time_str} / {total_time_str}"

        cv2.putText(
            frame,
            time_text,
            (bar_x + bar_width // 2 - 50, bar_y - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            self._text_color,
            1,
            cv2.LINE_AA,
        )

        # Draw title (top center)
        title_size = cv2.getTextSize(
            title,
            cv2.FONT_HERSHEY_SIMPLEX,
            1.5,
            2,
        )[0]
        title_x = (self._width - title_size[0]) // 2

        cv2.putText(
            frame,
            title,
            (title_x, 80),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.5,
            self._text_color,
            2,
            cv2.LINE_AA,
        )

        # Draw artist name (below title)
        artist_size = cv2.getTextSize(
            artist,
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            2,
        )[0]
        artist_x = (self._width - artist_size[0]) // 2

        cv2.putText(
            frame,
            artist,
            (artist_x, 130),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (200, 200, 200),
            2,
            cv2.LINE_AA,
        )

        return frame

    def _merge_audio_video(
        self,
        audio_path: Path,
        video_path: Path,
        output_path: Path,
    ) -> None:
        """Merge audio and video files using FFmpeg.

        Args:
            audio_path: Path to audio file.
            video_path: Path to video file (no audio).
            output_path: Path for merged output.

        Raises:
            RuntimeError: If FFmpeg command fails.
        """
        try:
            # FFmpeg command to merge audio and video
            cmd = [
                "ffmpeg",
                "-y",  # Overwrite output file
                "-i", str(video_path),  # Video input
                "-i", str(audio_path),  # Audio input
                "-c:v", "libx264",  # Video codec
                "-preset", "medium",  # Encoding preset
                "-crf", "23",  # Quality (lower = better, 18-28 recommended)
                "-c:a", "aac",  # Audio codec
                "-b:a", "192k",  # Audio bitrate
                "-shortest",  # Finish when shortest input ends
                str(output_path),
            ]

            logger.debug("FFmpeg command: %s", " ".join(cmd))

            # Run FFmpeg
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
            )

            logger.debug("FFmpeg completed successfully")

        except subprocess.CalledProcessError as exc:
            logger.error("FFmpeg failed: %s", exc.stderr)
            raise RuntimeError(f"FFmpeg merge failed: {exc.stderr}") from exc
        except FileNotFoundError:
            raise RuntimeError(
                "FFmpeg not found. Please install FFmpeg and add it to PATH"
            )

    def _format_time(self, seconds: float) -> str:
        """Format time in seconds as MM:SS.

        Args:
            seconds: Time in seconds.

        Returns:
            Formatted time string (e.g., "03:45").
        """
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"
