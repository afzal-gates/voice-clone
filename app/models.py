"""Pydantic v2 data models for the VoiceClone AI platform.

Defines enums, domain models, request schemas, and response schemas used
across the API layer and internal pipeline services.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class JobStatus(str, Enum):
    """Lifecycle states for a voice-clone processing job."""

    PENDING = "pending"
    EXTRACTING_AUDIO = "extracting_audio"
    SEPARATING = "separating"
    DIARIZING = "diarizing"
    TRANSCRIBING = "transcribing"
    AWAITING_VOICE_ASSIGNMENT = "awaiting_voice_assignment"
    GENERATING_SPEECH = "generating_speech"
    ALIGNING = "aligning"
    MERGING = "merging"
    COMPLETED = "completed"
    FAILED = "failed"


class InputType(str, Enum):
    """Supported input media types."""

    AUDIO = "audio"
    VIDEO = "video"
    TEXT = "text"


class MusicStyle(str, Enum):
    """Music generation styles/genres."""

    POP = "pop"
    ROCK = "rock"
    ELECTRONIC = "electronic"
    CLASSICAL = "classical"
    JAZZ = "jazz"
    AMBIENT = "ambient"
    HIP_HOP = "hip-hop"
    COUNTRY = "country"
    FOLK = "folk"
    CINEMATIC = "cinematic"


# ---------------------------------------------------------------------------
# Domain models
# ---------------------------------------------------------------------------


class SpeakerSegment(BaseModel):
    """A single time-aligned segment attributed to a speaker.

    Attributes:
        speaker_id: Unique identifier for the speaker within the job.
        start_time: Segment start in seconds from the beginning of the media.
        end_time: Segment end in seconds from the beginning of the media.
        text: Transcribed text for this segment (populated after transcription).
    """

    speaker_id: str
    start_time: float
    end_time: float
    text: str = ""


class Speaker(BaseModel):
    """Aggregated metadata for a detected speaker.

    Attributes:
        speaker_id: Unique identifier for the speaker within the job.
        label: Human-readable label (e.g. "Speaker 1").
        segment_count: Number of segments attributed to this speaker.
        total_duration: Cumulative speaking duration in seconds.
        assigned_voice_ref: Filename of the reference audio uploaded for
            voice cloning.  ``None`` until the user assigns a voice.
    """

    speaker_id: str
    label: str = ""
    segment_count: int = 0
    total_duration: float = 0.0
    assigned_voice_ref: Optional[str] = None


class VoiceProfile(BaseModel):
    """A saved voice profile for reuse across jobs and TTS sessions."""

    voice_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str
    description: str = ""
    audio_filename: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    sample_rate: int = 0
    duration: float = 0.0


class JobInfo(BaseModel):
    """Complete state representation of a voice-clone job.

    Attributes:
        job_id: Short unique identifier (12-char hex).
        status: Current lifecycle status.
        input_type: Type of the uploaded input media.
        input_filename: Original filename of the uploaded media.
        speakers: Detected speakers with aggregated metadata.
        segments: Time-aligned speaker segments with transcriptions.
        progress: Processing progress as a fraction ``[0.0, 1.0]``.
        error: Error message if the job has failed, else ``None``.
        created_at: UTC timestamp when the job was created.
        updated_at: UTC timestamp of the last status change.
        output_file: Path to the final output file, else ``None``.
    """

    job_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    status: JobStatus = JobStatus.PENDING
    input_type: InputType = InputType.AUDIO
    input_filename: str = ""
    speakers: list[Speaker] = Field(default_factory=list)
    segments: list[SpeakerSegment] = Field(default_factory=list)
    progress: float = 0.0
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    output_file: Optional[str] = None


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class TTSRequest(BaseModel):
    """Request payload for standalone text-to-speech synthesis.

    Attributes:
        text: The text to synthesize into speech.
        speed: Playback speed multiplier (0.5x -- 2.0x).
        pitch: Pitch shift multiplier (0.5x -- 2.0x).
    """

    text: str
    speed: float = Field(default=1.0, ge=0.5, le=2.0)
    pitch: float = Field(default=1.0, ge=0.5, le=2.0)


class VoiceAssignment(BaseModel):
    """Maps a detected speaker to a reference voice audio file.

    Either ``reference_audio_filename`` or ``voice_id`` must be provided.
    When ``voice_id`` is set, the saved voice profile's audio is used.
    """

    speaker_id: str
    reference_audio_filename: str = ""
    voice_id: Optional[str] = None


class VoiceAssignmentRequest(BaseModel):
    """Batch voice assignment request for a job.

    Attributes:
        assignments: One or more speaker-to-voice mappings.
    """

    assignments: list[VoiceAssignment]


class MusicRequest(BaseModel):
    """Request payload for music generation.

    Attributes:
        prompt: Text description of the desired music.
        duration: Length of generated audio in seconds (5-30s).
        style: Optional genre/style preset for enhanced generation.
    """

    prompt: str = Field(..., min_length=1, max_length=500)
    duration: float = Field(default=10.0, ge=5.0, le=30.0)
    style: Optional[MusicStyle] = None


class MusicResponse(BaseModel):
    """Response returned after music generation request.

    Attributes:
        job_id: The unique job identifier.
        status: Current generation status.
        output_file: Path to the generated audio file, else ``None``.
        duration: Actual duration of generated audio in seconds.
    """

    job_id: str
    status: str
    output_file: Optional[str] = None
    duration: Optional[float] = None


class MixRequest(BaseModel):
    """Request payload for audio mixing.

    Attributes:
        tts_job_id: Job ID of the completed TTS generation.
        music_job_id: Job ID of the completed music generation.
        tts_volume: TTS volume level (0.0-1.0). Default: 0.85.
        music_volume: Music volume level (0.0-1.0). Default: 0.30.
        music_delay: Delay before music starts in seconds. Default: 0.0.
    """

    tts_job_id: str
    music_job_id: str
    tts_volume: float = Field(default=0.85, ge=0.0, le=1.0)
    music_volume: float = Field(default=0.30, ge=0.0, le=1.0)
    music_delay: float = Field(default=0.0, ge=0.0, le=30.0)


class MixResponse(BaseModel):
    """Response returned after audio mixing request.

    Attributes:
        job_id: The unique job identifier.
        status: Current mixing status.
        output_file: Path to the mixed audio file, else ``None``.
    """

    job_id: str
    status: str
    output_file: Optional[str] = None


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class JobResponse(BaseModel):
    """Lightweight response returned after job creation or status update.

    Attributes:
        job_id: The unique job identifier.
        status: Current job status.
        message: Optional human-readable status message.
    """

    job_id: str
    status: JobStatus
    message: str = ""


class JobDetailResponse(BaseModel):
    """Detailed response with full job state for polling or inspection.

    Attributes:
        job_id: The unique job identifier.
        status: Current job status.
        input_type: Type of input media.
        input_filename: Original filename of the uploaded media.
        speakers: Detected speakers with metadata.
        segments: Time-aligned speaker segments.
        progress: Processing progress as a fraction ``[0.0, 1.0]``.
        error: Error description if the job has failed.
        created_at: UTC creation timestamp.
        output_file: Path to the final output file.
    """

    job_id: str
    status: JobStatus
    input_type: InputType
    input_filename: str
    speakers: list[Speaker] = Field(default_factory=list)
    segments: list[SpeakerSegment] = Field(default_factory=list)
    progress: float = 0.0
    error: Optional[str] = None
    created_at: datetime
    output_file: Optional[str] = None


class TTSResponse(BaseModel):
    """Response returned after a TTS synthesis request.

    Attributes:
        job_id: The unique job identifier.
        status: Current synthesis status.
        output_file: Path to the generated audio file, else ``None``.
    """

    job_id: str
    status: str
    output_file: Optional[str] = None


class VoiceProfileResponse(BaseModel):
    """Response model for voice profile API endpoints."""

    voice_id: str
    name: str
    description: str = ""
    audio_filename: str = ""
    created_at: datetime
    sample_rate: int = 0
    duration: float = 0.0


class MelodyFormat(str, Enum):
    """Melody input formats for singing synthesis."""

    MIDI = "midi"
    NOTATION = "notation"
    AUTO = "auto"


class SingingRequest(BaseModel):
    """Request payload for singing synthesis.

    Attributes:
        lyrics: Song lyrics (text).
        melody: Melody specification (MIDI file ID, notation string, or None).
        melody_format: Format of the melody input.
        voice_model: Singing voice model identifier.
        tempo: Tempo in BPM (60-200).
        key_shift: Pitch shift in semitones (-12 to +12).
        language: Language code for phoneme conversion.
    """

    lyrics: str = Field(..., min_length=1, max_length=2000)
    melody: Optional[str] = None
    melody_format: MelodyFormat = MelodyFormat.AUTO
    voice_model: str = "default"
    tempo: int = Field(default=120, ge=60, le=200)
    key_shift: int = Field(default=0, ge=-12, le=12)
    language: str = "en"


class SingingResponse(BaseModel):
    """Response returned after a singing synthesis request.

    Attributes:
        job_id: The unique job identifier.
        status: Current synthesis status.
        output_file: Path to the generated singing audio file, else ``None``.
        duration: Actual duration of generated audio in seconds.
    """

    job_id: str
    status: str
    output_file: Optional[str] = None
    duration: Optional[float] = None
