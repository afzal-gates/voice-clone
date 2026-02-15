"""Pydantic models for request/response validation and API documentation."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Job lifecycle
# ---------------------------------------------------------------------------


class JobStatus(str, Enum):
    """Lifecycle states for a voice-clone processing job."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class InputType(str, Enum):
    """Type of input media uploaded by the user."""

    AUDIO = "audio"
    VIDEO = "video"
    TEXT = "text"


# ---------------------------------------------------------------------------
# Music/Song Generation Enums
# ---------------------------------------------------------------------------


class MusicGenre(str, Enum):
    """Music genre options for generation."""

    POP = "pop"
    ROCK = "rock"
    EDM = "edm"
    CLASSICAL = "classical"
    CINEMATIC = "cinematic"
    HIPHOP = "hiphop"
    JAZZ = "jazz"
    COUNTRY = "country"
    FOLK = "folk"
    AMBIENT = "ambient"


class MusicMood(str, Enum):
    """Mood/emotion options for music generation."""

    HAPPY = "happy"
    SAD = "sad"
    DARK = "dark"
    ROMANTIC = "romantic"
    EPIC = "epic"
    CALM = "calm"
    ENERGETIC = "energetic"


class VocalType(str, Enum):
    """Voice type for singing vocals."""

    MALE = "male"
    FEMALE = "female"
    CHOIR = "choir"
    AI = "ai"


# ---------------------------------------------------------------------------
# Speaker diarization
# ---------------------------------------------------------------------------


class SpeakerSegment(BaseModel):
    """Time-aligned segment with speaker identity and transcript.

    Attributes:
        start: Segment start time in seconds.
        end: Segment end time in seconds.
        speaker_id: Unique identifier for the speaker.
        text: Transcribed text for this segment.
    """

    start: float
    end: float
    speaker_id: str
    text: str = ""


class Speaker(BaseModel):
    """Aggregated metadata for a detected speaker.

    Attributes:
        speaker_id: Unique identifier for the speaker within the job.
        label: Human-readable label (e.g., ``"Speaker 1"``).
        total_duration: Total speaking time in seconds.
        num_segments: Number of segments attributed to this speaker.
        reference_audio: Optional path to extracted reference audio.
    """

    speaker_id: str
    label: str
    total_duration: float = 0.0
    num_segments: int = 0
    reference_audio: Optional[str] = None


class VoiceMapping(BaseModel):
    """Maps a speaker to a reference voice for cloning or synthesis.

    Attributes:
        speaker_id: The original speaker identifier.
        reference_audio: Path to the reference audio for voice cloning.
        reference_text: Optional transcript of the reference audio.
    """

    speaker_id: str
    reference_audio: str
    reference_text: Optional[str] = None
    duration: float = 0.0


class VoiceProfile(BaseModel):
    """Voice profile for voice management.

    Attributes:
        voice_id: Unique identifier for the voice profile.
        name: Voice profile name.
        description: Optional description of the voice.
        audio_filename: Optional path to the audio file.
    """

    voice_id: str = ""
    name: str
    description: str = ""
    audio_filename: Optional[str] = None


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
        metadata: Optional dictionary for storing additional job data (e.g., outputs).
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
    updated_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))
    output_file: Optional[str] = None
    metadata: Optional[dict] = None


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class TTSRequest(BaseModel):
    """Request payload for standalone text-to-speech synthesis.

    Attributes:
        text: The text to synthesize into speech.
        language: Language code (e.g., ``"English"``, ``"Chinese"``).
        tts_model: TTS model to use (``"qwen3-tts"`` or ``"mms-tts"``).
        reference_audio: Optional path to a reference voice for cloning.
        ref_text: Optional transcript of the reference audio.
    """

    text: str = Field(..., min_length=1, max_length=5000)
    language: str = Field(default="English", max_length=50)
    tts_model: str = Field(default="qwen3-tts", max_length=50)
    reference_audio: Optional[str] = None
    ref_text: Optional[str] = None


class SpeakerMappingRequest(BaseModel):
    """Request payload to update speaker-to-voice mappings.

    Attributes:
        job_id: The job identifier.
        mappings: List of speaker-to-reference-voice mappings.
    """

    job_id: str
    mappings: list[VoiceMapping]


class MusicRequest(BaseModel):
    """Request payload for instrumental music generation.

    Attributes:
        prompt: Optional text prompt describing the desired music.
        duration: Duration of the music in seconds (5-60).
        genre: Music genre.
        mood: Emotional mood.
        bpm: Tempo in BPM (60-200).
        instruments: Optional list of instruments to feature.
    """

    prompt: str = Field(default="", max_length=500)
    duration: float = Field(default=30.0, ge=5.0, le=60.0)
    genre: MusicGenre = MusicGenre.POP
    mood: MusicMood = MusicMood.HAPPY
    bpm: int = Field(default=120, ge=60, le=200)
    instruments: Optional[list[str]] = None


class SingingRequest(BaseModel):
    """Request payload for singing voice synthesis.

    Attributes:
        lyrics: Song lyrics text.
        melody: Melody specification (MIDI notes or "auto" for generation).
        tempo: Tempo in BPM (60-200).
        vocal_type: Voice type (male, female, choir, ai).
        language: Language code (en, es, fr, de, etc.).
    """

    lyrics: str = Field(..., min_length=1, max_length=5000)
    melody: str = Field(default="auto", max_length=10000)
    tempo: int = Field(default=120, ge=60, le=200)
    vocal_type: VocalType = VocalType.AI
    language: str = Field(default="en", max_length=10)


class CompleteSongRequest(BaseModel):
    """Request payload for complete AI song generation.

    Attributes:
        lyrics: Song lyrics text.
        genre: Music genre.
        mood: Emotional mood.
        bpm: Tempo in BPM (60-200).
        instruments: Optional list of instruments to feature.
        vocal_type: Voice type for singing (male, female, choir, ai).
        language: Language code for vocals (en, es, fr, de, etc.).
        song_title: Song title for metadata and video. Default: "Untitled Song".
        artist_name: Artist name for metadata and video. Default: "AI Artist".
        generate_video: Whether to generate music video. Default: False.
        duration: Song duration in seconds (5-60). Default: 30.
    """

    lyrics: str = Field(..., min_length=10, max_length=5000)
    genre: MusicGenre
    mood: MusicMood
    bpm: int = Field(default=120, ge=60, le=200)
    instruments: Optional[list[str]] = None
    vocal_type: VocalType = VocalType.AI
    language: str = Field(default="en", max_length=10)
    song_title: str = Field(default="Untitled Song", max_length=200)
    artist_name: str = Field(default="AI Artist", max_length=200)
    generate_video: bool = False
    duration: float = Field(default=30.0, ge=5.0, le=60.0)


class InstrumentalRequest(BaseModel):
    """Request payload for instrumental-only music generation from lyrics.

    Attributes:
        lyrics: Lyrics text to inspire the instrumental music generation.
        genre: Music genre.
        mood: Emotional mood.
        bpm: Tempo in BPM (60-200).
        instruments: Optional list of instruments to feature.
        title: Music title for metadata. Default: "Untitled Instrumental".
        duration: Music duration in seconds (5-60). Default: 30.
    """

    lyrics: str = Field(..., min_length=10, max_length=5000)
    genre: MusicGenre
    mood: MusicMood
    bpm: int = Field(default=120, ge=60, le=200)
    instruments: Optional[list[str]] = None
    title: str = Field(default="Untitled Instrumental", max_length=200)
    duration: float = Field(default=30.0, ge=5.0, le=60.0)


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class JobResponse(BaseModel):
    """Lightweight response returned after job creation or status update.

    Attributes:
        job_id: The unique job identifier.
        status: Current job status.
        progress: Processing progress as a fraction ``[0.0, 1.0]``.
        message: Optional status message.
    """

    job_id: str
    status: JobStatus
    progress: float = 0.0
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
        created_at: UTC timestamp of job creation.
        updated_at: UTC timestamp of last update.
        output_file: Path to the final output, if available.
    """

    job_id: str
    status: JobStatus
    input_type: InputType
    input_filename: str
    speakers: list[Speaker]
    segments: list[SpeakerSegment]
    progress: float
    error: Optional[str]
    created_at: datetime
    updated_at: datetime
    output_file: Optional[str]


class MusicResponse(BaseModel):
    """Response for music generation job.

    Attributes:
        job_id: The unique job identifier.
        status: Current job status.
        progress: Generation progress.
        output_file: Path to generated music file.
        error: Error message if generation failed.
    """

    job_id: str
    status: JobStatus
    progress: float = 0.0
    output_file: Optional[str] = None
    error: Optional[str] = None


class SingingResponse(BaseModel):
    """Response for singing synthesis job.

    Attributes:
        job_id: The unique job identifier.
        status: Current job status.
        progress: Synthesis progress.
        output_file: Path to generated singing audio.
        error: Error message if synthesis failed.
    """

    job_id: str
    status: JobStatus
    progress: float = 0.0
    output_file: Optional[str] = None
    error: Optional[str] = None


class CompleteSongResponse(BaseModel):
    """Response for complete song generation job.

    Attributes:
        job_id: The unique job identifier.
        status: Current job status.
        outputs: Dictionary of output file paths (vocals, instrumental, mixed, video, midi).
        progress: Generation progress.
        error: Error message if generation failed.
    """

    job_id: str
    status: JobStatus
    outputs: Optional[dict[str, str]] = None
    progress: float = 0.0
    error: Optional[str] = None


class InstrumentalResponse(BaseModel):
    """Response for instrumental-only music generation job.

    Attributes:
        job_id: The unique job identifier.
        status: Current job status.
        outputs: Dictionary of output file paths (instrumental_wav, instrumental_mp3, midi).
        progress: Generation progress.
        error: Error message if generation failed.
    """

    job_id: str
    status: JobStatus
    outputs: Optional[dict[str, str]] = None
    progress: float = 0.0
    error: Optional[str] = None


class TTSResponse(BaseModel):
    """Response for TTS (text-to-speech) synthesis job.

    Attributes:
        job_id: The unique job identifier.
        status: Current job status.
        output_file: Path to the generated audio file (null while processing).
    """

    job_id: str
    status: str
    output_file: Optional[str] = None


class MixRequest(BaseModel):
    """Request for mixing TTS audio with background music.

    Attributes:
        tts_job_id: Job ID for the TTS generation.
        music_job_id: Job ID for the music generation.
        tts_volume: Volume level for TTS audio (0.0-1.0).
        music_volume: Volume level for music audio (0.0-1.0).
        music_delay: Delay before music starts in seconds.
    """

    tts_job_id: str
    music_job_id: str
    tts_volume: float = Field(default=0.8, ge=0.0, le=1.0)
    music_volume: float = Field(default=0.3, ge=0.0, le=1.0)
    music_delay: float = Field(default=0.0, ge=0.0)


class MixResponse(BaseModel):
    """Response for audio mixing job.

    Attributes:
        job_id: The unique job identifier.
        status: Current job status.
        output_file: Path to the mixed audio file (null while processing).
    """

    job_id: str
    status: str
    output_file: Optional[str] = None


# Alias VoiceProfileResponse to VoiceProfile for API responses
VoiceProfileResponse = VoiceProfile
