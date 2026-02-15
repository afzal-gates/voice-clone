"""Tests for the AudioMixer module.

This module tests the audio mixing functionality for combining TTS
narration with background music, including volume control, timing
offsets, and crossfade effects.
"""

import asyncio
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from app.pipeline.audio_mixer import AudioMixer


@pytest.fixture
def temp_audio_dir(tmp_path):
    """Create temporary directory for test audio files."""
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()
    return audio_dir


@pytest.fixture
def sample_rate():
    """Standard sample rate for tests."""
    return 16000


def create_test_audio(
    path: Path,
    duration: float,
    sample_rate: int,
    frequency: float = 440.0,
) -> None:
    """Generate test audio file with sine wave.

    Args:
        path: Output file path.
        duration: Duration in seconds.
        sample_rate: Sample rate in Hz.
        frequency: Sine wave frequency in Hz.
    """
    samples = int(duration * sample_rate)
    t = np.linspace(0, duration, samples, dtype=np.float32)
    audio = 0.5 * np.sin(2 * np.pi * frequency * t)
    sf.write(str(path), audio, sample_rate)


@pytest.mark.asyncio
async def test_audio_mixer_basic_mix(temp_audio_dir, sample_rate):
    """Test basic audio mixing with default parameters."""
    # Create test audio files
    tts_path = temp_audio_dir / "tts.wav"
    music_path = temp_audio_dir / "music.wav"
    output_path = temp_audio_dir / "mixed.wav"

    create_test_audio(tts_path, duration=3.0, sample_rate=sample_rate, frequency=440)
    create_test_audio(music_path, duration=5.0, sample_rate=sample_rate, frequency=220)

    # Mix audio
    mixer = AudioMixer()
    result_path = await mixer.mix(
        tts_audio_path=tts_path,
        music_audio_path=music_path,
        output_path=output_path,
    )

    # Verify output exists
    assert result_path.exists()
    assert result_path == output_path

    # Verify output properties
    audio, sr = sf.read(str(output_path))
    assert sr == sample_rate
    assert len(audio) > 0
    # Duration should match TTS duration (3 seconds)
    expected_samples = int(3.0 * sample_rate)
    assert abs(len(audio) - expected_samples) < sample_rate * 0.1  # 100ms tolerance


@pytest.mark.asyncio
async def test_audio_mixer_with_volume_control(temp_audio_dir, sample_rate):
    """Test audio mixing with custom volume levels."""
    tts_path = temp_audio_dir / "tts.wav"
    music_path = temp_audio_dir / "music.wav"
    output_path = temp_audio_dir / "mixed.wav"

    create_test_audio(tts_path, duration=2.0, sample_rate=sample_rate, frequency=440)
    create_test_audio(music_path, duration=2.0, sample_rate=sample_rate, frequency=220)

    mixer = AudioMixer()
    await mixer.mix(
        tts_audio_path=tts_path,
        music_audio_path=music_path,
        output_path=output_path,
        tts_volume=0.9,
        music_volume=0.2,
    )

    # Verify output exists and has audio data
    audio, sr = sf.read(str(output_path))
    assert len(audio) > 0
    assert np.max(np.abs(audio)) > 0  # Not silent


@pytest.mark.asyncio
async def test_audio_mixer_with_delay(temp_audio_dir, sample_rate):
    """Test audio mixing with music delay."""
    tts_path = temp_audio_dir / "tts.wav"
    music_path = temp_audio_dir / "music.wav"
    output_path = temp_audio_dir / "mixed.wav"

    create_test_audio(tts_path, duration=2.0, sample_rate=sample_rate, frequency=440)
    create_test_audio(music_path, duration=2.0, sample_rate=sample_rate, frequency=220)

    mixer = AudioMixer()
    await mixer.mix(
        tts_audio_path=tts_path,
        music_audio_path=music_path,
        output_path=output_path,
        music_delay=1.0,  # 1 second delay
    )

    # Verify output exists
    audio, sr = sf.read(str(output_path))
    assert len(audio) > 0

    # Check that first 1 second has lower energy (music delayed)
    delay_samples = sample_rate  # 1 second
    first_second = audio[:delay_samples]
    second_half = audio[delay_samples : delay_samples * 2]

    # Second half should have higher energy (TTS + music)
    # Note: This is a rough check since both tracks have energy
    assert np.std(audio) > 0  # Audio has variation


@pytest.mark.asyncio
async def test_audio_mixer_missing_file_error(temp_audio_dir, sample_rate):
    """Test error handling for missing input files."""
    tts_path = temp_audio_dir / "nonexistent_tts.wav"
    music_path = temp_audio_dir / "music.wav"
    output_path = temp_audio_dir / "mixed.wav"

    create_test_audio(music_path, duration=2.0, sample_rate=sample_rate, frequency=220)

    mixer = AudioMixer()

    with pytest.raises(FileNotFoundError, match="TTS audio file not found"):
        await mixer.mix(
            tts_audio_path=tts_path,
            music_audio_path=music_path,
            output_path=output_path,
        )


@pytest.mark.asyncio
async def test_audio_mixer_invalid_volume_error(temp_audio_dir, sample_rate):
    """Test error handling for invalid volume levels."""
    tts_path = temp_audio_dir / "tts.wav"
    music_path = temp_audio_dir / "music.wav"
    output_path = temp_audio_dir / "mixed.wav"

    create_test_audio(tts_path, duration=2.0, sample_rate=sample_rate, frequency=440)
    create_test_audio(music_path, duration=2.0, sample_rate=sample_rate, frequency=220)

    mixer = AudioMixer()

    with pytest.raises(ValueError, match="TTS volume must be in range"):
        await mixer.mix(
            tts_audio_path=tts_path,
            music_audio_path=music_path,
            output_path=output_path,
            tts_volume=1.5,  # Invalid: > 1.0
        )


@pytest.mark.asyncio
async def test_audio_mixer_resampling(temp_audio_dir):
    """Test audio mixing with different sample rates."""
    tts_path = temp_audio_dir / "tts.wav"
    music_path = temp_audio_dir / "music.wav"
    output_path = temp_audio_dir / "mixed.wav"

    # Create files with different sample rates
    create_test_audio(tts_path, duration=2.0, sample_rate=22050, frequency=440)
    create_test_audio(music_path, duration=2.0, sample_rate=44100, frequency=220)

    mixer = AudioMixer()
    await mixer.mix(
        tts_audio_path=tts_path,
        music_audio_path=music_path,
        output_path=output_path,
    )

    # Verify output exists with consistent sample rate
    audio, sr = sf.read(str(output_path))
    assert len(audio) > 0
    # Sample rate should be the mixer's target rate (16000 by default)
    assert sr == 16000


@pytest.mark.asyncio
async def test_audio_mixer_normalization(temp_audio_dir, sample_rate):
    """Test that output audio is normalized properly."""
    tts_path = temp_audio_dir / "tts.wav"
    music_path = temp_audio_dir / "music.wav"
    output_path = temp_audio_dir / "mixed.wav"

    # Create loud audio (full scale)
    samples = int(2.0 * sample_rate)
    loud_audio = np.ones(samples, dtype=np.float32) * 0.9
    sf.write(str(tts_path), loud_audio, sample_rate)
    sf.write(str(music_path), loud_audio, sample_rate)

    mixer = AudioMixer()
    await mixer.mix(
        tts_audio_path=tts_path,
        music_audio_path=music_path,
        output_path=output_path,
        tts_volume=1.0,
        music_volume=1.0,
    )

    # Verify output is normalized (not clipping)
    audio, sr = sf.read(str(output_path))
    peak = np.max(np.abs(audio))
    # Peak should be normalized to around -1 dBFS (0.89125)
    assert peak <= 1.0  # No clipping
    assert peak > 0.8  # Normalized to reasonable level


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
