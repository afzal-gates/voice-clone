"""Real-time audio effects processor for voice modification.

Provides Voicemod-style audio effects including pitch shifting, reverb,
echo, chorus, distortion, noise gate, and equalization.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, asdict
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class EffectParameters:
    """Parameters for audio effects."""

    # Pitch & Formant
    pitch_shift: float = 0.0  # semitones (-12 to +12)
    formant_shift: float = 1.0  # ratio (0.5 to 2.0)

    # Reverb
    reverb_enabled: bool = False
    reverb_room_size: float = 0.5  # 0.0 to 1.0
    reverb_damping: float = 0.5  # 0.0 to 1.0
    reverb_wet: float = 0.3  # 0.0 to 1.0 (mix amount)

    # Delay/Echo
    delay_enabled: bool = False
    delay_time: float = 0.3  # seconds (0.01 to 2.0)
    delay_feedback: float = 0.4  # 0.0 to 0.9
    delay_mix: float = 0.3  # 0.0 to 1.0

    # Chorus
    chorus_enabled: bool = False
    chorus_rate: float = 1.5  # Hz (0.1 to 10.0)
    chorus_depth: float = 0.025  # 0.0 to 1.0
    chorus_mix: float = 0.5  # 0.0 to 1.0

    # Distortion
    distortion_enabled: bool = False
    distortion_gain: float = 5.0  # 1.0 to 50.0
    distortion_mix: float = 0.5  # 0.0 to 1.0

    # Noise Gate
    noise_gate_enabled: bool = False
    noise_gate_threshold: float = -40.0  # dB (-60 to 0)
    noise_gate_ratio: float = 4.0  # 1.0 to 10.0

    # Equalizer (3-band)
    eq_enabled: bool = False
    eq_low_gain: float = 0.0  # dB (-12 to +12)
    eq_mid_gain: float = 0.0  # dB (-12 to +12)
    eq_high_gain: float = 0.0  # dB (-12 to +12)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> EffectParameters:
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


class AudioEffectsProcessor:
    """Real-time audio effects processor.

    Applies various audio effects to audio streams in real-time
    with minimal latency using efficient NumPy operations.
    """

    def __init__(self, sample_rate: int = 16000):
        """Initialize effects processor.

        Args:
            sample_rate: Audio sample rate in Hz
        """
        self.sample_rate = sample_rate
        self.params = EffectParameters()

        # Effect state buffers
        self._delay_buffer: Optional[np.ndarray] = None
        self._chorus_phase = 0.0
        self._reverb_buffer: Optional[np.ndarray] = None

        # Noise gate envelope follower
        self._gate_envelope = 0.0

        logger.info(f"Audio effects processor initialized (sample_rate={sample_rate})")

    def set_parameters(self, params: EffectParameters) -> None:
        """Update effect parameters.

        Args:
            params: New effect parameters
        """
        self.params = params
        self._reset_buffers()

    def update_parameter(self, param_name: str, value: float | bool) -> None:
        """Update a single parameter.

        Args:
            param_name: Parameter name (e.g., 'pitch_shift', 'reverb_enabled')
            value: New parameter value
        """
        if hasattr(self.params, param_name):
            setattr(self.params, param_name, value)
            logger.debug(f"Updated {param_name} = {value}")
        else:
            logger.warning(f"Unknown parameter: {param_name}")

    def process(self, audio: np.ndarray) -> np.ndarray:
        """Process audio with enabled effects.

        Args:
            audio: Input audio samples (mono, float32, range -1 to +1)

        Returns:
            Processed audio samples (same shape as input)
        """
        if audio.size == 0:
            return audio

        # Ensure correct data type and shape
        audio = audio.astype(np.float32).flatten()

        # Apply effects in order
        processed = audio.copy()

        # 1. Noise Gate (should be first to eliminate noise early)
        if self.params.noise_gate_enabled:
            processed = self._apply_noise_gate(processed)

        # 2. EQ (before pitch/formant for better tone control)
        if self.params.eq_enabled:
            processed = self._apply_equalizer(processed)

        # 3. Pitch Shift (affects fundamental frequency)
        if abs(self.params.pitch_shift) > 0.1:  # Only if significant shift
            processed = self._apply_pitch_shift(processed, self.params.pitch_shift)

        # 4. Formant Shift (affects voice character)
        if abs(self.params.formant_shift - 1.0) > 0.05:  # Only if not 1.0
            processed = self._apply_formant_shift(processed, self.params.formant_shift)

        # 5. Distortion (before time-based effects)
        if self.params.distortion_enabled:
            processed = self._apply_distortion(processed)

        # 6. Chorus (time-based modulation)
        if self.params.chorus_enabled:
            processed = self._apply_chorus(processed)

        # 7. Delay (time-based echo)
        if self.params.delay_enabled:
            processed = self._apply_delay(processed)

        # 8. Reverb (should be last for natural space simulation)
        if self.params.reverb_enabled:
            processed = self._apply_reverb(processed)

        # Ensure output is in valid range
        processed = np.clip(processed, -1.0, 1.0)

        return processed

    def _apply_pitch_shift(self, audio: np.ndarray, semitones: float) -> np.ndarray:
        """Apply pitch shifting.

        Args:
            audio: Input audio
            semitones: Pitch shift in semitones (-12 to +12)

        Returns:
            Pitch-shifted audio
        """
        if semitones == 0:
            return audio

        try:
            import librosa

            # Pitch shift using librosa (high quality but CPU intensive)
            shifted = librosa.effects.pitch_shift(
                audio, sr=self.sample_rate, n_steps=semitones
            )
            return shifted.astype(np.float32)

        except Exception as e:
            logger.warning(f"Pitch shift failed: {e}, using simple resampling")
            # Fallback: simple time-stretch approximation
            ratio = 2 ** (-semitones / 12.0)
            indices = np.arange(0, len(audio), ratio)
            indices = np.clip(indices, 0, len(audio) - 1).astype(int)
            return audio[indices]

    def _apply_formant_shift(self, audio: np.ndarray, ratio: float) -> np.ndarray:
        """Apply formant shifting to change voice character.

        Args:
            audio: Input audio
            ratio: Formant shift ratio (0.5 to 2.0)

        Returns:
            Formant-shifted audio
        """
        if ratio == 1.0:
            return audio

        try:
            from scipy import signal

            # Formant shifting via frequency domain manipulation
            # This is a simplified approach - professional formant shifting
            # requires more sophisticated algorithms (e.g., LPC analysis)

            # Simple approach: stretch/compress spectrum
            spectrum = np.fft.rfft(audio)
            freqs = np.fft.rfftfreq(len(audio), 1 / self.sample_rate)

            # Warp frequencies
            new_freqs = freqs * ratio
            new_freqs = np.clip(new_freqs, 0, self.sample_rate / 2)

            # Interpolate spectrum
            new_spectrum = np.interp(freqs, new_freqs, np.abs(spectrum)) * np.exp(
                1j * np.angle(spectrum)
            )

            result = np.fft.irfft(new_spectrum, n=len(audio))
            return result.astype(np.float32)

        except Exception as e:
            logger.warning(f"Formant shift failed: {e}")
            return audio

    def _apply_reverb(self, audio: np.ndarray) -> np.ndarray:
        """Apply reverb effect.

        Args:
            audio: Input audio

        Returns:
            Audio with reverb
        """
        # Initialize reverb buffer if needed
        reverb_length = int(self.sample_rate * self.params.reverb_room_size * 0.5)
        if self._reverb_buffer is None or len(self._reverb_buffer) != reverb_length:
            self._reverb_buffer = np.zeros(reverb_length, dtype=np.float32)

        # Simple Schroeder reverb approximation
        output = audio.copy()

        for i in range(len(audio)):
            # Read from delay buffer
            reverb_sample = self._reverb_buffer[i % len(self._reverb_buffer)]

            # Mix with input
            output[i] = audio[i] + reverb_sample * self.params.reverb_wet

            # Update buffer with damped feedback
            feedback = (audio[i] + reverb_sample * 0.5) * self.params.reverb_damping
            self._reverb_buffer[i % len(self._reverb_buffer)] = feedback

        return output

    def _apply_delay(self, audio: np.ndarray) -> np.ndarray:
        """Apply delay/echo effect.

        Args:
            audio: Input audio

        Returns:
            Audio with delay
        """
        # Initialize delay buffer
        delay_samples = int(self.sample_rate * self.params.delay_time)
        if self._delay_buffer is None or len(self._delay_buffer) != delay_samples:
            self._delay_buffer = np.zeros(delay_samples, dtype=np.float32)

        output = np.zeros_like(audio)

        for i in range(len(audio)):
            # Read delayed sample
            delayed = self._delay_buffer[i % len(self._delay_buffer)]

            # Mix dry and wet
            output[i] = audio[i] * (1 - self.params.delay_mix) + delayed * self.params.delay_mix

            # Write to buffer with feedback
            self._delay_buffer[i % len(self._delay_buffer)] = (
                audio[i] + delayed * self.params.delay_feedback
            )

        return output

    def _apply_chorus(self, audio: np.ndarray) -> np.ndarray:
        """Apply chorus effect.

        Args:
            audio: Input audio

        Returns:
            Audio with chorus
        """
        output = audio.copy()

        # LFO (Low Frequency Oscillator) for modulation
        samples_per_phase = self.sample_rate / self.params.chorus_rate
        phase_increment = 2.0 * np.pi / samples_per_phase

        for i in range(len(audio)):
            # Calculate delay based on LFO
            lfo = np.sin(self._chorus_phase) * self.params.chorus_depth * self.sample_rate
            delay_samples = int(lfo + self.sample_rate * 0.02)  # Base delay 20ms

            # Read delayed sample
            read_pos = i - delay_samples
            if read_pos >= 0:
                output[i] = (
                    audio[i] * (1 - self.params.chorus_mix)
                    + audio[read_pos] * self.params.chorus_mix
                )

            # Update LFO phase
            self._chorus_phase += phase_increment
            if self._chorus_phase >= 2.0 * np.pi:
                self._chorus_phase -= 2.0 * np.pi

        return output

    def _apply_distortion(self, audio: np.ndarray) -> np.ndarray:
        """Apply distortion effect.

        Args:
            audio: Input audio

        Returns:
            Distorted audio
        """
        # Soft clipping distortion
        gained = audio * self.params.distortion_gain

        # Hyperbolic tangent soft clipping
        distorted = np.tanh(gained)

        # Mix with dry signal
        output = (
            audio * (1 - self.params.distortion_mix)
            + distorted * self.params.distortion_mix
        )

        return output

    def _apply_noise_gate(self, audio: np.ndarray) -> np.ndarray:
        """Apply noise gate to remove low-level noise.

        Args:
            audio: Input audio

        Returns:
            Gated audio
        """
        # Convert threshold from dB to linear
        threshold = 10 ** (self.params.noise_gate_threshold / 20.0)

        # Envelope follower parameters
        attack_time = 0.005  # 5ms
        release_time = 0.1  # 100ms
        attack_coef = np.exp(-1.0 / (self.sample_rate * attack_time))
        release_coef = np.exp(-1.0 / (self.sample_rate * release_time))

        output = np.zeros_like(audio)

        for i in range(len(audio)):
            # Calculate envelope
            abs_sample = abs(audio[i])
            if abs_sample > self._gate_envelope:
                self._gate_envelope = (
                    attack_coef * self._gate_envelope + (1 - attack_coef) * abs_sample
                )
            else:
                self._gate_envelope = (
                    release_coef * self._gate_envelope + (1 - release_coef) * abs_sample
                )

            # Apply gate
            if self._gate_envelope > threshold:
                gain = 1.0
            else:
                gain = 1.0 / self.params.noise_gate_ratio

            output[i] = audio[i] * gain

        return output

    def _apply_equalizer(self, audio: np.ndarray) -> np.ndarray:
        """Apply 3-band equalizer.

        Args:
            audio: Input audio

        Returns:
            Equalized audio
        """
        try:
            from scipy import signal

            # Design filters
            nyquist = self.sample_rate / 2

            # Low shelf (< 500 Hz)
            if abs(self.params.eq_low_gain) > 0.1:
                b, a = signal.iirfilter(
                    2,
                    500 / nyquist,
                    btype="low",
                    ftype="butter",
                )
                audio = signal.lfilter(b, a, audio) * (
                    10 ** (self.params.eq_low_gain / 20.0)
                )

            # Mid peaking (500 Hz - 4 kHz)
            if abs(self.params.eq_mid_gain) > 0.1:
                b, a = signal.iirfilter(
                    2,
                    [500 / nyquist, 4000 / nyquist],
                    btype="band",
                    ftype="butter",
                )
                audio = signal.lfilter(b, a, audio) * (
                    10 ** (self.params.eq_mid_gain / 20.0)
                )

            # High shelf (> 4 kHz)
            if abs(self.params.eq_high_gain) > 0.1:
                b, a = signal.iirfilter(
                    2,
                    4000 / nyquist,
                    btype="high",
                    ftype="butter",
                )
                audio = signal.lfilter(b, a, audio) * (
                    10 ** (self.params.eq_high_gain / 20.0)
                )

            return audio.astype(np.float32)

        except Exception as e:
            logger.warning(f"EQ failed: {e}")
            return audio

    def _reset_buffers(self) -> None:
        """Reset internal effect buffers."""
        self._delay_buffer = None
        self._reverb_buffer = None
        self._chorus_phase = 0.0
        self._gate_envelope = 0.0

    def get_parameters(self) -> dict:
        """Get current effect parameters as dictionary.

        Returns:
            Parameters dictionary
        """
        return self.params.to_dict()
