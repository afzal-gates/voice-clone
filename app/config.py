"""Central configuration for VoiceClone AI platform.

Reads all settings from environment variables with sensible defaults.
Uses python-dotenv for .env file support. No pydantic BaseSettings dependency.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings loaded from environment variables.

    All configuration values are read from ``os.getenv`` at instantiation time.
    A ``.env`` file placed in the project root is automatically loaded via
    ``python-dotenv`` before any lookups occur.

    Attributes:
        APP_NAME: Display name of the application.
        APP_VERSION: Semantic version string.
        HOST: Bind address for the ASGI server.
        PORT: Bind port for the ASGI server.
        DEBUG: Enable debug mode (verbose logging, auto-reload).
        STORAGE_DIR: Root directory for persistent file storage.
        HF_TOKEN: Hugging Face API token (required for gated models).
        DEMUCS_MODEL: Demucs model variant for source separation.
        WHISPER_MODEL: Faster-Whisper model size for transcription.
        WHISPER_DEVICE: Compute device for Whisper (``auto`` resolves at runtime).
        WHISPER_COMPUTE_TYPE: Numerical precision for Whisper inference.
        QWEN_TTS_MODEL: Hugging Face model ID for Qwen3 TTS.
        PYANNOTE_MODEL: Hugging Face model ID for speaker diarization.
        MIN_SPEAKERS: Minimum number of speakers for diarization.
        MAX_SPEAKERS: Maximum number of speakers for diarization.
        SAMPLE_RATE: Target audio sample rate in Hz.
        OUTPUT_FORMAT: Default audio output container format.
        FFMPEG_PATH: Path to the ``ffmpeg`` binary.
        FFPROBE_PATH: Path to the ``ffprobe`` binary.
        MAX_FILE_SIZE_MB: Maximum allowed upload file size in megabytes.
        CHUNK_DURATION_S: Duration in seconds for audio chunking.
    """

    def __init__(self) -> None:
        # --- Application ---
        self.APP_NAME: str = os.getenv("APP_NAME", "VoiceClone AI")
        self.APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
        self.HOST: str = os.getenv("HOST", "0.0.0.0")
        self.PORT: int = int(os.getenv("PORT", "8000"))
        self.DEBUG: bool = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")

        # --- Storage ---
        self.STORAGE_DIR: Path = Path(os.getenv("STORAGE_DIR", "storage"))

        # --- Hugging Face ---
        self.HF_TOKEN: str = os.getenv("HF_TOKEN", "")

        # --- Demucs (source separation) ---
        self.DEMUCS_MODEL: str = os.getenv("DEMUCS_MODEL", "htdemucs")

        # --- Whisper (transcription) ---
        self.WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "large-v3")
        self.WHISPER_DEVICE: str = os.getenv("WHISPER_DEVICE", "auto")
        self.WHISPER_COMPUTE_TYPE: str = os.getenv("WHISPER_COMPUTE_TYPE", "float16")

        # --- TTS ---
        self.QWEN_TTS_MODEL: str = os.getenv("QWEN_TTS_MODEL", "Qwen/Qwen3-TTS-12Hz-1.7B-Base")
        self.MMS_TTS_MODEL: str = os.getenv("MMS_TTS_MODEL", "facebook/mms-tts-ben")

        # --- Diarization ---
        self.PYANNOTE_MODEL: str = os.getenv(
            "PYANNOTE_MODEL", "pyannote/speaker-diarization-3.1"
        )
        self.MIN_SPEAKERS: int = int(os.getenv("MIN_SPEAKERS", "1"))
        self.MAX_SPEAKERS: int = int(os.getenv("MAX_SPEAKERS", "10"))

        # --- Audio ---
        self.SAMPLE_RATE: int = int(os.getenv("SAMPLE_RATE", "24000"))
        self.OUTPUT_FORMAT: str = os.getenv("OUTPUT_FORMAT", "wav")

        # --- External tools ---
        self.FFMPEG_PATH: str = os.getenv("FFMPEG_PATH", "ffmpeg")
        self.FFPROBE_PATH: str = os.getenv("FFPROBE_PATH", "ffprobe")

        # --- Limits ---
        self.MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "500"))
        self.CHUNK_DURATION_S: int = int(os.getenv("CHUNK_DURATION_S", "30"))

        # --- Derived paths ---
        self.UPLOADS_DIR: Path = self.STORAGE_DIR / "uploads"
        self.JOBS_DIR: Path = self.STORAGE_DIR / "jobs"
        self.VOICES_DIR: Path = self.STORAGE_DIR / "voices"

        self._create_storage_dirs()

    def _create_storage_dirs(self) -> None:
        """Create required storage directories if they do not exist."""
        self.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        self.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        self.JOBS_DIR.mkdir(parents=True, exist_ok=True)
        self.VOICES_DIR.mkdir(parents=True, exist_ok=True)

    def __repr__(self) -> str:
        return (
            f"Settings(APP_NAME={self.APP_NAME!r}, PORT={self.PORT}, "
            f"DEBUG={self.DEBUG}, STORAGE_DIR={self.STORAGE_DIR!r})"
        )


settings = Settings()
