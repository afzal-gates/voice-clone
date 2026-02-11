#!/usr/bin/env python3
"""Pre-download all models for offline operation.

Usage:
    python scripts/download_models.py                   # download all
    python scripts/download_models.py --model whisper    # download one
    python scripts/download_models.py --models-dir D:\\models --token hf_xxx

Models are cached under ``<models-dir>/huggingface/`` and
``<models-dir>/torch/`` using the standard HuggingFace Hub and
Torch Hub cache layouts.  After downloading, set ``MODELS_DIR``
in your ``.env`` and the app will use local models only.
"""

import argparse
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Ensure project root is on sys.path so we can read .env
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ---------------------------------------------------------------------------
# Read .env for HF_TOKEN
# ---------------------------------------------------------------------------
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass  # dotenv not installed — user can pass --token instead


# ---------------------------------------------------------------------------
# Model definitions
# ---------------------------------------------------------------------------

MODELS = {
    "whisper": {
        "label": "Faster-Whisper large-v3 (transcription)",
        "type": "hf_snapshot",
        "repo": "Systran/faster-whisper-large-v3",
        "gated": False,
    },
    "qwen-tts": {
        "label": "Qwen3-TTS 1.7B Base (multilingual TTS)",
        "type": "hf_snapshot",
        "repo": "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
        "gated": False,
    },
    "mms-tts": {
        "label": "MMS-TTS Bengali (Bengali TTS)",
        "type": "hf_snapshot",
        "repo": "facebook/mms-tts-ben",
        "gated": False,
    },
    "pyannote": {
        "label": "Pyannote speaker diarization 3.1 + sub-models",
        "type": "hf_snapshot_multi",
        "repos": [
            "pyannote/speaker-diarization-3.1",
            "pyannote/segmentation-3.0",
            "pyannote/wespeaker-voxceleb-resnet34-LM",
        ],
        "gated": True,
    },
    "indicf5": {
        "label": "IndicF5 (Indian languages TTS)",
        "type": "hf_files",
        "repo": "ai4bharat/IndicF5",
        "files": ["model.safetensors", "checkpoints/vocab.txt"],
        "gated": False,
    },
    "vocos": {
        "label": "Vocos vocoder (for IndicF5)",
        "type": "hf_snapshot",
        "repo": "charactr/vocos-mel-24khz",
        "gated": False,
    },
    "demucs": {
        "label": "Demucs htdemucs (vocal separation)",
        "type": "demucs",
        "model_name": "htdemucs",
    },
}


# ---------------------------------------------------------------------------
# Download helpers
# ---------------------------------------------------------------------------

def setup_env(models_dir: Path) -> None:
    """Set cache environment variables before importing download libs."""
    hf_home = str(models_dir / "huggingface")
    torch_home = str(models_dir / "torch")
    os.environ["HF_HOME"] = hf_home
    os.environ["TORCH_HOME"] = torch_home
    # Do NOT set HF_HUB_OFFLINE — we need network for downloading
    os.environ.pop("HF_HUB_OFFLINE", None)
    (models_dir / "huggingface").mkdir(parents=True, exist_ok=True)
    (models_dir / "torch").mkdir(parents=True, exist_ok=True)


def download_hf_snapshot(repo_id: str, token: str | None) -> str:
    """Download a full HF repo snapshot. Returns the cached path."""
    from huggingface_hub import snapshot_download
    path = snapshot_download(repo_id, token=token)
    return path


def download_hf_files(repo_id: str, filenames: list[str], token: str | None) -> list[str]:
    """Download specific files from a HF repo. Returns cached paths."""
    from huggingface_hub import hf_hub_download
    paths = []
    for fname in filenames:
        path = hf_hub_download(repo_id, filename=fname, token=token)
        paths.append(path)
    return paths


def download_demucs(model_name: str) -> None:
    """Pre-download Demucs model into torch hub cache."""
    from demucs.pretrained import get_model
    get_model(model_name)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def download_model(key: str, spec: dict, token: str | None) -> bool:
    """Download a single model. Returns True on success."""
    print(f"\n{'='*60}")
    print(f"  {spec['label']}")
    print(f"{'='*60}")

    if spec.get("gated") and not token:
        print("  WARNING: This model is gated and requires an HF token.")
        print("  Pass --token or set HF_TOKEN in .env")
        print("  Skipping...")
        return False

    try:
        model_type = spec["type"]

        if model_type == "hf_snapshot":
            path = download_hf_snapshot(spec["repo"], token)
            print(f"  Cached at: {path}")

        elif model_type == "hf_snapshot_multi":
            for repo in spec["repos"]:
                print(f"  Downloading {repo}...")
                path = download_hf_snapshot(repo, token)
                print(f"  Cached at: {path}")

        elif model_type == "hf_files":
            paths = download_hf_files(spec["repo"], spec["files"], token)
            for p in paths:
                print(f"  Cached at: {p}")

        elif model_type == "demucs":
            print(f"  Downloading {spec['model_name']} via torch hub...")
            download_demucs(spec["model_name"])
            print("  Cached in torch hub")

        print("  DONE")
        return True

    except Exception as exc:
        print(f"  FAILED: {exc}")
        return False


def get_dir_size(path: Path) -> str:
    """Get human-readable directory size."""
    total = 0
    if path.exists():
        for f in path.rglob("*"):
            if f.is_file():
                total += f.stat().st_size
    if total < 1024 * 1024:
        return f"{total / 1024:.1f} KB"
    if total < 1024 * 1024 * 1024:
        return f"{total / (1024 * 1024):.1f} MB"
    return f"{total / (1024 * 1024 * 1024):.2f} GB"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download all VoiceClone AI models for offline use.",
    )
    parser.add_argument(
        "--models-dir",
        type=Path,
        default=PROJECT_ROOT / "models",
        help="Directory to store models (default: models/)",
    )
    parser.add_argument(
        "--token",
        type=str,
        default=None,
        help="HuggingFace token (or set HF_TOKEN in .env)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        choices=list(MODELS.keys()),
        help="Download only this model (default: all)",
    )
    args = parser.parse_args()

    models_dir = args.models_dir.resolve()
    token = args.token or os.getenv("HF_TOKEN") or None

    print(f"Models directory: {models_dir}")
    print(f"HF token: {'set' if token else 'NOT SET (gated models will be skipped)'}")

    # Set up cache env vars BEFORE importing HF/torch libs
    setup_env(models_dir)

    # Determine which models to download
    if args.model:
        targets = {args.model: MODELS[args.model]}
    else:
        targets = MODELS

    # Download
    results = {}
    for key, spec in targets.items():
        results[key] = download_model(key, spec, token)

    # Summary
    print(f"\n{'='*60}")
    print("  DOWNLOAD SUMMARY")
    print(f"{'='*60}")
    for key, success in results.items():
        status = "OK" if success else "FAILED"
        print(f"  [{status:6s}] {MODELS[key]['label']}")

    hf_size = get_dir_size(models_dir / "huggingface")
    torch_size = get_dir_size(models_dir / "torch")
    print(f"\n  HuggingFace cache: {hf_size}")
    print(f"  Torch cache:       {torch_size}")
    print(f"  Total location:    {models_dir}")

    failed = sum(1 for v in results.values() if not v)
    if failed:
        print(f"\n  {failed} model(s) failed. Re-run to retry.")
        print("  For gated models, pass: --token YOUR_HF_TOKEN")
        sys.exit(1)
    else:
        print("\n  All models downloaded successfully!")
        print("  Set MODELS_DIR=models in your .env to run offline.")


if __name__ == "__main__":
    main()
