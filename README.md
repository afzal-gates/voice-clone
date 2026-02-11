# VoiceClone AI

> **AI-powered voice replacement and dubbing platform** with speaker diarization, voice cloning, and real-time processing capabilities.

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0+-red.svg)](https://pytorch.org/)

---

## 📋 Table of Contents

- [Features](#-features)
- [System Requirements](#-system-requirements)
- [Quick Start](#-quick-start)
- [Installation](#-installation)
  - [Windows](#windows)
  - [Linux](#linux)
  - [macOS](#macos)
- [Configuration](#-configuration)
- [Running the Application](#-running-the-application)
- [API Documentation](#-api-documentation)
- [Offline Mode](#-offline-mode)
- [Project Structure](#-project-structure)
- [Troubleshooting](#-troubleshooting)
- [License](#-license)

---

## 🚀 Features

- **🎙️ Voice Cloning**: Clone any voice from audio samples
- **🔊 Speaker Diarization**: Automatically identify and separate multiple speakers
- **🎵 Audio Separation**: Isolate vocals from background music using Demucs
- **📝 Speech Transcription**: Accurate speech-to-text using Whisper
- **🗣️ Text-to-Speech**: Multiple TTS engines (Qwen3-TTS, MMS-TTS, IndicF5)
- **🎬 Video Support**: Process audio from video files (MP4, MKV, AVI, etc.)
- **⚡ Real-time Processing**: WebSocket support for live updates
- **🌐 RESTful API**: Comprehensive API with FastAPI
- **📦 Offline Mode**: Run completely offline after model downloads
- **🔧 Cross-platform**: Windows, Linux, and macOS support

---

## 💻 System Requirements

### Minimum Requirements
- **Python**: 3.9 or higher (3.10+ recommended)
- **RAM**: 8 GB minimum, 16 GB recommended
- **Storage**: 20 GB free space (for models and processing)
- **FFmpeg**: Required for audio/video processing

### Optional (Recommended)
- **GPU**: NVIDIA GPU with CUDA support for faster processing
- **VRAM**: 6 GB+ for large models

### Supported Operating Systems
- Windows 10/11
- Ubuntu 20.04+ / Debian 11+
- macOS 11+ (Intel and Apple Silicon)

---

## ⚡ Quick Start

```bash
# Clone the repository
git clone <repository-url>
cd voice-clone

# Copy environment configuration
cp .env.example .env

# Edit .env and add your Hugging Face token
# Get token from: https://huggingface.co/settings/tokens

# Run the setup script for your OS (see Installation section)

# Start the application
python run.py

# Access the application at http://localhost:8000
```

---

## 🔧 Installation

### Windows

#### Prerequisites
1. **Python 3.9+**: Download from [python.org](https://www.python.org/downloads/)
2. **FFmpeg** (Optional, auto-bundled): Or install via [Chocolatey](https://chocolatey.org/)
   ```cmd
   choco install ffmpeg
   ```

#### Installation Steps

```cmd
# 1. Create virtual environment
python -m venv .venv

# 2. Activate virtual environment
.venv\Scripts\activate

# 3. Install PyTorch (choose based on your hardware)

# For NVIDIA GPU:
pip install -r requirements-cuda.txt

# For CPU only:
pip install -r requirements-cpu.txt

# 4. Install other dependencies
pip install -r requirements.txt

# 5. Python 3.9 compatibility fix (if needed)
pip install eval-type-backport

# 6. Configure environment
copy .env.example .env
# Edit .env and add your HF_TOKEN
```

**Alternative: Automated Setup**
```cmd
scripts\setup-windows.bat
```

---

### Linux

#### Prerequisites
1. **Python 3.9+**
   ```bash
   # Ubuntu/Debian
   sudo apt update
   sudo apt install python3 python3-pip python3-venv

   # Fedora/RHEL
   sudo dnf install python3 python3-pip
   ```

2. **FFmpeg**
   ```bash
   # Ubuntu/Debian
   sudo apt install ffmpeg

   # Fedora/RHEL
   sudo dnf install ffmpeg

   # Arch Linux
   sudo pacman -S ffmpeg
   ```

#### Installation Steps

```bash
# 1. Create virtual environment
python3 -m venv .venv

# 2. Activate virtual environment
source .venv/bin/activate

# 3. Install PyTorch (choose based on your hardware)

# For NVIDIA GPU with CUDA:
pip install -r requirements-cuda.txt

# For CPU only:
pip install -r requirements-cpu.txt

# 4. Install other dependencies
pip install -r requirements.txt

# 5. Python 3.9 compatibility fix (if needed)
pip install eval-type-backport

# 6. Configure environment
cp .env.example .env
# Edit .env and add your HF_TOKEN
nano .env
```

**Alternative: Automated Setup**
```bash
bash scripts/setup-linux.sh
```

---

### macOS

#### Prerequisites
1. **Homebrew**: Install from [brew.sh](https://brew.sh/)
2. **Python 3.9+**
   ```bash
   brew install python@3.9
   ```
3. **FFmpeg**
   ```bash
   brew install ffmpeg
   ```

#### Installation Steps

```bash
# 1. Create virtual environment
python3 -m venv .venv

# 2. Activate virtual environment
source .venv/bin/activate

# 3. Install PyTorch

# For Apple Silicon (M1/M2/M3):
pip install torch torchaudio

# For Intel Mac (CPU only):
pip install -r requirements-cpu.txt

# 4. Install other dependencies
pip install -r requirements.txt

# 5. Python 3.9 compatibility fix (if needed)
pip install eval-type-backport

# 6. Configure environment
cp .env.example .env
# Edit .env and add your HF_TOKEN
nano .env
```

**Alternative: Automated Setup**
```bash
bash scripts/setup-macos.sh
```

---

## ⚙️ Configuration

### Required Configuration

Edit the `.env` file with your settings:

```bash
# Required: Hugging Face Token for gated models
HF_TOKEN=hf_your_token_here

# Application Settings
APP_NAME=VoiceClone AI
APP_VERSION=1.0.0
HOST=0.0.0.0
PORT=8000
DEBUG=false

# Storage
STORAGE_DIR=storage

# Model Settings (defaults are fine for most cases)
WHISPER_MODEL=large-v3
DEMUCS_MODEL=htdemucs
QWEN_TTS_MODEL=Qwen/Qwen3-TTS-12Hz-1.7B-Base
```

### Getting a Hugging Face Token

1. Go to [Hugging Face Settings](https://huggingface.co/settings/tokens)
2. Create a new token with "Read" access
3. Accept the terms for gated models:
   - [pyannote/speaker-diarization-3.1](https://huggingface.co/pyannote/speaker-diarization-3.1)
   - [Qwen/Qwen3-TTS-12Hz-1.7B-Base](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-Base)

### Optional Configuration

```bash
# Audio Processing
SAMPLE_RATE=24000
OUTPUT_FORMAT=wav

# Model Compute Settings
WHISPER_DEVICE=auto          # auto | cpu | cuda
WHISPER_COMPUTE_TYPE=float16 # float16 | float32 | int8

# Speaker Diarization
MIN_SPEAKERS=1
MAX_SPEAKERS=10

# Limits
MAX_FILE_SIZE_MB=500
CHUNK_DURATION_S=30
```

---

## 🎯 Running the Application

### Standard Mode

```bash
# Activate virtual environment first
# Windows:
.venv\Scripts\activate

# Linux/macOS:
source .venv/bin/activate

# Run the application
python run.py
```

### Alternative: Direct uvicorn

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Using Scripts

**Windows:**
```cmd
scripts\run.bat
```

**Linux/macOS:**
```bash
bash scripts/run.sh
```

### Development Mode

Enable auto-reload for development:

```bash
# Set in .env
DEBUG=true

# Then run
python run.py
```

### Access the Application

Once running, access:
- **API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Alternative API Docs**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/api/health

---

## 📚 API Documentation

### Core Endpoints

#### 🏥 Health & Settings
```http
GET /api/health         # Health check
GET /api/settings       # Application settings
```

#### 📤 File Upload & Job Management
```http
POST /api/upload        # Upload media file (audio/video)
GET  /api/jobs          # List all jobs
GET  /api/jobs/{id}     # Get job details
DELETE /api/jobs/{id}   # Delete job
```

#### 🎙️ Voice Management
```http
POST /api/voices/upload       # Upload reference voice
GET  /api/voices              # List all voices
GET  /api/voices/{id}         # Get voice details
DELETE /api/voices/{id}       # Delete voice
```

#### 🎬 Voice Replacement Pipeline
```http
POST /api/jobs/{id}/voices     # Assign voices to speakers
POST /api/jobs/{id}/process    # Start voice replacement
GET  /api/jobs/{id}/output     # Download processed output
```

#### 🗣️ Direct TTS
```http
POST /api/tts/generate         # Generate speech from text
POST /api/tts/clone            # Clone voice with text
```

#### 🔌 WebSocket
```http
WS /api/jobs/{id}/ws           # Real-time job progress updates
```

### Example Usage

**Upload a video:**
```bash
curl -X POST http://localhost:8000/api/upload \
  -F "file=@video.mp4" \
  -F "input_type=video"
```

**Generate TTS:**
```bash
curl -X POST http://localhost:8000/api/tts/generate \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, this is a test",
    "language": "en",
    "output_path": "output.wav"
  }'
```

**Interactive API Documentation:**
Visit http://localhost:8000/docs for a complete interactive API reference powered by Swagger UI.

---

## 🔒 Offline Mode

Run completely offline after downloading models once:

### Download Models

```bash
# Activate virtual environment
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

# Download all models
python scripts/download_models.py

# This downloads:
# - Whisper (speech recognition)
# - Pyannote (speaker diarization)
# - Demucs (audio separation)
# - Qwen TTS (text-to-speech)
# - IndicF5 TTS (multilingual TTS)
```

### Configure Offline Mode

Edit `.env`:
```bash
# Set models directory
MODELS_DIR=models

# Enable offline mode
HF_HUB_OFFLINE=1
```

Now the application runs without internet access!

---

## 📁 Project Structure

```
voice-clone/
├── app/
│   ├── __init__.py           # Package version
│   ├── config.py             # Configuration loader
│   ├── main.py               # FastAPI application
│   ├── models.py             # Pydantic data models
│   ├── pipeline/             # Processing pipeline
│   │   ├── aligner.py        # Audio alignment
│   │   ├── audio_extractor.py # Media extraction
│   │   ├── diarizer.py       # Speaker diarization
│   │   ├── merger.py         # Audio merging
│   │   ├── separator.py      # Vocal separation
│   │   ├── transcriber.py    # Speech-to-text
│   │   └── tts_engine.py     # Text-to-speech
│   ├── services/             # Business logic
│   │   ├── job_manager.py    # Job lifecycle
│   │   ├── pipeline_orchestrator.py # Pipeline coordination
│   │   └── voice_manager.py  # Voice profile management
│   ├── utils/                # Utilities
│   │   └── audio_utils.py    # Audio processing helpers
│   └── static/               # Frontend files (if any)
├── scripts/                  # Setup & utility scripts
│   ├── download_models.py    # Model downloader
│   ├── setup-windows.bat     # Windows setup
│   ├── setup-linux.sh        # Linux setup
│   ├── setup-macos.sh        # macOS setup
│   ├── run.bat               # Windows runner
│   └── run.sh                # Linux/macOS runner
├── storage/                  # Runtime data (auto-created)
│   ├── jobs/                 # Job processing files
│   └── voices/               # Voice profiles
├── .env                      # Environment config (create from .env.example)
├── .env.example              # Configuration template
├── requirements.txt          # Python dependencies
├── requirements-cuda.txt     # PyTorch with CUDA
├── requirements-cpu.txt      # PyTorch CPU-only
├── run.py                    # Application entry point
└── README.md                 # This file
```

---

## 🐛 Troubleshooting

### Common Issues

#### 1. **Python Version Error**
```
TypeError: unsupported operand type(s) for |
```
**Solution**: Install compatibility package
```bash
pip install eval-type-backport
```

#### 2. **FFmpeg Not Found**
```
FFmpeg not found in PATH
```
**Solution**: Install FFmpeg
```bash
# Windows
choco install ffmpeg

# Linux
sudo apt install ffmpeg

# macOS
brew install ffmpeg
```

#### 3. **CUDA Out of Memory**
```
RuntimeError: CUDA out of memory
```
**Solution**: Use CPU mode or reduce batch size
```bash
# In .env
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
```

#### 4. **Hugging Face Token Error**
```
Repo model ... is gated. You must be authenticated
```
**Solution**:
1. Get token from https://huggingface.co/settings/tokens
2. Add to `.env`: `HF_TOKEN=hf_your_token`
3. Accept terms for gated models

#### 5. **Module Not Found**
```
ModuleNotFoundError: No module named 'cffi'
```
**Solution**: Install missing dependencies
```bash
pip install cffi soundfile
```

#### 6. **Port Already in Use**
```
Error: [Errno 48] Address already in use
```
**Solution**: Change port in `.env`
```bash
PORT=8001
```

### Platform-Specific Issues

#### Windows: Long Path Support
Enable long paths if you encounter path-too-long errors:
```cmd
# Run as Administrator
reg add HKLM\SYSTEM\CurrentControlSet\Control\FileSystem /v LongPathsEnabled /t REG_DWORD /d 1 /f
```

#### Linux: Permission Denied
```bash
# Make scripts executable
chmod +x scripts/*.sh
```

#### macOS: SSL Certificate Error
```bash
# Install certificates
/Applications/Python\ 3.9/Install\ Certificates.command
```

### Getting Help

1. Check logs in the console output
2. Enable debug mode: `DEBUG=true` in `.env`
3. Check API docs: http://localhost:8000/docs
4. Review configuration: http://localhost:8000/api/settings

---

## 📊 Performance Tips

### GPU Acceleration
- Install CUDA-enabled PyTorch for 5-10x faster processing
- Requires NVIDIA GPU with CUDA support

### Memory Optimization
- Use `int8` compute type for lower VRAM usage
- Reduce `MAX_SPEAKERS` if you know speaker count
- Process shorter audio chunks with `CHUNK_DURATION_S`

### Model Selection
```bash
# Faster models (lower quality)
WHISPER_MODEL=base           # ~1 GB VRAM
DEMUCS_MODEL=htdemucs        # ~2 GB VRAM

# Slower models (higher quality)
WHISPER_MODEL=large-v3       # ~5 GB VRAM
DEMUCS_MODEL=mdx_extra       # ~4 GB VRAM
```

---

## 🔐 Security Notes

- **API Access**: Default configuration allows all origins (CORS `*`)
- **File Uploads**: Limited to `MAX_FILE_SIZE_MB` (default 500 MB)
- **Storage**: Jobs and voices stored in `STORAGE_DIR` (default: `./storage`)
- **Tokens**: Keep your `HF_TOKEN` secret, don't commit `.env` to git

---

## 🛠️ Development

### Running Tests
```bash
pytest tests/
```

### Code Formatting
```bash
black app/
isort app/
```

### Type Checking
```bash
mypy app/
```

---

## 📝 License

[Add your license information here]

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

## 🙏 Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
- [PyTorch](https://pytorch.org/) - Deep learning framework
- [Whisper](https://github.com/openai/whisper) - Speech recognition
- [Pyannote](https://github.com/pyannote/pyannote-audio) - Speaker diarization
- [Demucs](https://github.com/facebookresearch/demucs) - Audio separation
- [Qwen3-TTS](https://huggingface.co/Qwen) - Text-to-speech
- [IndicF5](https://huggingface.co/ai4bharat/IndicF5) - Multilingual TTS

---

<div align="center">
  <strong>Made with ❤️ for the voice cloning community</strong>
</div>
