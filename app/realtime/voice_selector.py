"""Voice selection and management for real-time voice changing.

Manages voice profile switching, hotkey assignment, and voice library organization.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from app.services.voice_manager import VoiceManager

logger = logging.getLogger(__name__)


class VoiceSelector:
    """Manages voice profile selection for real-time voice changing.

    Similar to Voicemod's voice library browser, this component handles:
    - Voice profile loading and caching
    - Real-time voice switching
    - Hotkey management
    - Voice categorization and search
    """

    def __init__(self, voice_manager: VoiceManager):
        """Initialize voice selector.

        Args:
            voice_manager: Voice manager instance for accessing saved voices
        """
        self.voice_manager = voice_manager
        self.current_voice_id: Optional[str] = None
        self.hotkeys: dict[str, str] = {}  # voice_id -> hotkey mapping
        self._voice_embeddings: dict[str, any] = {}  # Cached voice embeddings

    def get_voice_library(self) -> list[dict]:
        """Get all available voices for UI display.

        Returns:
            List of voice profile dicts with metadata for UI rendering
        """
        voices = self.voice_manager.list_voices()
        result = []

        for voice in voices:
            audio_path = self.voice_manager.get_audio_path(voice.voice_id)
            result.append({
                "id": voice.voice_id,
                "name": voice.name,
                "duration": voice.duration,
                "sample_rate": voice.sample_rate,
                "audio_path": str(audio_path) if audio_path else "",
                "category": self._get_voice_category(voice.name),
                "hotkey": self.hotkeys.get(voice.voice_id),
            })

        return result

    def select_voice(self, voice_id: str) -> dict:
        """Switch to a different voice profile.

        Args:
            voice_id: ID of voice profile to activate

        Returns:
            Voice profile data

        Raises:
            ValueError: If voice_id not found
        """
        voice = self.voice_manager.get_voice(voice_id)
        if not voice:
            raise ValueError(f"Voice not found: {voice_id}")

        logger.info(f"Switching to voice: {voice.name} ({voice_id})")
        self.current_voice_id = voice_id

        audio_path = self.voice_manager.get_audio_path(voice_id)
        return {
            "id": voice.voice_id,
            "name": voice.name,
            "audio_path": str(audio_path) if audio_path else "",
        }

    def get_current_voice(self) -> Optional[dict]:
        """Get currently selected voice profile.

        Returns:
            Current voice profile data or None
        """
        if not self.current_voice_id:
            return None

        voice = self.voice_manager.get_voice(self.current_voice_id)
        if not voice:
            return None

        audio_path = self.voice_manager.get_audio_path(self.current_voice_id)
        return {
            "id": voice.voice_id,
            "name": voice.name,
            "audio_path": str(audio_path) if audio_path else "",
        }

    def assign_hotkey(self, voice_id: str, hotkey: str) -> None:
        """Assign a hotkey to a voice profile.

        Args:
            voice_id: Voice profile ID
            hotkey: Hotkey string (e.g., "F1", "Ctrl+1")
        """
        self.hotkeys[voice_id] = hotkey
        logger.info(f"Assigned hotkey {hotkey} to voice {voice_id}")

    def get_voice_by_hotkey(self, hotkey: str) -> Optional[str]:
        """Get voice ID for a hotkey.

        Args:
            hotkey: Hotkey string

        Returns:
            Voice ID or None
        """
        for voice_id, key in self.hotkeys.items():
            if key == hotkey:
                return voice_id
        return None

    def _get_voice_category(self, voice_name: str) -> str:
        """Categorize voice based on name/metadata.

        Args:
            voice_name: Name of voice profile

        Returns:
            Category name (e.g., "custom", "realistic", "character")
        """
        # Simple categorization based on name
        # Can be enhanced with metadata or AI classification
        name_lower = voice_name.lower()

        if any(char in name_lower for char in ["speaker", "person", "voice"]):
            return "realistic"
        elif any(char in name_lower for char in ["robot", "alien", "monster"]):
            return "character"
        else:
            return "custom"

    def search_voices(self, query: str) -> list[dict]:
        """Search voices by name or category.

        Args:
            query: Search query string

        Returns:
            List of matching voice profiles
        """
        all_voices = self.get_voice_library()
        query_lower = query.lower()

        return [
            v for v in all_voices
            if query_lower in v["name"].lower()
            or query_lower in v.get("category", "").lower()
        ]

    def get_voices_by_category(self, category: str) -> list[dict]:
        """Get voices filtered by category.

        Args:
            category: Category name

        Returns:
            List of voice profiles in category
        """
        all_voices = self.get_voice_library()
        return [v for v in all_voices if v.get("category") == category]
