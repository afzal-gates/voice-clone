"""Soundboard system for background sounds and effects.

Allows playing background sounds, sound effects, and audio clips
during real-time voice processing.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import numpy as np
import soundfile as sf

logger = logging.getLogger(__name__)


class Soundboard:
    """Soundboard for playing background sounds and effects."""

    def __init__(self, sample_rate: int = 16000):
        """Initialize soundboard.

        Args:
            sample_rate: Target sample rate for audio playback
        """
        self.sample_rate = sample_rate
        self._loaded_sounds: dict[str, np.ndarray] = {}
        self._current_sound: Optional[np.ndarray] = None
        self._sound_position = 0
        self._volume = 0.5  # 0.0 to 1.0

        logger.info("Soundboard initialized")

    def load_sound(self, sound_id: str, file_path: str | Path) -> None:
        """Load a sound file into the soundboard.

        Args:
            sound_id: Identifier for the sound
            file_path: Path to audio file

        Raises:
            FileNotFoundError: If file doesn't exist
            RuntimeError: If file cannot be loaded
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Sound file not found: {file_path}")

        try:
            # Load audio file
            audio, sr = sf.read(str(file_path), dtype=np.float32)

            # Convert to mono if stereo
            if audio.ndim > 1:
                audio = audio.mean(axis=1)

            # Resample if needed
            if sr != self.sample_rate:
                from scipy import signal

                audio = signal.resample(
                    audio, int(len(audio) * self.sample_rate / sr)
                )

            # Store in memory
            self._loaded_sounds[sound_id] = audio.astype(np.float32)
            logger.info(f"Loaded sound: {sound_id} ({len(audio)} samples, {sr} Hz)")

        except Exception as e:
            raise RuntimeError(f"Failed to load sound {sound_id}: {e}") from e

    def play_sound(self, sound_id: str, loop: bool = False) -> None:
        """Start playing a loaded sound.

        Args:
            sound_id: Sound identifier to play
            loop: Whether to loop the sound

        Raises:
            KeyError: If sound not loaded
        """
        if sound_id not in self._loaded_sounds:
            raise KeyError(f"Sound '{sound_id}' not loaded")

        self._current_sound = self._loaded_sounds[sound_id]
        self._sound_position = 0
        self._loop = loop

        logger.info(f"Playing sound: {sound_id} (loop={loop})")

    def stop_sound(self) -> None:
        """Stop currently playing sound."""
        if self._current_sound is not None:
            logger.info("Stopping sound")
            self._current_sound = None
            self._sound_position = 0

    def set_volume(self, volume: float) -> None:
        """Set soundboard volume.

        Args:
            volume: Volume level (0.0 to 1.0)
        """
        self._volume = np.clip(volume, 0.0, 1.0)
        logger.debug(f"Volume set to {self._volume}")

    def get_samples(self, num_samples: int) -> np.ndarray:
        """Get next samples from currently playing sound.

        Args:
            num_samples: Number of samples to retrieve

        Returns:
            Audio samples (zeros if no sound playing)
        """
        if self._current_sound is None:
            return np.zeros(num_samples, dtype=np.float32)

        # Get samples from current position
        end_pos = min(self._sound_position + num_samples, len(self._current_sound))
        samples = self._current_sound[self._sound_position : end_pos].copy()

        # Apply volume
        samples *= self._volume

        # Handle end of sound
        remaining = num_samples - len(samples)
        if remaining > 0:
            if self._loop:
                # Loop back to beginning
                self._sound_position = 0
                samples = np.concatenate([samples, self.get_samples(remaining)])
            else:
                # Stop and pad with zeros
                self._current_sound = None
                self._sound_position = 0
                samples = np.pad(samples, (0, remaining))
        else:
            self._sound_position = end_pos

        return samples

    def mix_with_input(self, audio: np.ndarray) -> np.ndarray:
        """Mix soundboard output with input audio.

        Args:
            audio: Input audio samples

        Returns:
            Mixed audio (input + soundboard)
        """
        sound_samples = self.get_samples(len(audio))
        mixed = audio + sound_samples

        # Prevent clipping
        mixed = np.clip(mixed, -1.0, 1.0)

        return mixed

    def is_playing(self) -> bool:
        """Check if a sound is currently playing.

        Returns:
            True if sound is playing
        """
        return self._current_sound is not None

    def list_loaded_sounds(self) -> list[str]:
        """Get list of loaded sound IDs.

        Returns:
            List of sound identifiers
        """
        return list(self._loaded_sounds.keys())

    def unload_sound(self, sound_id: str) -> None:
        """Unload a sound from memory.

        Args:
            sound_id: Sound identifier to unload
        """
        if sound_id in self._loaded_sounds:
            del self._loaded_sounds[sound_id]
            logger.info(f"Unloaded sound: {sound_id}")

    def clear_all(self) -> None:
        """Clear all loaded sounds from memory."""
        self._loaded_sounds.clear()
        self.stop_sound()
        logger.info("Cleared all sounds from soundboard")


# Predefined sound effect metadata (files would need to be added to project)
SOUND_EFFECTS = {
    "applause": {
        "name": "Applause",
        "description": "Clapping and cheering",
        "icon": "👏",
        "category": "reactions",
    },
    "drumroll": {
        "name": "Drum Roll",
        "description": "Suspenseful drum roll",
        "icon": "🥁",
        "category": "effects",
    },
    "airhorn": {
        "name": "Air Horn",
        "description": "Loud air horn blast",
        "icon": "📯",
        "category": "effects",
    },
    "crickets": {
        "name": "Crickets",
        "description": "Awkward silence",
        "icon": "🦗",
        "category": "reactions",
    },
    "laugh": {
        "name": "Laugh Track",
        "description": "Audience laughter",
        "icon": "😂",
        "category": "reactions",
    },
    "sad_trombone": {
        "name": "Sad Trombone",
        "description": "Wah wah waaaah",
        "icon": "🎺",
        "category": "reactions",
    },
    "alarm": {
        "name": "Alarm",
        "description": "Warning alarm",
        "icon": "🚨",
        "category": "alerts",
    },
    "bell": {
        "name": "Bell",
        "description": "Ding ding!",
        "icon": "🔔",
        "category": "alerts",
    },
}


def get_sound_effects_list() -> list[dict]:
    """Get list of available sound effects.

    Returns:
        List of sound effect metadata
    """
    effects = []
    for sound_id, data in SOUND_EFFECTS.items():
        effects.append({
            "id": sound_id,
            "name": data["name"],
            "description": data["description"],
            "icon": data["icon"],
            "category": data["category"],
        })
    return effects
