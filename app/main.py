"""FastAPI application for the VoiceClone AI platform.

Defines all HTTP endpoints for uploading media, managing jobs,
assigning reference voices, launching voice replacement, standalone
TTS, and downloading results.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.models import (
    InputType,
    JobDetailResponse,
    JobResponse,
    JobStatus,
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


@app.get("/api/tts-models")
async def list_tts_models() -> list[dict]:
    """Return the available TTS models with metadata."""
    from app.pipeline.tts_engine import MODEL_QWEN, MODEL_MMS

    return [
        {
            "id": MODEL_QWEN,
            "name": "Qwen3-TTS",
            "description": "Multilingual TTS with voice cloning",
            "supports_cloning": True,
            "languages": ["English", "Bengali", "Chinese", "Japanese", "Korean"],
        },
        {
            "id": MODEL_MMS,
            "name": "Meta MMS-TTS Bengali",
            "description": "Bengali text-to-speech (no voice cloning)",
            "supports_cloning": False,
            "languages": ["Bengali"],
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
) -> TTSResponse:
    """Synthesise speech from text with optional voice cloning.

    Provide either *voice_id* (a saved voice profile) or *reference_audio*
    (a one-time upload) to clone a voice.  If neither is given the default
    TTS voice is used.  Voice cloning is only available with Qwen3-TTS.

    Args:
        text:            The text to synthesise.
        reference_audio: Optional reference voice audio file.
        voice_id:        Optional saved voice profile ID.
        language:        Language for synthesis (e.g. "English", "Bengali").
                         ``None`` for auto-detection from text.
        tts_model:       TTS model to use (``qwen3-tts`` or ``mms-tts-ben``).
                         ``None`` defaults to ``qwen3-tts``.
        speed:           Playback speed multiplier (0.5 -- 2.0).
        pitch:           Pitch shift multiplier (0.5 -- 2.0).

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
    from app.pipeline.tts_engine import MODEL_QWEN, MODEL_MMS, AVAILABLE_MODELS

    resolved_model = tts_model if tts_model in AVAILABLE_MODELS else MODEL_QWEN

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

    _launch_background_task(
        orchestrator.process_tts(
            job_id=job.job_id,
            text=text,
            ref_audio_path=ref_path,
            speed=speed,
            pitch=pitch,
            language=tts_language,
            tts_model=resolved_model,
        )
    )

    return TTSResponse(
        job_id=job.job_id,
        status=job.status.value,
        output_file=None,
    )


# -- Download --------------------------------------------------------------


@app.get("/api/jobs/{job_id}/download")
async def download_output(
    job_id: str,
    format: str = Query(default="wav", regex="^(wav|mp3|mp4)$"),  # noqa: A002
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
