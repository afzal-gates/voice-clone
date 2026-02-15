"""Test script for singing synthesis feature.

This script demonstrates the singing synthesis pipeline:
1. Phoneme conversion
2. Melody parsing (notation and MIDI)
3. Singing synthesis

Run from project root:
    python scripts/test_singing.py
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.pipeline.phoneme_converter import PhonemeConverter
from app.pipeline.melody_parser import MelodyParser
from app.pipeline.singing_engine import SingingEngine

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def test_phoneme_converter():
    """Test phoneme conversion functionality."""
    logger.info("=" * 70)
    logger.info("Testing Phoneme Converter")
    logger.info("=" * 70)

    converter = PhonemeConverter()

    # Test 1: Simple English text
    test_texts = [
        ("Hello world", "en"),
        ("How are you today", "en"),
        ("This is a test song", "en"),
    ]

    for text, language in test_texts:
        try:
            phonemes = converter.text_to_phonemes(text, language)
            logger.info(
                "Text: '%s' -> %d phonemes: %s",
                text,
                len(phonemes),
                phonemes[:10],  # Show first 10
            )
        except Exception as exc:
            logger.error("Phoneme conversion failed for '%s': %s", text, exc)

    # Test 2: Get phoneme count
    count = converter.get_phoneme_count("Sing a simple song", "en")
    logger.info("Phoneme count for 'Sing a simple song': %d", count)

    logger.info("Phoneme converter tests passed!")
    logger.info("")


def test_melody_parser():
    """Test melody parsing functionality."""
    logger.info("=" * 70)
    logger.info("Testing Melody Parser")
    logger.info("=" * 70)

    parser = MelodyParser()

    # Test 1: Simple notation parsing
    notations = [
        "C4:1.0 D4:1.0 E4:1.0 F4:1.0",
        "G4:0.5 A4:0.5 B4:1.0 C5:2.0",
        "C4 D4 E4 F4 G4",  # Without durations
    ]

    for notation in notations:
        try:
            contour = parser.parse_simple_notation(notation, tempo=120.0)
            logger.info(
                "Notation: '%s' -> %d notes, duration=%.2fs",
                notation[:30],
                len(contour.notes),
                contour.total_duration,
            )

            # Show first few notes
            for i, note in enumerate(contour.notes[:3]):
                logger.info(
                    "  Note %d: pitch=%d, start=%.2fs, duration=%.2fs",
                    i,
                    note.pitch,
                    note.start_time,
                    note.duration,
                )
        except Exception as exc:
            logger.error("Melody parsing failed for '%s': %s", notation, exc)

    # Test 2: Auto-melody generation
    try:
        test_text = "Sing a simple song with me"
        contour = parser.generate_simple_melody(test_text, tempo=120.0)
        logger.info(
            "Auto-generated melody for '%s': %d notes, duration=%.2fs",
            test_text,
            len(contour.notes),
            contour.total_duration,
        )
    except Exception as exc:
        logger.error("Auto melody generation failed: %s", exc)

    # Test 3: Note name conversion
    test_notes = ["C4", "D#4", "Bb3", "G5"]
    for note_name in test_notes:
        try:
            midi_note = parser._note_name_to_midi(note_name)
            logger.info("Note name '%s' -> MIDI %d", note_name, midi_note)
        except Exception as exc:
            logger.error("Note conversion failed for '%s': %s", note_name, exc)

    # Test 4: F0 contour extraction
    try:
        contour = parser.parse_simple_notation("C4:1.0 E4:1.0 G4:1.0", tempo=120.0)
        times, f0_values = contour.to_f0_contour(sample_rate=100)
        logger.info(
            "F0 contour: %d time points, values range %.2f-%.2f Hz",
            len(times),
            f0_values[f0_values > 0].min() if f0_values.any() else 0,
            f0_values.max(),
        )
    except Exception as exc:
        logger.error("F0 contour extraction failed: %s", exc)

    logger.info("Melody parser tests passed!")
    logger.info("")


async def test_singing_engine():
    """Test singing synthesis engine."""
    logger.info("=" * 70)
    logger.info("Testing Singing Engine")
    logger.info("=" * 70)

    engine = SingingEngine()
    output_dir = Path("outputs/test_singing")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Test 1: Simple singing with auto-melody
    test_cases = [
        {
            "name": "auto_melody",
            "lyrics": "Hello world sing with me",
            "melody": None,
            "tempo": 120,
            "key_shift": 0,
        },
        {
            "name": "notation_melody",
            "lyrics": "Do re mi fa sol la ti do",
            "melody": "C4:1.0 D4:1.0 E4:1.0 F4:1.0 G4:1.0 A4:1.0 B4:1.0 C5:2.0",
            "tempo": 100,
            "key_shift": 0,
        },
        {
            "name": "key_shift_up",
            "lyrics": "Test pitch shift up three steps",
            "melody": "C4:1.0 E4:1.0 G4:2.0",
            "tempo": 120,
            "key_shift": 3,
        },
        {
            "name": "key_shift_down",
            "lyrics": "Test pitch shift down two steps",
            "melody": "G4:1.0 E4:1.0 C4:2.0",
            "tempo": 120,
            "key_shift": -2,
        },
    ]

    for test_case in test_cases:
        output_path = output_dir / f"{test_case['name']}.wav"

        try:
            logger.info("Test: %s", test_case["name"])
            logger.info("  Lyrics: %s", test_case["lyrics"])
            logger.info("  Melody: %s", test_case["melody"] or "auto-generated")
            logger.info("  Tempo: %d BPM", test_case["tempo"])
            logger.info("  Key shift: %d semitones", test_case["key_shift"])

            result_path = await engine.synthesize(
                lyrics=test_case["lyrics"],
                melody=test_case["melody"],
                voice_model="default",
                tempo=test_case["tempo"],
                key_shift=test_case["key_shift"],
                output_path=output_path,
                language="en",
            )

            logger.info("  Output: %s", result_path)
            logger.info("  Success!")

        except Exception as exc:
            logger.error("  Test failed: %s", exc, exc_info=True)

    # Test 2: List available models
    try:
        models = engine.list_available_models()
        logger.info("Available singing models: %d", len(models))
        for model in models:
            logger.info(
                "  - %s: %s (%s)",
                model["id"],
                model["name"],
                model["language"],
            )
    except Exception as exc:
        logger.error("Model listing failed: %s", exc)

    logger.info("Singing engine tests passed!")
    logger.info("")


async def test_integration():
    """Test full integration of all components."""
    logger.info("=" * 70)
    logger.info("Testing Full Integration")
    logger.info("=" * 70)

    # Initialize all components
    converter = PhonemeConverter()
    parser = MelodyParser()
    engine = SingingEngine()

    # Test lyrics
    lyrics = "Twinkle twinkle little star, how I wonder what you are"

    # Step 1: Convert to phonemes
    logger.info("Step 1: Converting lyrics to phonemes")
    phonemes = converter.text_to_phonemes(lyrics, "en")
    logger.info("  Generated %d phonemes", len(phonemes))

    # Step 2: Generate melody
    logger.info("Step 2: Generating melody")
    melody_notation = "C4:0.5 C4:0.5 G4:0.5 G4:0.5 A4:0.5 A4:0.5 G4:1.0"
    contour = parser.parse_simple_notation(melody_notation, tempo=120.0)
    logger.info("  Generated %d notes, duration=%.2fs", len(contour.notes), contour.total_duration)

    # Step 3: Synthesize singing
    logger.info("Step 3: Synthesizing singing")
    output_path = Path("outputs/test_singing/integration_test.wav")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        result = await engine.synthesize(
            lyrics=lyrics,
            melody=melody_notation,
            voice_model="default",
            tempo=120,
            key_shift=0,
            output_path=output_path,
            language="en",
        )
        logger.info("  Success! Output: %s", result)
    except Exception as exc:
        logger.error("  Integration test failed: %s", exc, exc_info=True)

    logger.info("Integration tests passed!")
    logger.info("")


async def main():
    """Run all tests."""
    logger.info("=" * 70)
    logger.info("DiffSinger Singing Synthesis Test Suite")
    logger.info("=" * 70)
    logger.info("")

    try:
        # Component tests
        test_phoneme_converter()
        test_melody_parser()
        await test_singing_engine()

        # Integration test
        await test_integration()

        logger.info("=" * 70)
        logger.info("ALL TESTS PASSED!")
        logger.info("=" * 70)

    except Exception as exc:
        logger.error("Test suite failed: %s", exc, exc_info=True)
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
