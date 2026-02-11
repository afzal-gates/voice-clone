"""Voice profile management with in-memory cache and file-system persistence.

Provides CRUD operations for saved voice profiles. Every mutation is
written through to a ``profile.json`` file inside the voice's storage
directory so that profiles survive application restarts.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from app.config import settings
from app.models import VoiceProfile

logger = logging.getLogger(__name__)


class VoiceManager:
    """Manage voice profiles with in-memory cache backed by JSON files."""

    def __init__(self) -> None:
        self._voices: dict[str, VoiceProfile] = {}
        self._voices_root: Path = settings.VOICES_DIR
        self._voices_root.mkdir(parents=True, exist_ok=True)
        self._load_all_voices()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_voice(self, name: str, description: str = "") -> VoiceProfile:
        """Create a new voice profile and persist it."""
        voice = VoiceProfile(name=name, description=description)
        voice_dir = self._voice_dir(voice.voice_id)
        voice_dir.mkdir(parents=True, exist_ok=True)
        self._voices[voice.voice_id] = voice
        self.save_voice(voice)
        logger.info("Voice profile created: id=%s name=%s", voice.voice_id, name)
        return voice

    def get_voice(self, voice_id: str) -> VoiceProfile | None:
        """Return voice by *voice_id*, falling back to disk if not cached."""
        if voice_id in self._voices:
            return self._voices[voice_id]
        voice = self.load_voice(voice_id)
        if voice is not None:
            self._voices[voice_id] = voice
        return voice

    def update_voice(self, voice_id: str, **kwargs: object) -> VoiceProfile:
        """Update fields on an existing voice profile and persist."""
        voice = self.get_voice(voice_id)
        if voice is None:
            raise ValueError(f"Voice not found: {voice_id}")
        for field, value in kwargs.items():
            if not hasattr(voice, field):
                logger.warning("Ignoring unknown field %r on voice %s", field, voice_id)
                continue
            setattr(voice, field, value)
        self._voices[voice_id] = voice
        self.save_voice(voice)
        return voice

    def list_voices(self) -> list[VoiceProfile]:
        """Return all known voices ordered by creation time (newest first)."""
        return sorted(
            self._voices.values(),
            key=lambda v: v.created_at,
            reverse=True,
        )

    def delete_voice(self, voice_id: str) -> bool:
        """Delete a voice profile from memory and disk."""
        if voice_id not in self._voices:
            if not self._voice_dir(voice_id).exists():
                return False
        self._voices.pop(voice_id, None)
        voice_dir = self._voice_dir(voice_id)
        if voice_dir.exists():
            shutil.rmtree(voice_dir, ignore_errors=True)
        logger.info("Voice profile deleted: %s", voice_id)
        return True

    def get_voice_dir(self, voice_id: str) -> Path:
        """Return the root directory for *voice_id*."""
        return self._voice_dir(voice_id)

    def get_audio_path(self, voice_id: str) -> Path | None:
        """Return the full path to the voice's audio file, or ``None``."""
        voice = self.get_voice(voice_id)
        if voice is None or not voice.audio_filename:
            return None
        audio_path = self._voice_dir(voice_id) / voice.audio_filename
        return audio_path if audio_path.exists() else None

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def save_voice(self, voice: VoiceProfile) -> None:
        """Serialise *voice* to its ``profile.json`` file on disk."""
        voice_dir = self._voice_dir(voice.voice_id)
        voice_dir.mkdir(parents=True, exist_ok=True)
        profile_file = voice_dir / "profile.json"
        try:
            profile_file.write_text(
                voice.model_dump_json(indent=2), encoding="utf-8"
            )
        except OSError:
            logger.exception("Failed to save voice %s to disk", voice.voice_id)

    def load_voice(self, voice_id: str) -> VoiceProfile | None:
        """Deserialise a voice profile from its ``profile.json`` on disk."""
        profile_file = self._voice_dir(voice_id) / "profile.json"
        if not profile_file.exists():
            return None
        try:
            raw = profile_file.read_text(encoding="utf-8")
            return VoiceProfile.model_validate_json(raw)
        except Exception:
            logger.exception("Failed to load voice from %s", profile_file)
            return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _voice_dir(self, voice_id: str) -> Path:
        return self._voices_root / voice_id

    def _load_all_voices(self) -> None:
        """Scan voices directory and load all persisted profiles into memory."""
        if not self._voices_root.exists():
            return
        loaded = 0
        for child in self._voices_root.iterdir():
            if not child.is_dir():
                continue
            voice = self.load_voice(child.name)
            if voice is not None:
                self._voices[voice.voice_id] = voice
                loaded += 1
        if loaded:
            logger.info(
                "Loaded %d existing voice profile(s) from %s",
                loaded,
                self._voices_root,
            )
