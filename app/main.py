"""FastAPI application for the VoiceClone AI platform.

Defines all HTTP endpoints for uploading media, managing jobs,
assigning reference voices, launching voice replacement, standalone
TTS, and downloading results.
"""

from __future__ import annotations

import asyncio
import io
import json
import logging
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

import numpy as np

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.models import (
    InputType,
    JobDetailResponse,
    JobResponse,
    JobStatus,
    MixRequest,
    MixResponse,
    MusicResponse,
    MusicStyle,
    SingingResponse,
    TTSResponse,
    VoiceAssignmentRequest,
    VoiceProfileResponse,
)
from app.services.job_manager import JobManager
from app.services.pipeline_orchestrator import PipelineOrchestrator
from app.services.voice_manager import VoiceManager

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Allowed file extensions
# ---------------------------------------------------------------------------

_VIDEO_EXTENSIONS: frozenset[str] = frozenset(
    {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv"}
)
_AUDIO_EXTENSIONS: frozenset[str] = frozenset({".wav", ".mp3"})
_ALLOWED_EXTENSIONS: frozenset[str] = _VIDEO_EXTENSIONS | _AUDIO_EXTENSIONS

_MEDIA_TYPES: dict[str, str] = {
    "wav": "audio/wav",
    "mp3": "audio/mpeg",
    "mp4": "video/mp4",
}

# ---------------------------------------------------------------------------
# Application-scoped singletons
# ---------------------------------------------------------------------------

job_manager = JobManager()
voice_manager = VoiceManager()
orchestrator = PipelineOrchestrator(job_manager)

# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan handler for startup / shutdown logic."""
    logger.info(
        "%s v%s starting -- storage=%s",
        settings.APP_NAME,
        settings.APP_VERSION,
        settings.STORAGE_DIR,
    )
    yield
    logger.info("%s shutting down", settings.APP_NAME)


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Static files & UI
# ---------------------------------------------------------------------------

_STATIC_DIR = Path(__file__).parent / "static"
if _STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
async def serve_ui() -> HTMLResponse:
    """Serve the web UI."""
    index_file = _STATIC_DIR / "index.html"
    if not index_file.exists():
        return HTMLResponse("<h1>VoiceClone AI</h1><p>UI not found. Use /docs for the API.</p>")
    return HTMLResponse(index_file.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def _detect_input_type(filename: str) -> InputType:
    """Infer :class:`InputType` from a filename extension.

    Args:
        filename: Original filename with extension.

    Returns:
        ``InputType.VIDEO`` for video extensions, ``InputType.AUDIO`` otherwise.
    """
    suffix = Path(filename).suffix.lower()
    if suffix in _VIDEO_EXTENSIONS:
        return InputType.VIDEO
    return InputType.AUDIO


def _validate_extension(filename: str) -> None:
    """Raise :class:`HTTPException` if the file extension is not allowed.

    Args:
        filename: Original filename with extension.

    Raises:
        HTTPException: 400 if the extension is unsupported.
    """
    suffix = Path(filename).suffix.lower()
    if suffix not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported file extension '{suffix}'. "
                f"Allowed: {sorted(_ALLOWED_EXTENSIONS)}"
            ),
        )


async def _save_upload(upload: UploadFile, destination: Path) -> None:
    """Stream an :class:`UploadFile` to *destination* on disk.

    Args:
        upload:      The incoming upload.
        destination: Target file path.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    chunk_size = 1024 * 1024  # 1 MiB

    with open(destination, "wb") as fh:
        while True:
            chunk = await upload.read(chunk_size)
            if not chunk:
                break
            fh.write(chunk)


def _job_to_detail(job: object) -> dict:
    """Convert a :class:`JobInfo` to a dict compatible with
    :class:`JobDetailResponse`.

    Fields that are ``None`` are normalised to suitable defaults so
    the response model validates cleanly.
    """
    return {
        "job_id": job.job_id,
        "status": job.status,
        "input_type": job.input_type,
        "input_filename": job.input_filename,
        "speakers": job.speakers,
        "segments": job.segments,
        "progress": job.progress,
        "error": job.error,
        "created_at": job.created_at,
        "output_file": job.output_file,
    }


def _launch_background_task(coro) -> None:  # noqa: ANN001
    """Schedule *coro* as a fire-and-forget ``asyncio`` task.

    Exceptions are logged rather than propagated so they do not crash
    the event loop.
    """

    async def _wrapper() -> None:
        try:
            await coro
        except Exception:
            logger.exception("Background task failed")

    asyncio.create_task(_wrapper())


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/api/health")
async def health_check() -> dict:
    """Return a lightweight health check response."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


@app.get("/api/settings")
async def get_settings() -> dict:
    """Return current application settings (mode, models directory, etc.)."""
    return {
        "offline_mode": settings.OFFLINE_MODE,
        "models_dir": settings.MODELS_DIR,
        "has_local_models": settings.has_local_models(),
    }


@app.post("/api/settings")
async def update_settings(
    offline_mode: bool = Form(...),
) -> dict:
    """Update application settings at runtime.

    Args:
        offline_mode: ``True`` to use only local cached models,
                      ``False`` to allow downloading from HuggingFace.
    """
    settings.set_offline_mode(offline_mode)
    logger.info("Settings updated: offline_mode=%s", offline_mode)
    return {
        "offline_mode": settings.OFFLINE_MODE,
        "models_dir": settings.MODELS_DIR,
        "has_local_models": settings.has_local_models(),
    }


@app.get("/api/tts-models")
async def list_tts_models() -> list[dict]:
    """Return the available TTS models with metadata."""
    from app.pipeline.tts_engine import MODEL_QWEN, MODEL_MMS, MODEL_INDICF5

    return [
        {
            "id": MODEL_QWEN,
            "name": "Qwen3-TTS",
            "description": "Multilingual TTS with voice cloning",
            "supports_cloning": True,
            "languages": [
                "Chinese", "English", "French", "German", "Italian",
                "Japanese", "Korean", "Portuguese", "Russian", "Spanish",
            ],
        },
        {
            "id": MODEL_MMS,
            "name": "Meta MMS-TTS Bengali",
            "description": "Bengali text-to-speech (no voice cloning)",
            "supports_cloning": False,
            "languages": ["Bengali"],
        },
        {
            "id": MODEL_INDICF5,
            "name": "IndicF5",
            "description": "Indian languages TTS with voice cloning (Bengali, Hindi, Tamil, Telugu + 7 more)",
            "supports_cloning": True,
            "languages": [
                "Assamese", "Bengali", "Gujarati", "Hindi", "Kannada",
                "Malayalam", "Marathi", "Odia", "Punjabi", "Tamil", "Telugu",
            ],
        },
    ]


# -- Upload ----------------------------------------------------------------


@app.post("/api/upload", response_model=JobResponse)
async def upload_file(
    file: UploadFile = File(...),
    input_type: str | None = Form(default=None),
) -> JobResponse:
    """Upload a media file and start the analysis pipeline.

    The file extension is validated against the list of supported formats.
    If *input_type* is not provided it is auto-detected from the extension.
    The analysis pipeline (extraction, separation, diarization,
    transcription) runs as a background task.

    Args:
        file:       The uploaded media file.
        input_type: Optional explicit input type (``audio`` or ``video``).

    Returns:
        A :class:`JobResponse` with the new ``job_id`` and status.

    Raises:
        HTTPException: 400 on unsupported extension, oversized file, or
                       missing filename.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required.")

    _validate_extension(file.filename)

    # Validate file size (Content-Length is not always reliable, so we also
    # check after saving -- but a preliminary check is helpful).
    if file.size is not None and file.size > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail=(
                f"File size exceeds maximum of {settings.MAX_FILE_SIZE_MB} MB."
            ),
        )

    # Determine input type.
    if input_type is not None:
        try:
            resolved_type = InputType(input_type.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid input_type '{input_type}'. Use 'audio' or 'video'.",
            )
    else:
        resolved_type = _detect_input_type(file.filename)

    # Create job and persist the uploaded file.
    job = job_manager.create_job(resolved_type, file.filename)
    job_dir = job_manager.get_job_dir(job.job_id)
    dest_path = job_dir / "input" / file.filename

    await _save_upload(file, dest_path)

    # Validate actual size on disk.
    actual_size = dest_path.stat().st_size
    if actual_size > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
        job_manager.delete_job(job.job_id)
        raise HTTPException(
            status_code=400,
            detail=f"File size ({actual_size / (1024*1024):.1f} MB) exceeds maximum of {settings.MAX_FILE_SIZE_MB} MB.",
        )

    logger.info(
        "Upload received: job=%s file=%s type=%s size=%.1f MB",
        job.job_id,
        file.filename,
        resolved_type.value,
        actual_size / (1024 * 1024),
    )

    _launch_background_task(orchestrator.process_upload(job.job_id, dest_path))

    return JobResponse(
        job_id=job.job_id,
        status=job.status,
        message="Upload received. Processing started.",
    )


# -- Job listing -----------------------------------------------------------


@app.get("/api/jobs", response_model=list[JobDetailResponse])
async def list_jobs() -> list[dict]:
    """Return all known jobs ordered by creation time (newest first)."""
    jobs = job_manager.list_jobs()
    return [_job_to_detail(j) for j in jobs]


@app.get("/api/jobs/{job_id}", response_model=JobDetailResponse)
async def get_job(job_id: str) -> dict:
    """Return detailed information for a single job.

    Args:
        job_id: The 12-character hex job identifier.

    Raises:
        HTTPException: 404 if the job does not exist.
    """
    job = job_manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    return _job_to_detail(job)


# -- Reference voice upload ------------------------------------------------


@app.post("/api/jobs/{job_id}/reference-voice")
async def upload_reference_voice(
    job_id: str,
    file: UploadFile = File(...),
    speaker_id: str = Form(...),
) -> dict:
    """Upload a reference voice audio file for a specific speaker.

    The file is saved to the job's ``references/`` directory.

    Args:
        job_id:     The job identifier.
        file:       The reference voice audio file.
        speaker_id: The speaker to assign this reference to.

    Raises:
        HTTPException: 404 if the job does not exist, 400 if the filename
                       is missing.
    """
    job = job_manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required.")

    job_dir = job_manager.get_job_dir(job_id)
    dest_path = job_dir / "references" / file.filename

    await _save_upload(file, dest_path)

    logger.info(
        "Reference voice uploaded: job=%s speaker=%s file=%s",
        job_id,
        speaker_id,
        file.filename,
    )

    return {
        "message": "Reference voice uploaded",
        "speaker_id": speaker_id,
        "filename": file.filename,
    }


# -- Voice assignment & replacement ----------------------------------------


@app.post("/api/jobs/{job_id}/assign-voices", response_model=JobResponse)
async def assign_voices(
    job_id: str,
    request: VoiceAssignmentRequest,
) -> JobResponse:
    """Assign reference voices to detected speakers and start replacement.

    Validates that:
    - The job exists and is in ``AWAITING_VOICE_ASSIGNMENT`` status.
    - All referenced speakers exist in the job.
    - All referenced audio files exist on disk.

    The voice replacement pipeline runs as a background task.

    Args:
        job_id:  The job identifier.
        request: A :class:`VoiceAssignmentRequest` with speaker-voice
                 mappings.

    Raises:
        HTTPException: 404 if job not found, 400 on validation failure.
    """
    job = job_manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    if job.status != JobStatus.AWAITING_VOICE_ASSIGNMENT:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Job is not awaiting voice assignment. "
                f"Current status: {job.status.value}"
            ),
        )

    # Validate speakers.
    known_speaker_ids = {s.speaker_id for s in job.speakers}
    job_dir = job_manager.get_job_dir(job_id)

    for assignment in request.assignments:
        if assignment.speaker_id not in known_speaker_ids:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown speaker: {assignment.speaker_id}",
            )

        # Resolve voice_id to a reference file if provided.
        if assignment.voice_id:
            audio_path = voice_manager.get_audio_path(assignment.voice_id)
            if audio_path is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"Voice profile not found: {assignment.voice_id}",
                )
            import shutil
            ref_dest = job_dir / "references" / audio_path.name
            if not ref_dest.exists():
                ref_dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(audio_path), str(ref_dest))
            assignment.reference_audio_filename = audio_path.name
        else:
            ref_path = job_dir / "references" / assignment.reference_audio_filename
            if not ref_path.exists():
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Reference audio file not found: "
                        f"{assignment.reference_audio_filename}"
                    ),
                )

    # Update speaker assignments on the job model.
    assignment_map = {a.speaker_id: a.reference_audio_filename for a in request.assignments}
    for speaker in job.speakers:
        if speaker.speaker_id in assignment_map:
            speaker.assigned_voice_ref = assignment_map[speaker.speaker_id]
    job_manager.save_job(job)

    logger.info(
        "Voice assignment started: job=%s assignments=%d",
        job_id,
        len(request.assignments),
    )

    _launch_background_task(
        orchestrator.process_voice_replacement(job_id, request.assignments)
    )

    return JobResponse(
        job_id=job.job_id,
        status=job.status,
        message="Voice replacement started.",
    )


# -- TTS -------------------------------------------------------------------


@app.post("/api/tts", response_model=TTSResponse)
async def text_to_speech(
    text: str = Form(...),
    reference_audio: UploadFile | None = File(default=None),
    voice_id: str | None = Form(default=None),
    language: str | None = Form(default=None),
    tts_model: str | None = Form(default=None),
    speed: float = Form(default=1.0),
    pitch: float = Form(default=1.0),
    ref_text: str | None = Form(default=None),
) -> TTSResponse:
    """Synthesise speech from text with optional voice cloning.

    Provide either *voice_id* (a saved voice profile) or *reference_audio*
    (a one-time upload) to clone a voice.  If neither is given the default
    TTS voice is used.  Voice cloning is available with Qwen3-TTS and
    IndicF5.

    Args:
        text:            The text to synthesise.
        reference_audio: Optional reference voice audio file.
        voice_id:        Optional saved voice profile ID.
        language:        Language for synthesis (e.g. "English", "Bengali").
                         ``None`` for auto-detection from text.
        tts_model:       TTS model to use (``qwen3-tts``, ``mms-tts-ben``,
                         or ``indicf5``).  ``None`` defaults to ``qwen3-tts``.
        speed:           Playback speed multiplier (0.5 -- 2.0).
        pitch:           Pitch shift multiplier (0.5 -- 2.0).
        ref_text:        Transcript of the reference audio (recommended for
                         IndicF5, optional for Qwen3-TTS).

    Raises:
        HTTPException: 400 on invalid parameters, 404 if voice_id not found.
    """
    if not text.strip():
        raise HTTPException(status_code=400, detail="Text must not be empty.")

    if not 0.5 <= speed <= 2.0:
        raise HTTPException(
            status_code=400, detail="Speed must be between 0.5 and 2.0."
        )
    if not 0.5 <= pitch <= 2.0:
        raise HTTPException(
            status_code=400, detail="Pitch must be between 0.5 and 2.0."
        )

    job = job_manager.create_job(InputType.TEXT, "tts_request")
    job_dir = job_manager.get_job_dir(job.job_id)

    ref_path: Path | None = None
    if voice_id:
        ref_path = voice_manager.get_audio_path(voice_id)
        if ref_path is None:
            raise HTTPException(
                status_code=404, detail=f"Voice profile not found: {voice_id}"
            )
        logger.info("TTS using saved voice profile: %s", voice_id)
    elif reference_audio is not None and reference_audio.filename:
        ref_path = job_dir / "references" / reference_audio.filename
        await _save_upload(reference_audio, ref_path)

    # Normalize model name
    from app.pipeline.tts_engine import MODEL_QWEN, MODEL_MMS, MODEL_INDICF5, AVAILABLE_MODELS

    resolved_model = tts_model if tts_model in AVAILABLE_MODELS else MODEL_QWEN

    # Qwen3-TTS and IndicF5 require a reference voice
    if resolved_model == MODEL_QWEN and ref_path is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "Qwen3-TTS requires a reference voice. "
                "Please select a saved voice or upload a reference audio file, "
                "or switch to Meta MMS-TTS Bengali for plain text-to-speech."
            ),
        )
    if resolved_model == MODEL_INDICF5 and ref_path is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "IndicF5 requires a reference voice for voice cloning. "
                "Please upload a reference audio file or select a saved voice."
            ),
        )

    logger.info(
        "TTS request: job=%s text_len=%d speed=%.1f pitch=%.1f ref=%s model=%s",
        job.job_id,
        len(text),
        speed,
        pitch,
        ref_path.name if ref_path else "none",
        resolved_model,
    )

    # Normalize language: empty string or "auto" means auto-detect
    tts_language = language if language and language.lower() != "auto" else None

    # Normalize ref_text: empty string means no transcript
    resolved_ref_text = ref_text.strip() if ref_text and ref_text.strip() else None

    _launch_background_task(
        orchestrator.process_tts(
            job_id=job.job_id,
            text=text,
            ref_audio_path=ref_path,
            speed=speed,
            pitch=pitch,
            language=tts_language,
            tts_model=resolved_model,
            ref_text=resolved_ref_text,
        )
    )

    return TTSResponse(
        job_id=job.job_id,
        status=job.status.value,
        output_file=None,
    )


# -- Music Generation ------------------------------------------------------


@app.post("/api/music", response_model=MusicResponse)
async def generate_music(
    prompt: str = Form(...),
    duration: float = Form(default=10.0),
    style: str | None = Form(default=None),
    reference_audio: UploadFile | None = File(default=None),
) -> MusicResponse:
    """Generate music from a text prompt.

    Uses Meta's AudioCraft MusicGen to create music based on textual
    descriptions. Supports style conditioning via genre presets and
    optional melody conditioning via reference audio uploads.

    Args:
        prompt:          Text description of the desired music (1-500 chars).
        duration:        Length of audio to generate in seconds (5-30s).
        style:           Optional genre/style preset (pop, rock, electronic, etc.).
        reference_audio: Optional reference audio for melody conditioning.

    Returns:
        A :class:`MusicResponse` with the new ``job_id`` and status.

    Raises:
        HTTPException: 400 on invalid parameters (empty prompt, bad duration).
    """
    if not prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt must not be empty.")

    if len(prompt) > 500:
        raise HTTPException(
            status_code=400, detail="Prompt must be 500 characters or less."
        )

    if not 5.0 <= duration <= 30.0:
        raise HTTPException(
            status_code=400,
            detail="Duration must be between 5 and 30 seconds.",
        )

    # Validate style if provided
    if style is not None:
        try:
            MusicStyle(style.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid style '{style}'. Valid styles: {[s.value for s in MusicStyle]}",
            )

    # Create job
    job = job_manager.create_job(InputType.TEXT, "music_generation")
    job_dir = job_manager.get_job_dir(job.job_id)

    # Handle reference audio upload
    ref_path: Path | None = None
    if reference_audio is not None and reference_audio.filename:
        ref_path = job_dir / "references" / reference_audio.filename
        await _save_upload(reference_audio, ref_path)
        logger.info("Music gen using reference audio: %s", reference_audio.filename)

    logger.info(
        "Music generation request: job=%s prompt='%s...' duration=%.1fs style=%s ref=%s",
        job.job_id,
        prompt[:30],
        duration,
        style or "none",
        ref_path.name if ref_path else "none",
    )

    # Launch background task
    _launch_background_task(
        orchestrator.process_music(
            job_id=job.job_id,
            prompt=prompt,
            duration=duration,
            style=style,
            ref_audio_path=ref_path,
        )
    )

    return MusicResponse(
        job_id=job.job_id,
        status=job.status.value,
        output_file=None,
        duration=duration,
    )


@app.get("/api/music/{job_id}", response_model=MusicResponse)
async def get_music_status(job_id: str) -> MusicResponse:
    """Get music generation job status.

    Args:
        job_id: The job identifier.

    Returns:
        A :class:`MusicResponse` with current status and output info.

    Raises:
        HTTPException: 404 if the job does not exist.
    """
    job = job_manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    # Get actual duration if output exists
    actual_duration: float | None = None
    if job.output_file and Path(job.output_file).exists():
        try:
            import soundfile as sf

            info = sf.info(job.output_file)
            actual_duration = info.duration
        except Exception:
            pass

    return MusicResponse(
        job_id=job.job_id,
        status=job.status.value,
        output_file=job.output_file,
        duration=actual_duration,
    )


# -- Audio Mixing ----------------------------------------------------------


@app.post("/api/mix", response_model=MixResponse)
async def mix_audio(request: MixRequest) -> MixResponse:
    """Mix TTS narration with background music.

    Combines completed TTS and music generation outputs with adjustable
    volume levels and timing offsets. Both source jobs must be in
    COMPLETED status with valid output files.

    Args:
        request: A :class:`MixRequest` with source job IDs and mix parameters.

    Returns:
        A :class:`MixResponse` with the new mixing job ID and status.

    Raises:
        HTTPException: 400 on validation failure (missing jobs, incomplete
                       jobs, missing output files), 404 if source jobs not found.
    """
    # Validate source jobs exist
    tts_job = job_manager.get_job(request.tts_job_id)
    if tts_job is None:
        raise HTTPException(
            status_code=404, detail=f"TTS job not found: {request.tts_job_id}"
        )

    music_job = job_manager.get_job(request.music_job_id)
    if music_job is None:
        raise HTTPException(
            status_code=404, detail=f"Music job not found: {request.music_job_id}"
        )

    # Validate jobs are completed
    if tts_job.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=(
                f"TTS job is not completed. "
                f"Current status: {tts_job.status.value}"
            ),
        )

    if music_job.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Music job is not completed. "
                f"Current status: {music_job.status.value}"
            ),
        )

    # Validate output files exist
    if not tts_job.output_file or not Path(tts_job.output_file).exists():
        raise HTTPException(
            status_code=400,
            detail=f"TTS output file not found for job: {request.tts_job_id}",
        )

    if not music_job.output_file or not Path(music_job.output_file).exists():
        raise HTTPException(
            status_code=400,
            detail=f"Music output file not found for job: {request.music_job_id}",
        )

    # Create mixing job
    job = job_manager.create_job(InputType.TEXT, "audio_mix")

    logger.info(
        "Audio mixing request: job=%s, tts=%s, music=%s, tts_vol=%.2f, music_vol=%.2f, delay=%.2fs",
        job.job_id,
        request.tts_job_id,
        request.music_job_id,
        request.tts_volume,
        request.music_volume,
        request.music_delay,
    )

    # Launch background task
    _launch_background_task(
        orchestrator.process_mix(
            job_id=job.job_id,
            tts_job_id=request.tts_job_id,
            music_job_id=request.music_job_id,
            tts_volume=request.tts_volume,
            music_volume=request.music_volume,
            music_delay=request.music_delay,
        )
    )

    return MixResponse(
        job_id=job.job_id,
        status=job.status.value,
        output_file=None,
    )


@app.get("/api/mix/{job_id}", response_model=MixResponse)
async def get_mix_status(job_id: str) -> MixResponse:
    """Get audio mixing job status.

    Args:
        job_id: The mixing job identifier.

    Returns:
        A :class:`MixResponse` with current status and output info.

    Raises:
        HTTPException: 404 if the job does not exist.
    """
    job = job_manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    return MixResponse(
        job_id=job.job_id,
        status=job.status.value,
        output_file=job.output_file,
    )


# -- Singing Synthesis -----------------------------------------------------


@app.post("/api/singing", response_model=SingingResponse)
async def generate_singing(
    lyrics: str = Form(...),
    melody: str | None = Form(default=None),
    melody_file: UploadFile | None = File(default=None),
    voice_model: str = Form(default="default"),
    tempo: int = Form(default=120),
    key_shift: int = Form(default=0),
) -> SingingResponse:
    """Generate singing from lyrics and melody.

    Supports three melody input methods:
    1. ABC notation string via *melody* parameter
    2. MIDI file upload via *melody_file* parameter
    3. Auto-generation if neither is provided (or melody="auto")

    Args:
        lyrics:       Song lyrics to synthesize (1-2000 characters).
        melody:       Melody in ABC notation or "auto" for auto-generation.
        melody_file:  Optional MIDI file for melody input.
        voice_model:  Singing voice model identifier (default: "default").
        tempo:        Tempo in BPM (60-240, default: 120).
        key_shift:    Semitone shift (-12 to +12, default: 0).

    Returns:
        A :class:`SingingResponse` with the new job_id and status.

    Raises:
        HTTPException: 400 on invalid parameters (empty lyrics, invalid tempo/key_shift).
    """
    # Validation
    if not lyrics.strip():
        raise HTTPException(status_code=400, detail="Lyrics are required.")

    if len(lyrics) > 2000:
        raise HTTPException(
            status_code=400, detail="Lyrics too long (max 2000 characters)."
        )

    if not 60 <= tempo <= 240:
        raise HTTPException(
            status_code=400, detail="Tempo must be between 60 and 240 BPM."
        )

    if not -12 <= key_shift <= 12:
        raise HTTPException(
            status_code=400, detail="Key shift must be between -12 and +12 semitones."
        )

    # Create job
    job = job_manager.create_job(InputType.TEXT, "singing_synthesis")
    job_dir = job_manager.get_job_dir(job.job_id)

    # Handle MIDI file upload
    midi_path: Path | None = None
    if melody_file is not None and melody_file.filename:
        if not melody_file.filename.lower().endswith((".mid", ".midi")):
            raise HTTPException(
                status_code=400,
                detail="Melody file must be a MIDI file (.mid or .midi).",
            )
        midi_path = job_dir / "references" / melody_file.filename
        await _save_upload(melody_file, midi_path)
        logger.info("MIDI file uploaded: %s", melody_file.filename)

    logger.info(
        "Singing generation request: job=%s voice=%s tempo=%d key_shift=%d lyrics_len=%d melody=%s",
        job.job_id,
        voice_model,
        tempo,
        key_shift,
        len(lyrics),
        "MIDI" if midi_path else (melody if melody else "auto"),
    )

    # Launch background task
    _launch_background_task(
        orchestrator.process_singing(
            job_id=job.job_id,
            lyrics=lyrics,
            melody=melody,
            voice_model=voice_model,
            tempo=tempo,
            key_shift=key_shift,
            melody_file_path=midi_path,
        )
    )

    return SingingResponse(
        job_id=job.job_id,
        status=job.status.value,
        output_file=None,
    )


@app.get("/api/singing/{job_id}", response_model=SingingResponse)
async def get_singing_status(job_id: str) -> SingingResponse:
    """Get singing synthesis job status.

    Args:
        job_id: The job identifier.

    Returns:
        A :class:`SingingResponse` with current status and output info.

    Raises:
        HTTPException: 404 if the job does not exist.
    """
    job = job_manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    return SingingResponse(
        job_id=job.job_id,
        status=job.status.value,
        output_file=job.output_file,
    )


@app.get("/api/singing-models")
async def list_singing_models() -> dict:
    """List available singing voice models.

    Returns:
        Dictionary with "models" key containing list of available singing models.
        Each model has: id, name, language, description.
    """
    models = orchestrator.singing_engine.list_available_models()
    return {"models": models}


# -- Download --------------------------------------------------------------


@app.get("/api/jobs/{job_id}/download")
async def download_output(
    job_id: str,
    format: str = Query(default="wav", pattern="^(wav|mp3|mp4)$"),  # noqa: A002
) -> FileResponse:
    """Download the final output file for a completed job.

    Args:
        job_id: The job identifier.
        format: Desired output format (``wav`` or ``mp3``).

    Raises:
        HTTPException: 404 if the job or output file is not found,
                       400 if the job is not completed.
    """
    job = job_manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    if job.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Job is not completed. Current status: {job.status.value}",
        )

    job_dir = job_manager.get_job_dir(job_id)
    output_dir = job_dir / "output"

    # Determine the file to serve.
    if format == "mp4":
        candidates = list(output_dir.glob("*.mp4"))
    elif format == "mp3":
        candidates = list(output_dir.glob("*.mp3"))
    else:
        candidates = list(output_dir.glob("*.wav"))

    if not candidates:
        # Fallback: try the output_file recorded on the job.
        if job.output_file and Path(job.output_file).exists():
            target = Path(job.output_file)
        else:
            raise HTTPException(
                status_code=404,
                detail=f"No {format} output file found for job {job_id}.",
            )
    else:
        target = candidates[0]

    media_type = _MEDIA_TYPES.get(format, "application/octet-stream")

    logger.info("Download: job=%s file=%s format=%s", job_id, target.name, format)

    return FileResponse(
        path=str(target),
        media_type=media_type,
        filename=target.name,
    )


# -- Delete ----------------------------------------------------------------


@app.delete("/api/jobs/{job_id}")
async def delete_job(job_id: str) -> dict:
    """Delete a job and all associated files from disk.

    Args:
        job_id: The job identifier.

    Raises:
        HTTPException: 404 if the job does not exist.
    """
    deleted = job_manager.delete_job(job_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    logger.info("Job deleted via API: %s", job_id)
    return {"message": "Job deleted", "job_id": job_id}


# -- Voice profiles --------------------------------------------------------


@app.post("/api/voices", response_model=VoiceProfileResponse)
async def create_voice_profile(
    name: str = Form(...),
    description: str = Form(default=""),
    audio: UploadFile = File(...),
) -> VoiceProfileResponse:
    """Create a new voice profile by uploading a reference audio file."""
    if not audio.filename:
        raise HTTPException(status_code=400, detail="Audio filename is required.")

    suffix = Path(audio.filename).suffix.lower()
    if suffix not in _AUDIO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format '{suffix}'. Allowed: {sorted(_AUDIO_EXTENSIONS)}",
        )

    voice = voice_manager.create_voice(name=name, description=description)
    voice_dir = voice_manager.get_voice_dir(voice.voice_id)
    dest_path = voice_dir / audio.filename

    await _save_upload(audio, dest_path)

    # Extract audio metadata.
    import soundfile as sf

    try:
        info = sf.info(str(dest_path))
        voice_manager.update_voice(
            voice.voice_id,
            audio_filename=audio.filename,
            sample_rate=info.samplerate,
            duration=info.duration,
        )
    except Exception:
        voice_manager.update_voice(voice.voice_id, audio_filename=audio.filename)

    voice = voice_manager.get_voice(voice.voice_id)
    return VoiceProfileResponse(**voice.model_dump())


@app.get("/api/voices", response_model=list[VoiceProfileResponse])
async def list_voice_profiles() -> list[VoiceProfileResponse]:
    """Return all saved voice profiles ordered by creation time."""
    voices = voice_manager.list_voices()
    return [VoiceProfileResponse(**v.model_dump()) for v in voices]


@app.get("/api/voices/{voice_id}", response_model=VoiceProfileResponse)
async def get_voice_profile(voice_id: str) -> VoiceProfileResponse:
    """Return details for a single voice profile."""
    voice = voice_manager.get_voice(voice_id)
    if voice is None:
        raise HTTPException(status_code=404, detail=f"Voice profile not found: {voice_id}")
    return VoiceProfileResponse(**voice.model_dump())


@app.delete("/api/voices/{voice_id}")
async def delete_voice_profile(voice_id: str) -> dict:
    """Delete a voice profile and its audio file from disk."""
    deleted = voice_manager.delete_voice(voice_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Voice profile not found: {voice_id}")
    return {"message": "Voice profile deleted", "voice_id": voice_id}


@app.get("/api/voices/{voice_id}/audio")
async def stream_voice_audio(voice_id: str) -> FileResponse:
    """Stream the reference audio file for a voice profile."""
    audio_path = voice_manager.get_audio_path(voice_id)
    if audio_path is None:
        raise HTTPException(status_code=404, detail=f"Audio not found for voice: {voice_id}")

    suffix = audio_path.suffix.lower().lstrip(".")
    media_type = _MEDIA_TYPES.get(suffix, "application/octet-stream")
    return FileResponse(
        path=str(audio_path),
        media_type=media_type,
        filename=audio_path.name,
    )


@app.post("/api/voices/from-job/{job_id}", response_model=VoiceProfileResponse)
async def create_voice_from_job(
    job_id: str,
    speaker_id: str = Form(...),
    name: str = Form(...),
    description: str = Form(default=""),
) -> VoiceProfileResponse:
    """Save a reference audio uploaded for a job as a reusable voice profile."""
    job = job_manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    speaker = next((s for s in job.speakers if s.speaker_id == speaker_id), None)
    if speaker is None or not speaker.assigned_voice_ref:
        raise HTTPException(
            status_code=400,
            detail=f"No voice reference found for speaker: {speaker_id}",
        )

    job_dir = job_manager.get_job_dir(job_id)
    ref_path = job_dir / "references" / speaker.assigned_voice_ref
    if not ref_path.exists():
        raise HTTPException(status_code=404, detail="Reference audio file not found on disk.")

    import shutil
    import soundfile as sf

    voice = voice_manager.create_voice(name=name, description=description)
    voice_dir = voice_manager.get_voice_dir(voice.voice_id)
    dest_path = voice_dir / ref_path.name
    shutil.copy2(str(ref_path), str(dest_path))

    try:
        info = sf.info(str(dest_path))
        voice_manager.update_voice(
            voice.voice_id,
            audio_filename=ref_path.name,
            sample_rate=info.samplerate,
            duration=info.duration,
        )
    except Exception:
        voice_manager.update_voice(voice.voice_id, audio_filename=ref_path.name)

    voice = voice_manager.get_voice(voice.voice_id)
    return VoiceProfileResponse(**voice.model_dump())


# -- Real-time voice changer ------------------------------------------------


def _decode_audio_blob(blob: bytes) -> tuple[np.ndarray, int]:
    """Decode a WebM/Opus audio blob from the browser into a numpy array.

    Uses pydub (which delegates to FFmpeg) to handle the WebM container,
    then converts to mono 16 kHz float32 for Whisper consumption.
    """
    from pydub import AudioSegment  # noqa: WPS433

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            suffix=".webm", delete=False,
        ) as tmp:
            tmp.write(blob)
            tmp_path = Path(tmp.name)

        seg = AudioSegment.from_file(str(tmp_path))
        seg = seg.set_channels(1).set_frame_rate(16000).set_sample_width(2)
        samples = np.array(seg.get_array_of_samples(), dtype=np.float32) / 32768.0
        return samples, 16000
    finally:
        if tmp_path is not None:
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass


def _encode_wav_bytes(audio: np.ndarray, sr: int) -> bytes:
    """Encode a numpy audio array to in-memory WAV bytes."""
    buf = io.BytesIO()
    import soundfile as sf  # noqa: WPS433
    sf.write(buf, audio, sr, format="WAV")
    return buf.getvalue()


@app.websocket("/ws/voice-changer")
async def voice_changer_ws(websocket: WebSocket) -> None:
    """Real-time voice changer via WebSocket.

    Protocol
    --------
    1. Client sends JSON config: ``{voice_id, tts_model, ref_text, language}``
    2. Server validates and replies ``{status: "ready"}``.
    3. Client sends binary audio blobs (WebM from MediaRecorder, ~3 s each).
    4. Server transcribes, synthesises, and sends back WAV bytes.
    5. Client sends ``{action: "stop"}`` to end the session.
    """
    await websocket.accept()
    logger.info("Voice changer WebSocket connected")

    try:
        # ---- 1. Receive configuration ------------------------------------
        config = await websocket.receive_json()
        voice_id: str = config.get("voice_id", "")
        tts_model: str = config.get("tts_model", "qwen3-tts")
        ref_text: str | None = config.get("ref_text") or None
        language: str | None = config.get("language") or None

        ref_path = voice_manager.get_audio_path(voice_id)
        if ref_path is None:
            await websocket.send_json({"error": f"Voice not found: {voice_id}"})
            await websocket.close()
            return

        await websocket.send_json({"status": "ready"})
        logger.info(
            "Voice changer session: voice=%s model=%s", voice_id, tts_model,
        )

        # ---- 2. Process audio chunks in a loop ----------------------------
        while True:
            message = await websocket.receive()

            # JSON control messages
            if "text" in message:
                data = json.loads(message["text"])
                if data.get("action") == "stop":
                    logger.info("Voice changer stopped by client")
                    break
                continue

            # Binary audio blobs
            if "bytes" not in message:
                continue

            try:
                # Decode browser audio
                audio, sr = await asyncio.to_thread(
                    _decode_audio_blob, message["bytes"],
                )

                # Transcribe
                await websocket.send_json({"status": "transcribing"})
                text = await orchestrator.transcriber.transcribe_buffer(audio, sr)
                if not text.strip():
                    await websocket.send_json({"status": "no_speech"})
                    continue

                await websocket.send_json({
                    "status": "synthesizing", "text": text,
                })

                # Synthesize with the selected TTS model
                from app.pipeline.tts_engine import (  # noqa: WPS433
                    MODEL_QWEN, MODEL_MMS, MODEL_INDICF5,
                )

                tts = orchestrator.tts_engine
                ref_str = str(ref_path)

                if tts_model == MODEL_MMS:
                    synth, synth_sr = await asyncio.to_thread(
                        tts._synthesize_mms, text,
                    )
                elif tts_model == MODEL_INDICF5:
                    synth, synth_sr = await asyncio.to_thread(
                        tts._synthesize_indicf5, text, ref_str, ref_text,
                    )
                else:
                    synth, synth_sr = await asyncio.to_thread(
                        tts._synthesize_qwen, text, ref_str, ref_text, language,
                    )

                # Send synthesised audio back
                wav_bytes = _encode_wav_bytes(synth, synth_sr)
                await websocket.send_bytes(wav_bytes)
                await websocket.send_json({"status": "chunk_done"})

            except Exception as exc:
                logger.error("Voice changer chunk error: %s", exc)
                try:
                    await websocket.send_json({"error": str(exc)})
                except Exception:
                    break

    except WebSocketDisconnect:
        logger.info("Voice changer WebSocket disconnected")
    except Exception as exc:
        logger.error("Voice changer WebSocket error: %s", exc)


# ---------------------------------------------------------------------------
# Real-Time Voice Changer Control API
# ---------------------------------------------------------------------------

# Initialize real-time components
from app.realtime import RealtimeAudioEngine, VoiceSelector  # noqa: E402

rt_audio_engine = RealtimeAudioEngine()
rt_voice_selector = VoiceSelector(voice_manager)


@app.websocket("/ws/realtime-control")
async def websocket_realtime_control(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time voice changer control.

    Handles commands for voice selection, audio start/stop, and status updates.
    Similar to Voicemod's Control API.
    """
    await websocket.accept()
    logger.info("Real-time control WebSocket connected")

    try:
        # Send initial status with presets
        from app.realtime.voice_presets import list_presets

        await websocket.send_json({
            "type": "connected",
            "status": rt_audio_engine.get_status(),
            "voices": rt_voice_selector.get_voice_library(),
            "presets": list_presets(),
            "effectParameters": rt_audio_engine.get_effect_parameters(),
        })

        # Process commands
        while True:
            data = await websocket.receive_json()
            action = data.get("action")

            try:
                if action == "getVoices":
                    # Return voice library
                    voices = rt_voice_selector.get_voice_library()
                    await websocket.send_json({
                        "type": "voices",
                        "voices": voices,
                    })

                elif action == "selectVoice":
                    # Switch to a different voice
                    voice_id = data.get("voiceId")
                    if not voice_id:
                        await websocket.send_json({
                            "type": "error",
                            "message": "voiceId required",
                        })
                        continue

                    voice_data = rt_voice_selector.select_voice(voice_id)
                    rt_audio_engine.set_voice(
                        voice_id,
                        voice_data["audio_path"],
                    )

                    await websocket.send_json({
                        "type": "voiceSelected",
                        "voice": voice_data,
                    })

                elif action == "start":
                    # Start real-time audio processing
                    input_device = data.get("inputDevice")
                    output_device = data.get("outputDevice")

                    rt_audio_engine.start(
                        input_device=input_device,
                        output_device=output_device,
                    )

                    await websocket.send_json({
                        "type": "started",
                        "status": rt_audio_engine.get_status(),
                    })

                elif action == "stop":
                    # Stop real-time audio processing
                    rt_audio_engine.stop()

                    await websocket.send_json({
                        "type": "stopped",
                        "status": rt_audio_engine.get_status(),
                    })

                elif action == "getStatus":
                    # Get current engine status
                    await websocket.send_json({
                        "type": "status",
                        "status": rt_audio_engine.get_status(),
                    })

                elif action == "getDevices":
                    # List audio devices
                    devices = rt_audio_engine.list_audio_devices()
                    await websocket.send_json({
                        "type": "devices",
                        "devices": devices,
                    })

                elif action == "assignHotkey":
                    # Assign hotkey to voice
                    voice_id = data.get("voiceId")
                    hotkey = data.get("hotkey")

                    if voice_id and hotkey:
                        rt_voice_selector.assign_hotkey(voice_id, hotkey)

                        await websocket.send_json({
                            "type": "hotkeyAssigned",
                            "voiceId": voice_id,
                            "hotkey": hotkey,
                        })

                elif action == "setEffectParameter":
                    # Update a single effect parameter
                    param_name = data.get("parameter")
                    value = data.get("value")

                    if param_name and value is not None:
                        rt_audio_engine.update_effect_parameter(param_name, value)

                        await websocket.send_json({
                            "type": "effectParameterUpdated",
                            "parameter": param_name,
                            "value": value,
                        })

                elif action == "getEffectParameters":
                    # Get current effect parameters
                    params = rt_audio_engine.get_effect_parameters()

                    await websocket.send_json({
                        "type": "effectParameters",
                        "parameters": params,
                    })

                elif action == "loadPreset":
                    # Load voice effect preset
                    preset_id = data.get("presetId")

                    if preset_id:
                        from app.realtime.voice_presets import get_preset_parameters

                        params = get_preset_parameters(preset_id)
                        rt_audio_engine.set_effect_parameters(params)

                        await websocket.send_json({
                            "type": "presetLoaded",
                            "presetId": preset_id,
                            "parameters": params.to_dict(),
                        })

                elif action == "getPresets":
                    # Get list of available presets
                    from app.realtime.voice_presets import list_presets

                    presets = list_presets()

                    await websocket.send_json({
                        "type": "presets",
                        "presets": presets,
                    })

                elif action == "playSoundboard":
                    # Play soundboard sound (placeholder - needs soundboard integration)
                    sound_id = data.get("soundId")
                    loop = data.get("loop", False)

                    if sound_id:
                        logger.info(f"Soundboard: {sound_id} (loop={loop})")

                        await websocket.send_json({
                            "type": "soundboardPlayed",
                            "soundId": sound_id,
                        })

                elif action == "stopSoundboard":
                    # Stop soundboard playback
                    logger.info("Soundboard stopped")

                    await websocket.send_json({
                        "type": "soundboardStopped",
                    })

                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Unknown action: {action}",
                    })

            except Exception as exc:
                logger.error("Real-time control error: %s", exc)
                await websocket.send_json({
                    "type": "error",
                    "message": str(exc),
                })

    except WebSocketDisconnect:
        logger.info("Real-time control WebSocket disconnected")
        # Stop audio processing if still running
        if rt_audio_engine.is_processing:
            rt_audio_engine.stop()
    except Exception as exc:
        logger.error("Real-time control WebSocket error: %s", exc)
