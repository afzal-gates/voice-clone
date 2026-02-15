# Real-Time Voice Changer WebSocket Protocol

## Connection

**Endpoint**: `/ws/realtime-control`

**Client Connection**:
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/realtime-control');
```

**Connection Lifecycle**:
1. Client connects to endpoint
2. Server sends `connected` message
3. Client sends `getVoices` action
4. Server responds with `voices` message
5. Client can now interact with voice changer

## Message Format

All messages are JSON-encoded strings.

### Client → Server (Actions)

#### Get Available Voices
```json
{
  "action": "getVoices"
}
```

#### Select Voice
```json
{
  "action": "selectVoice",
  "voiceId": "voice-123"
}
```

#### Start Processing
```json
{
  "action": "start"
}
```

#### Stop Processing
```json
{
  "action": "stop"
}
```

#### Get Audio Status
```json
{
  "action": "getStatus"
}
```

**Note**: `getStatus` is sent automatically every 200ms while processing is active.

### Server → Client (Messages)

#### Connection Established
```json
{
  "type": "connected"
}
```

#### Voice Library Response
```json
{
  "type": "voices",
  "voices": [
    {
      "id": "voice-natural-1",
      "name": "Natural Voice",
      "category": "realistic",
      "description": "A natural-sounding voice"
    },
    {
      "id": "voice-character-1",
      "name": "Character Voice",
      "category": "character",
      "description": "A character-style voice"
    },
    {
      "id": "voice-custom-1",
      "name": "My Custom Voice",
      "category": "custom",
      "description": "User-created voice"
    }
  ]
}
```

#### Voice Selection Confirmation
```json
{
  "type": "voiceSelected",
  "voice": {
    "id": "voice-natural-1",
    "name": "Natural Voice",
    "category": "realistic"
  }
}
```

#### Audio Status Update
```json
{
  "type": "status",
  "status": {
    "processing": true,
    "input_level": 0.65,
    "output_level": 0.72,
    "latency_ms": 45.2,
    "processing_time_ms": 12.8
  }
}
```

**Status Fields**:
- `processing`: Boolean indicating if voice changer is active
- `input_level`: Input audio level (0.0 to 1.0)
- `output_level`: Output audio level (0.0 to 1.0)
- `latency_ms`: Total latency in milliseconds
- `processing_time_ms`: Processing time per audio chunk in milliseconds

#### Error Message
```json
{
  "type": "error",
  "error": "Voice not found: voice-invalid-id"
}
```

## Typical User Flow

### 1. Initial Connection and Voice Selection

```
Client: Connect to /ws/realtime-control
Server: {"type": "connected"}

Client: {"action": "getVoices"}
Server: {"type": "voices", "voices": [...]}

Client: {"action": "selectVoice", "voiceId": "voice-123"}
Server: {"type": "voiceSelected", "voice": {...}}
```

### 2. Starting Voice Processing

```
Client: {"action": "start"}
Server: {"type": "status", "status": {"processing": true, ...}}

[Every 200ms while processing:]
Client: {"action": "getStatus"}
Server: {"type": "status", "status": {...}}
```

### 3. Stopping Voice Processing

```
Client: {"action": "stop"}
Server: {"type": "status", "status": {"processing": false, ...}}

[Status polling stops]
```

### 4. Error Handling

```
Client: {"action": "selectVoice", "voiceId": "invalid-id"}
Server: {"type": "error", "error": "Voice not found: invalid-id"}
```

## Implementation Requirements

### Backend Server

```python
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List
import json

class VoiceChangerWebSocket:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.processing_state: Dict[WebSocket, bool] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        await websocket.send_json({"type": "connected"})

    async def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if websocket in self.processing_state:
            del self.processing_state[websocket]

    async def handle_message(self, websocket: WebSocket, message: dict):
        action = message.get("action")

        if action == "getVoices":
            voices = await self.get_voice_library()
            await websocket.send_json({"type": "voices", "voices": voices})

        elif action == "selectVoice":
            voice_id = message.get("voiceId")
            voice = await self.select_voice(voice_id)
            if voice:
                await websocket.send_json({"type": "voiceSelected", "voice": voice})
            else:
                await websocket.send_json({
                    "type": "error",
                    "error": f"Voice not found: {voice_id}"
                })

        elif action == "start":
            await self.start_processing(websocket)
            status = await self.get_audio_status(websocket)
            await websocket.send_json({"type": "status", "status": status})

        elif action == "stop":
            await self.stop_processing(websocket)
            status = await self.get_audio_status(websocket)
            await websocket.send_json({"type": "status", "status": status})

        elif action == "getStatus":
            status = await self.get_audio_status(websocket)
            await websocket.send_json({"type": "status", "status": status})

@app.websocket("/ws/realtime-control")
async def websocket_endpoint(websocket: WebSocket):
    voice_changer = VoiceChangerWebSocket()
    await voice_changer.connect(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            await voice_changer.handle_message(websocket, message)
    except WebSocketDisconnect:
        await voice_changer.disconnect(websocket)
```

### Audio Processing Integration

The backend needs to integrate with the existing sounddevice-based audio processing:

```python
import sounddevice as sd
import numpy as np

class RealtimeAudioProcessor:
    def __init__(self):
        self.input_level = 0.0
        self.output_level = 0.0
        self.latency_ms = 0.0
        self.processing_time_ms = 0.0
        self.processing = False
        self.selected_voice = None

    def audio_callback(self, indata, outdata, frames, time, status):
        """Called by sounddevice for each audio chunk"""
        start_time = time.time()

        # Measure input level
        self.input_level = np.abs(indata).mean()

        # Apply voice transformation
        if self.processing and self.selected_voice:
            transformed = self.transform_voice(indata, self.selected_voice)
            outdata[:] = transformed
        else:
            outdata[:] = indata

        # Measure output level
        self.output_level = np.abs(outdata).mean()

        # Calculate processing time
        self.processing_time_ms = (time.time() - start_time) * 1000

    def start(self):
        """Start audio stream"""
        self.processing = True
        self.stream = sd.Stream(
            callback=self.audio_callback,
            channels=1,
            samplerate=44100,
            blocksize=1024
        )
        self.stream.start()

    def stop(self):
        """Stop audio stream"""
        self.processing = False
        if hasattr(self, 'stream'):
            self.stream.stop()
            self.stream.close()

    def get_status(self):
        """Get current audio status"""
        return {
            "processing": self.processing,
            "input_level": float(self.input_level),
            "output_level": float(self.output_level),
            "latency_ms": float(self.latency_ms),
            "processing_time_ms": float(self.processing_time_ms)
        }
```

## Voice Categories

### Realistic
Natural-sounding voices that closely mimic human speech patterns. Examples:
- Natural Male
- Natural Female
- Professional Speaker

### Character
Stylized voices with distinct characteristics. Examples:
- Robot Voice
- Cartoon Character
- Movie Character

### Custom
User-created or trained voices. Examples:
- User's own voice clone
- Celebrity impersonations
- Custom trained models

## Error Codes

| Error Message | Cause | Resolution |
|---------------|-------|------------|
| `Voice not found: {id}` | Invalid voice ID | Select valid voice from library |
| `No voice selected` | Start without selection | Select voice before starting |
| `Processing already active` | Start called twice | Stop before starting again |
| `Audio device not available` | Hardware issue | Check audio device settings |
| `Model loading failed` | Voice model error | Reload model or select different voice |

## Performance Considerations

### Status Polling Rate
- Default: 200ms (5 updates/second)
- Adjustable in `useAudioMeters` hook
- Balance between responsiveness and network traffic

### Audio Latency Targets
- **Excellent**: < 50ms
- **Good**: 50-100ms
- **Acceptable**: 100-200ms
- **Poor**: > 200ms

### Processing Time Targets
- **Excellent**: < 10ms
- **Good**: 10-20ms
- **Acceptable**: 20-40ms
- **Poor**: > 40ms

## Security Considerations

### Authentication
Consider adding authentication token to WebSocket connection:
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/realtime-control?token=xxx');
```

### Rate Limiting
Implement rate limiting for:
- Voice selection changes
- Start/stop actions
- Status requests

### Input Validation
- Validate all action types
- Validate voice IDs against database
- Sanitize error messages

## Testing

### Manual Testing
1. Connect to WebSocket
2. Verify `connected` message received
3. Request voice library
4. Select a voice
5. Start processing
6. Verify audio levels update
7. Stop processing
8. Disconnect

### Automated Testing
```python
import pytest
from fastapi.testclient import TestClient

def test_websocket_connection():
    with client.websocket_connect("/ws/realtime-control") as websocket:
        data = websocket.receive_json()
        assert data["type"] == "connected"

def test_get_voices():
    with client.websocket_connect("/ws/realtime-control") as websocket:
        websocket.send_json({"action": "getVoices"})
        data = websocket.receive_json()
        assert data["type"] == "voices"
        assert len(data["voices"]) > 0

def test_select_voice():
    with client.websocket_connect("/ws/realtime-control") as websocket:
        websocket.send_json({"action": "selectVoice", "voiceId": "voice-123"})
        data = websocket.receive_json()
        assert data["type"] == "voiceSelected"
```

## Troubleshooting

### Connection Issues
- Verify WebSocket proxy configuration in Vite
- Check backend server is running on port 8000
- Ensure WebSocket endpoint is registered

### No Voice Library
- Verify voice profiles exist in database
- Check `getVoices` implementation returns data
- Validate JSON serialization of voice objects

### No Audio Levels
- Verify `getStatus` action is being sent
- Check audio processing is active
- Validate status response format

### High Latency
- Check audio device buffer settings
- Optimize voice transformation code
- Reduce audio chunk size
- Monitor CPU usage

## Future Enhancements

### Potential Protocol Extensions
- Voice preview playback
- Audio format configuration
- Multi-voice mixing
- Real-time parameter adjustment
- Session recording
- Voice effect chaining
