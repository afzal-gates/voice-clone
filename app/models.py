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

    Attributes:
        speaker_id: The speaker identifier from diarization output.
        reference_audio_filename: Filename of the uploaded reference audio
            stored in the job's directory.
    """

    speaker_id: str
    reference_audio_filename: str


class VoiceAssignmentRequest(BaseModel):
    """Batch voice assignment request for a job.

    Attributes:
        assignments: One or more speaker-to-voice mappings.
    """

    assignments: list[VoiceAssignment]


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
