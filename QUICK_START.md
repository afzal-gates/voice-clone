# VoiceClone AI - Quick Start Guide

## Windows Batch Files

Three convenient batch files are provided for easy operation on Windows:

### 1. **start.bat** - Standard Startup
```bash
start.bat
```
- Checks for virtual environment
- Verifies Python installation
- Starts the FastAPI server
- Displays server logs in console
- Press Ctrl+C to stop

**Use when:** You want to see server logs and have full control

---

### 2. **start-with-browser.bat** - Auto-Open Browser
```bash
start-with-browser.bat
```
- Does everything `start.bat` does
- Automatically opens http://localhost:8000 in your browser
- Press any key to stop the server

**Use when:** You want quick access to the web interface

---

### 3. **stop.bat** - Stop Server
```bash
stop.bat
```
- Finds any running server on port 8000
- Safely terminates the process

**Use when:** Server is running in background or unresponsive

---

## Manual Startup (Alternative Methods)

### Method 1: Using Python
```bash
python run.py
```

### Method 2: Using Uvicorn Directly
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Method 3: With Virtual Environment
```bash
# Activate virtual environment
.venv\Scripts\activate

# Start server
python run.py
```

---

## First-Time Setup

If this is your first time running the application:

1. **Install Python 3.9+** (if not already installed)
   - Download from: https://www.python.org/downloads/

2. **Create Virtual Environment** (recommended)
   ```bash
   python -m venv .venv
   ```

3. **Install Dependencies**
   ```bash
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. **Run the Application**
   ```bash
   start.bat
   ```

---

## Accessing the Application

Once the server starts, access the application at:

**🌐 http://localhost:8000**

### Available Features:
1. **Voice Replace** - Replace voices in audio files
2. **Text-to-Speech** - Generate speech from text
3. **Music Generation** - Create background music
4. **Audio Mixer** - Mix TTS with music
5. **Real-time Voice Changer** - Live voice transformation
6. **Singing Synthesis** - Generate singing from lyrics

---

## Troubleshooting

### Port Already in Use
If you see "port 8000 already in use":
```bash
stop.bat
```
Then restart with `start.bat`

### Python Not Found
- Ensure Python 3.9+ is installed
- Add Python to system PATH
- Restart command prompt after installation

### Dependencies Not Installed
The batch file will automatically install dependencies, or run manually:
```bash
pip install -r requirements.txt
```

### Virtual Environment Issues
If `.venv` doesn't exist:
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

---

## Configuration

Edit `.env` file to configure:
- `HOST` - Server host (default: 0.0.0.0)
- `PORT` - Server port (default: 8000)
- `DEBUG` - Debug mode (default: true)
- `MUSICGEN_MOCK_MODE` - Mock music generation (default: true)

---

## Support

For issues or questions:
- Check server logs in the console
- Review `backend.log` for detailed logs
- Ensure all dependencies are installed
- Try stopping and restarting the server
