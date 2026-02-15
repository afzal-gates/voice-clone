# Offline Mode Configuration

This guide explains how to run the application completely offline after downloading all required models.

## What Gets Downloaded

When you use the application for the first time, these models are downloaded from HuggingFace:

1. **Pyannote Speaker Diarization** (~300MB) - for speaker detection
2. **Whisper Large-v3** (~3GB) - for speech transcription
3. **Qwen TTS** (~3.5GB) - for text-to-speech
4. **IndicF5 TTS** (~600MB) - for Indian language TTS
5. **Demucs** (~350MB) - for audio source separation

Total: ~7.5GB of models

## Model Cache Locations

Models are cached in:
```
Windows: C:\Users\<username>\.cache\huggingface\hub\
Linux/Mac: ~/.cache/huggingface/hub/
```

## Steps to Enable Offline Mode

### 1. Download All Models First

Run these scripts while connected to internet:

```bash
# Download all models
python scripts/download_models.py

# Or download IndicF5 separately if needed
python download_indicf5.py
```

### 2. Configure Environment for Offline Mode

Add these to your `.env` file:

```bash
# Force offline mode - prevents any internet calls
HF_HUB_OFFLINE=1
TRANSFORMERS_OFFLINE=1

# Use local cache only
HF_DATASETS_OFFLINE=1
```

### 3. Verify Offline Mode

Test that everything works without internet:

```bash
# Disable network (Windows)
ipconfig /release

# Or disconnect WiFi, then test:
python run.py
```

## Troubleshooting Offline Mode

### Error: "Cannot access gated repo"
- **Cause**: Model not downloaded or token not configured
- **Fix**: Download the model first while online with your HF_TOKEN set

### Error: "No module named 'transformers'"
- **Cause**: Missing Python package
- **Fix**: `pip install transformers` (can be done offline if you have wheel files)

### Error: "Failed to load model"
- **Cause**: Model files corrupted or incomplete
- **Fix**: Delete cache and re-download:
  ```bash
  # Windows
  rmdir /s "C:\Users\<username>\.cache\huggingface"

  # Linux/Mac
  rm -rf ~/.cache/huggingface
  ```
  Then re-download with `python scripts/download_models.py`

## Transferring Models to Offline Machine

If you need to install on a machine without internet:

1. **On online machine**: Download all models to cache
2. **Copy cache folder**:
   ```bash
   # From: C:\Users\<user>\.cache\huggingface\
   # To: USB drive or network share
   ```
3. **On offline machine**:
   - Install Python packages from wheels (pip download on online machine first)
   - Copy cache folder to same location
   - Set offline environment variables

## Checking What's Downloaded

```bash
# List cached models
python -c "from pathlib import Path; print(list(Path.home().joinpath('.cache/huggingface/hub').glob('models--*')))"
```

## Model Sizes

| Model | Size | Required For |
|-------|------|--------------|
| pyannote/speaker-diarization-3.1 | ~300MB | Speaker detection |
| openai/whisper-large-v3 | ~3GB | Transcription |
| Qwen/Qwen3-TTS-12Hz-1.7B-Base | ~3.5GB | TTS |
| ai4bharat/IndicF5 | ~600MB | Indian language TTS |
| facebook/htdemucs | ~350MB | Audio separation |

Total: ~7.5GB
