"""Job lifecycle management with in-memory cache and file-system persistence.

Provides CRUD operations for voice-clone processing jobs.  Every mutation is
written through to a ``job.json`` file inside the job's storage directory so
that jobs survive application restarts.
"""

import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings
from app.models import InputType, JobInfo, JobStatus

logger = logging.getLogger(__name__)

# Sub-directories created inside every job folder.
_JOB_SUBDIRS: tuple[str, ...] = (
    "input",
    "vocals",
    "music",
    "segments",
    "output",
    "references",
)


class JobManager:
    """Manage voice-clone jobs with in-memory cache backed by JSON files.

    On construction the manager scans the jobs directory and loads any
    previously-persisted jobs into its in-memory cache so that the
    application can resume seamlessly after a restart.
    """

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def __init__(self) -> None:
        self._jobs: dict[str, JobInfo] = {}
        self._jobs_root: Path = settings.STORAGE_DIR / "jobs"
        self._jobs_root.mkdir(parents=True, exist_ok=True)
        self._load_all_jobs()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_job(self, input_type: InputType, filename: str) -> JobInfo:
        """Create a new job, persist it, and return the populated model.

        A fresh :class:`JobInfo` is generated with a unique ``job_id``.
        The corresponding directory tree is created on disk and the initial
        state is written to ``job.json``.

        Args:
            input_type: The media type of the uploaded input.
            filename:   Original filename of the uploaded file.

        Returns:
            The newly-created :class:`JobInfo` instance.
        """
        job = JobInfo(
            input_type=input_type,
            input_filename=filename,
            status=JobStatus.PENDING,
        )

        job_dir = self._job_dir(job.job_id)
        job_dir.mkdir(parents=True, exist_ok=True)
        for subdir in _JOB_SUBDIRS:
            (job_dir / subdir).mkdir(parents=True, exist_ok=True)

        self._jobs[job.job_id] = job
        self.save_job(job)

        logger.info(
            "Job created: id=%s type=%s file=%s",
            job.job_id,
            input_type.value,
            filename,
        )
        return job

    def get_job(self, job_id: str) -> JobInfo | None:
        """Return job by *job_id*, falling back to disk if not cached.

        Args:
            job_id: The 12-character hex identifier.

        Returns:
            The :class:`JobInfo` if found, otherwise ``None``.
        """
        if job_id in self._jobs:
            return self._jobs[job_id]

        # Attempt to recover from disk (e.g. after eviction or cold start).
        job = self.load_job(job_id)
        if job is not None:
            self._jobs[job_id] = job
        return job

    def update_job(self, job_id: str, **kwargs: object) -> JobInfo:
        """Update one or more fields on an existing job and persist.

        Automatically sets ``updated_at`` to the current UTC time.

        Args:
            job_id:  The 12-character hex identifier.
            **kwargs: Field names and their new values (must be valid
                      :class:`JobInfo` attributes).

        Returns:
            The updated :class:`JobInfo`.

        Raises:
            ValueError: If the job does not exist.
        """
        job = self.get_job(job_id)
        if job is None:
            raise ValueError(f"Job not found: {job_id}")

        for field, value in kwargs.items():
            if not hasattr(job, field):
                logger.warning(
                    "Ignoring unknown field %r on job %s", field, job_id
                )
                continue
            setattr(job, field, value)

        job.updated_at = datetime.now(timezone.utc)
        self._jobs[job_id] = job
        self.save_job(job)

        logger.debug(
            "Job updated: id=%s fields=%s",
            job_id,
            list(kwargs.keys()),
        )
        return job

    def list_jobs(self) -> list[JobInfo]:
        """Return all known jobs ordered by creation time (newest first).

        Returns:
            A list of :class:`JobInfo` instances.
        """
        return sorted(
            self._jobs.values(),
            key=lambda j: j.created_at,
            reverse=True,
        )

    def delete_job(self, job_id: str) -> bool:
        """Delete a job from memory and remove its directory tree from disk.

        Args:
            job_id: The 12-character hex identifier.

        Returns:
            ``True`` if the job existed and was deleted, ``False`` otherwise.
        """
        if job_id not in self._jobs:
            # Check disk in case it was only persisted there.
            if not self._job_dir(job_id).exists():
                logger.warning("Delete requested for unknown job: %s", job_id)
                return False

        self._jobs.pop(job_id, None)

        job_dir = self._job_dir(job_id)
        if job_dir.exists():
            shutil.rmtree(job_dir, ignore_errors=True)
            logger.info("Deleted job directory: %s", job_dir)

        logger.info("Job deleted: %s", job_id)
        return True

    def get_job_dir(self, job_id: str) -> Path:
        """Return the root directory for *job_id*.

        Args:
            job_id: The 12-character hex identifier.

        Returns:
            ``Path`` to ``{STORAGE_DIR}/jobs/{job_id}``.
        """
        return self._job_dir(job_id)

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def save_job(self, job: JobInfo) -> None:
        """Serialise *job* to its ``job.json`` file on disk.

        Args:
            job: The job model to persist.
        """
        job_dir = self._job_dir(job.job_id)
        job_dir.mkdir(parents=True, exist_ok=True)
        job_file = job_dir / "job.json"

        try:
            job_file.write_text(job.model_dump_json(indent=2), encoding="utf-8")
        except OSError:
            logger.exception("Failed to save job %s to disk", job.job_id)

    def load_job(self, job_id: str) -> JobInfo | None:
        """Deserialise a :class:`JobInfo` from its ``job.json`` on disk.

        Args:
            job_id: The 12-character hex identifier.

        Returns:
            The :class:`JobInfo` if the file exists and is valid, else ``None``.
        """
        job_file = self._job_dir(job_id) / "job.json"
        if not job_file.exists():
            return None

        try:
            raw = job_file.read_text(encoding="utf-8")
            return JobInfo.model_validate_json(raw)
        except Exception:
            logger.exception("Failed to load job from %s", job_file)
            return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _job_dir(self, job_id: str) -> Path:
        """Return the directory path for a given *job_id*."""
        return self._jobs_root / job_id

    def _load_all_jobs(self) -> None:
        """Scan the jobs directory and load all persisted jobs into memory.

        Called once during ``__init__``.  Invalid or corrupt JSON files are
        logged and skipped without raising.
        """
        if not self._jobs_root.exists():
            return

        loaded = 0
        for child in self._jobs_root.iterdir():
            if not child.is_dir():
                continue

            job = self.load_job(child.name)
            if job is not None:
                self._jobs[job.job_id] = job
                loaded += 1

        if loaded:
            logger.info(
                "Loaded %d existing job(s) from %s", loaded, self._jobs_root
            )
