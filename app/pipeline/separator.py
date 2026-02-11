"""Audio source separation using Facebook's Demucs.

Splits an audio file into isolated vocal and accompaniment (background)
stems, enabling downstream processing on clean speech signals.
"""

from __future__ import annotations

import asyncio
import logging
import shutil
import subprocess
import sys
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)


class AudioSeparator:
    """Separate vocals from music/background noise using Demucs.

    The separator lazily loads the Demucs model on first use.  It tries the
    ``demucs.api`` Python interface first; if the API is unavailable it falls
    back to invoking Demucs as a CLI subprocess.

    Typical usage::

        separator = AudioSeparator()
        vocals, accompaniment = await separator.separate(audio_path, output_dir)
    """

    def __init__(self) -> None:
        self._separator = None
        self._use_cli_fallback: bool = False

    # ------------------------------------------------------------------
    # Lazy model loading
    # ------------------------------------------------------------------

    def _ensure_model(self) -> None:
        """Load the Demucs model if not already initialised.

        Attempts to use ``demucs.api.Separator`` for in-process inference.
        When the API module is not available (older Demucs versions or import
        errors), a flag is set so that :meth:`separate` will use the CLI
        fallback instead.
        """
        if self._separator is not None or self._use_cli_fallback:
            return

        try:
            from demucs.api import Separator as DemucsAPISeparator  # type: ignore[import-untyped]

            logger.info(
                "Loading Demucs model via API: %s", settings.DEMUCS_MODEL,
            )
            self._separator = DemucsAPISeparator(
                model=settings.DEMUCS_MODEL,
            )
            logger.info("Demucs API model loaded successfully")
        except Exception as exc:
            logger.warning(
                "Demucs API unavailable (%s); will use CLI fallback", exc,
            )
            self._use_cli_fallback = True

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def separate(
        self,
        audio_path: Path,
        output_dir: Path,
    ) -> tuple[Path, Path]:
        """Separate *audio_path* into vocals and accompaniment stems.

        The two output files are written to *output_dir* as
        ``vocals.wav`` and ``accompaniment.wav``.

        Args:
            audio_path: Path to the input audio file (WAV recommended).
            output_dir: Directory where output stems will be written.

        Returns:
            A ``(vocals_path, accompaniment_path)`` tuple of :class:`Path`
            objects pointing to the separated stems.

        Raises:
            FileNotFoundError: If *audio_path* does not exist.
            RuntimeError:      If Demucs separation fails.
        """
        audio_path = Path(audio_path)
        output_dir = Path(output_dir)

        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        output_dir.mkdir(parents=True, exist_ok=True)

        vocals_path = output_dir / "vocals.wav"
        accompaniment_path = output_dir / "accompaniment.wav"

        self._ensure_model()

        if self._use_cli_fallback:
            await self._separate_cli(audio_path, output_dir)
        else:
            await self._separate_api(audio_path, output_dir)

        # Validate that both stems were produced
        if not vocals_path.exists():
            raise RuntimeError(
                f"Demucs did not produce vocals output at {vocals_path}"
            )
        if not accompaniment_path.exists():
            raise RuntimeError(
                f"Demucs did not produce accompaniment output at {accompaniment_path}"
            )

        logger.info(
            "Separation complete: vocals=%s, accompaniment=%s",
            vocals_path.name,
            accompaniment_path.name,
        )
        return vocals_path, accompaniment_path

    # ------------------------------------------------------------------
    # API-based separation
    # ------------------------------------------------------------------

    async def _separate_api(
        self,
        audio_path: Path,
        output_dir: Path,
    ) -> None:
        """Run separation through the ``demucs.api`` Python interface."""
        logger.info("Separating with Demucs API: %s", audio_path.name)

        def _run() -> dict:
            """Blocking call executed in a worker thread."""
            # demucs.api.Separator.separate_audio_file returns a dict
            # mapping stem names to tensors.  We need to obtain the
            # file paths from the separation results.
            import torch  # type: ignore[import-untyped]
            import torchaudio  # type: ignore[import-untyped]

            # The API returns (origin, separated) where separated is a
            # dict of {stem_name: tensor}.
            origin, separated = self._separator.separate_audio_file(audio_path)

            result_paths: dict[str, Path] = {}
            for stem_name, audio_tensor in separated.items():
                stem_path = output_dir / f"{stem_name}.wav"
                # audio_tensor shape: (channels, samples)
                # Ensure 2D: (channels, samples)
                if audio_tensor.dim() == 1:
                    audio_tensor = audio_tensor.unsqueeze(0)
                torchaudio.save(
                    str(stem_path),
                    audio_tensor.cpu(),
                    self._separator.samplerate,
                )
                result_paths[stem_name] = stem_path

            return result_paths

        result_paths = await asyncio.to_thread(_run)

        # Demucs with --two-stems=vocals produces "vocals" and "no_vocals".
        # The htdemucs model may produce: drums, bass, other, vocals.
        # We normalise outputs to vocals.wav and accompaniment.wav.
        vocals_dest = output_dir / "vocals.wav"
        accompaniment_dest = output_dir / "accompaniment.wav"

        self._resolve_stem(result_paths, "vocals", vocals_dest)
        self._resolve_accompaniment(result_paths, accompaniment_dest)

    # ------------------------------------------------------------------
    # CLI fallback separation
    # ------------------------------------------------------------------

    async def _separate_cli(
        self,
        audio_path: Path,
        output_dir: Path,
    ) -> None:
        """Run separation via the ``demucs`` command-line interface."""
        logger.info("Separating with Demucs CLI: %s", audio_path.name)

        cmd = [
            sys.executable,
            "-m", "demucs",
            "--two-stems", "vocals",
            "-n", settings.DEMUCS_MODEL,
            "-o", str(output_dir),
            str(audio_path),
        ]

        result = await asyncio.to_thread(
            subprocess.run, cmd, capture_output=True,
        )

        if result.returncode != 0:
            stderr_text = result.stderr.decode(errors="replace").strip()
            logger.error(
                "Demucs CLI failed (rc=%d): %s", result.returncode, stderr_text,
            )
            raise RuntimeError(
                f"Demucs CLI separation failed with exit code "
                f"{result.returncode}: {stderr_text}"
            )

        # Demucs CLI writes to: output_dir/{model}/{stem}/{vocals.wav, no_vocals.wav}
        # The stem folder name is the input file name without extension.
        stem_name = audio_path.stem
        demucs_output_dir = output_dir / settings.DEMUCS_MODEL / stem_name

        vocals_src = demucs_output_dir / "vocals.wav"
        no_vocals_src = demucs_output_dir / "no_vocals.wav"

        vocals_dest = output_dir / "vocals.wav"
        accompaniment_dest = output_dir / "accompaniment.wav"

        if not vocals_src.exists():
            raise RuntimeError(
                f"Demucs CLI did not produce expected vocals at {vocals_src}"
            )

        shutil.copy2(str(vocals_src), str(vocals_dest))
        logger.debug("Copied vocals: %s -> %s", vocals_src, vocals_dest)

        if no_vocals_src.exists():
            shutil.copy2(str(no_vocals_src), str(accompaniment_dest))
            logger.debug(
                "Copied accompaniment: %s -> %s", no_vocals_src, accompaniment_dest,
            )
        else:
            logger.warning(
                "No accompaniment stem found at %s; "
                "accompaniment output will be missing",
                no_vocals_src,
            )

    # ------------------------------------------------------------------
    # Stem resolution helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_stem(
        result_paths: dict[str, Path],
        stem_name: str,
        dest: Path,
    ) -> None:
        """Copy or rename a stem from Demucs output to the canonical destination.

        Args:
            result_paths: Mapping of stem names to their file paths.
            stem_name:    The stem to resolve (e.g. ``"vocals"``).
            dest:         Canonical output path.
        """
        source = result_paths.get(stem_name)
        if source is None:
            raise RuntimeError(
                f"Demucs API did not produce a '{stem_name}' stem. "
                f"Available stems: {list(result_paths.keys())}"
            )
        if source != dest:
            shutil.copy2(str(source), str(dest))

    @staticmethod
    def _resolve_accompaniment(
        result_paths: dict[str, Path],
        dest: Path,
    ) -> None:
        """Build the accompaniment stem from Demucs output.

        Demucs may output ``no_vocals`` (two-stem mode) or individual
        instrument stems (``drums``, ``bass``, ``other``).  This method
        handles both cases:

        * If ``no_vocals`` exists, copy it directly.
        * Otherwise, mix all non-vocal stems into a single file.
        * As a last resort, copy the first available non-vocal stem.
        """
        # Prefer explicit no_vocals stem
        if "no_vocals" in result_paths:
            source = result_paths["no_vocals"]
            if source != dest:
                shutil.copy2(str(source), str(dest))
            return

        # Collect non-vocal stems
        non_vocal_stems = {
            name: path
            for name, path in result_paths.items()
            if name != "vocals"
        }

        if not non_vocal_stems:
            raise RuntimeError(
                "Demucs API produced only a vocals stem; "
                "cannot construct accompaniment."
            )

        if len(non_vocal_stems) == 1:
            # Single non-vocal stem -- use directly
            source = next(iter(non_vocal_stems.values()))
            if source != dest:
                shutil.copy2(str(source), str(dest))
            return

        # Multiple non-vocal stems -- mix them down
        try:
            import torch  # type: ignore[import-untyped]
            import torchaudio  # type: ignore[import-untyped]

            mixed: torch.Tensor | None = None
            sample_rate: int = 0

            for stem_path in non_vocal_stems.values():
                waveform, sr = torchaudio.load(str(stem_path))
                sample_rate = sr
                if mixed is None:
                    mixed = waveform
                else:
                    # Ensure matching lengths by truncating to shortest
                    min_len = min(mixed.shape[-1], waveform.shape[-1])
                    mixed = mixed[..., :min_len] + waveform[..., :min_len]

            if mixed is not None:
                torchaudio.save(str(dest), mixed, sample_rate)
                logger.debug("Mixed %d stems into accompaniment", len(non_vocal_stems))
        except ImportError:
            # Fallback: just use the first non-vocal stem
            source = next(iter(non_vocal_stems.values()))
            shutil.copy2(str(source), str(dest))
            logger.warning(
                "torch/torchaudio unavailable for mixing; "
                "using single stem '%s' as accompaniment",
                source.name,
            )
