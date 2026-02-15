"""Real-time audio processing engine for voice changing.

Handles microphone input, voice conversion, and audio output with low latency.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Callable, Optional

import numpy as np

from app.realtime.effects_processor import AudioEffectsProcessor, EffectParameters

logger = logging.getLogger(__name__)


class RealtimeAudioEngine:
    """Real-time audio processing engine.

    Manages audio capture from microphone, applies voice conversion,
    and outputs modified audio with minimal latency.

    Architecture:
        Microphone → Audio Callback → Voice Conversion → Output
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        block_size: int = 512,
        channels: int = 1,
    ):
        """Initialize audio engine.

        Args:
            sample_rate: Audio sample rate (Hz)
            block_size: Audio buffer size (samples)
            channels: Number of audio channels (1=mono, 2=stereo)
        """
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.channels = channels

        self.is_processing = False
        self.current_voice_id: Optional[str] = None
        self.stream = None

        # Audio statistics
        self.input_level = 0.0
        self.output_level = 0.0
        self.latency_ms = 0.0
        self.processing_time_ms = 0.0

        # Callbacks
        self.on_audio_processed: Optional[Callable[[np.ndarray], None]] = None
        self.on_status_update: Optional[Callable[[dict], None]] = None

        # Voice conversion model (placeholder for RVC/SO-VITS-SVC integration)
        self._voice_converter = None
        self._voice_embeddings = {}

        # Audio effects processor
        self.effects_processor = AudioEffectsProcessor(sample_rate=sample_rate)

    def start(
        self,
        input_device: Optional[int] = None,
        output_device: Optional[int] = None,
    ) -> None:
        """Start real-time audio processing.

        Args:
            input_device: Input device index (None = default)
            output_device: Output device index (None = default)

        Raises:
            RuntimeError: If no voice is selected or processing already started
        """
        if self.is_processing:
            raise RuntimeError("Audio processing already started")

        if not self.current_voice_id:
            raise RuntimeError("No voice selected. Call set_voice() first.")

        try:
            import sounddevice as sd
        except ImportError:
            raise RuntimeError(
                "sounddevice not installed. Run: pip install sounddevice"
            )

        logger.info("Starting real-time audio processing...")
        logger.info(
            f"Config: sample_rate={self.sample_rate}, "
            f"block_size={self.block_size}, channels={self.channels}"
        )

        self.is_processing = True

        # Create audio stream
        self.stream = sd.Stream(
            samplerate=self.sample_rate,
            blocksize=self.block_size,
            device=(input_device, output_device),
            channels=self.channels,
            dtype=np.float32,
            callback=self._audio_callback,
            latency="low",  # Request low-latency mode
        )

        self.stream.start()
        logger.info("Audio stream started successfully")

        # Broadcast status
        self._update_status(
            {
                "processing": True,
                "voice_id": self.current_voice_id,
                "sample_rate": self.sample_rate,
            }
        )

    def stop(self) -> None:
        """Stop real-time audio processing."""
        if not self.is_processing:
            return

        logger.info("Stopping real-time audio processing...")
        self.is_processing = False

        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None

        logger.info("Audio stream stopped")

        self._update_status({"processing": False})

    def set_voice(self, voice_id: str, voice_audio_path: str) -> None:
        """Set the target voice for conversion.

        Args:
            voice_id: Voice profile ID
            voice_audio_path: Path to voice reference audio

        Raises:
            FileNotFoundError: If voice audio file not found
        """
        from pathlib import Path

        audio_path = Path(voice_audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Voice audio not found: {audio_path}")

        logger.info(f"Setting target voice: {voice_id}")
        self.current_voice_id = voice_id

        # Load voice embedding (placeholder for actual voice conversion model)
        # TODO: Integrate RVC or SO-VITS-SVC voice conversion
        # self._voice_embeddings[voice_id] = self._load_voice_embedding(audio_path)

        logger.info(f"Voice set successfully: {voice_id}")

    def get_status(self) -> dict:
        """Get current engine status.

        Returns:
            Status dictionary with metrics
        """
        return {
            "processing": self.is_processing,
            "voice_id": self.current_voice_id,
            "input_level": self.input_level,
            "output_level": self.output_level,
            "latency_ms": self.latency_ms,
            "processing_time_ms": self.processing_time_ms,
            "sample_rate": self.sample_rate,
            "block_size": self.block_size,
        }

    def _audio_callback(
        self,
        indata: np.ndarray,
        outdata: np.ndarray,
        frames: int,
        time_info: any,
        status: any,
    ) -> None:
        """Real-time audio callback - processes audio frame-by-frame.

        This is the critical low-latency path. Keep processing minimal.

        Args:
            indata: Input audio buffer
            outdata: Output audio buffer
            frames: Number of frames
            time_info: Timing information
            status: Stream status
        """
        if status:
            logger.warning(f"Audio callback status: {status}")

        start_time = time.time()

        try:
            # Calculate input level
            self.input_level = float(np.max(np.abs(indata)))

            # Apply audio effects
            processed = self.effects_processor.process(indata[:, 0])

            # Apply voice conversion (if enabled in future)
            # TODO: Add RVC/SO-VITS-SVC voice conversion after effects
            if self._voice_converter and self.current_voice_id:
                # transformed = self._apply_voice_conversion(processed)
                # outdata[:] = transformed.reshape(-1, 1)
                outdata[:] = processed.reshape(-1, 1)
            else:
                # Effects only (no voice conversion)
                outdata[:] = processed.reshape(-1, 1)

            # Calculate output level
            self.output_level = float(np.max(np.abs(outdata)))

            # Measure processing time
            self.processing_time_ms = (time.time() - start_time) * 1000

            # Calculate latency (block duration + processing time)
            block_duration_ms = (frames / self.sample_rate) * 1000
            self.latency_ms = block_duration_ms + self.processing_time_ms

            # Optional callback for audio data
            if self.on_audio_processed:
                self.on_audio_processed(outdata)

        except Exception as e:
            logger.error(f"Error in audio callback: {e}")
            # On error, passthrough original audio
            outdata[:] = indata

    def _apply_voice_conversion(self, audio_chunk: np.ndarray) -> np.ndarray:
        """Apply voice conversion to audio chunk.

        This is where the actual voice transformation happens.

        Args:
            audio_chunk: Input audio samples (mono)

        Returns:
            Transformed audio samples

        Note:
            This is a placeholder. Integrate RVC, SO-VITS-SVC, or similar
            voice conversion model here.
        """
        # TODO: Implement actual voice conversion
        # Options:
        # 1. RVC (Retrieval-based Voice Conversion) - fastest
        # 2. SO-VITS-SVC - high quality
        # 3. OpenVoice - multi-lingual
        #
        # Example (pseudo-code):
        # voice_emb = self._voice_embeddings.get(self.current_voice_id)
        # if voice_emb:
        #     return self._voice_converter.convert(audio_chunk, voice_emb)

        # Placeholder: return input unchanged
        return audio_chunk

    def _update_status(self, status: dict) -> None:
        """Broadcast status update.

        Args:
            status: Status dictionary
        """
        if self.on_status_update:
            self.on_status_update(status)

    def list_audio_devices(self) -> list[dict]:
        """List available audio input/output devices.

        Returns:
            List of device dictionaries
        """
        try:
            import sounddevice as sd

            devices = sd.query_devices()
            result = []

            for i, dev in enumerate(devices):
                result.append({
                    "index": i,
                    "name": dev["name"],
                    "max_input_channels": dev["max_input_channels"],
                    "max_output_channels": dev["max_output_channels"],
                    "default_samplerate": dev["default_samplerate"],
                    "is_input": dev["max_input_channels"] > 0,
                    "is_output": dev["max_output_channels"] > 0,
                })

            return result

        except ImportError:
            logger.error("sounddevice not installed")
            return []

    def set_effect_parameters(self, params: EffectParameters) -> None:
        """Set audio effect parameters.

        Args:
            params: Effect parameters to apply
        """
        self.effects_processor.set_parameters(params)
        logger.info("Effect parameters updated")

    def update_effect_parameter(self, param_name: str, value: float | bool) -> None:
        """Update a single effect parameter.

        Args:
            param_name: Parameter name
            value: Parameter value
        """
        self.effects_processor.update_parameter(param_name, value)

    def get_effect_parameters(self) -> dict:
        """Get current effect parameters.

        Returns:
            Parameters dictionary
        """
        return self.effects_processor.get_parameters()
