"""Melody parsing for singing synthesis.

Parses MIDI files, ABC notation, and simple melody notation into pitch
contours suitable for singing voice synthesis with DiffSinger.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class Note:
    """Represents a single musical note.

    Attributes:
        pitch: MIDI note number (21-108, where 60 is middle C).
        start_time: Note start time in seconds.
        duration: Note duration in seconds.
        velocity: Note velocity/loudness (0-127), default 64.
    """

    pitch: int
    start_time: float
    duration: float
    velocity: int = 64


@dataclass
class PitchContour:
    """Pitch contour representation for singing synthesis.

    Attributes:
        notes: List of Note objects.
        tempo: Tempo in beats per minute (BPM).
        total_duration: Total duration of the melody in seconds.
    """

    notes: list[Note]
    tempo: float
    total_duration: float

    def to_f0_contour(self, sample_rate: int = 100) -> tuple[np.ndarray, np.ndarray]:
        """Convert note sequence to continuous F0 (pitch) contour.

        Args:
            sample_rate: Samples per second for the contour (default 100Hz).

        Returns:
            Tuple of (times, f0_values) where:
            - times: Array of time points in seconds
            - f0_values: Array of fundamental frequency values in Hz
        """
        if not self.notes:
            return np.array([]), np.array([])

        # Create time grid
        num_samples = int(self.total_duration * sample_rate)
        times = np.linspace(0, self.total_duration, num_samples)
        f0_values = np.zeros(num_samples)

        # Fill in pitch values from notes
        for note in self.notes:
            start_idx = int(note.start_time * sample_rate)
            end_idx = int((note.start_time + note.duration) * sample_rate)

            if start_idx < num_samples and end_idx > 0:
                start_idx = max(0, start_idx)
                end_idx = min(num_samples, end_idx)

                # Convert MIDI note to frequency (Hz)
                f0 = self._midi_to_hz(note.pitch)
                f0_values[start_idx:end_idx] = f0

        return times, f0_values

    @staticmethod
    def _midi_to_hz(midi_note: int) -> float:
        """Convert MIDI note number to frequency in Hz.

        Args:
            midi_note: MIDI note number (0-127).

        Returns:
            Frequency in Hz.
        """
        return 440.0 * (2.0 ** ((midi_note - 69) / 12.0))


class MelodyParser:
    """Parse MIDI files and melody notation into pitch contours.

    Supports:
    - MIDI file parsing via pretty_midi
    - ABC notation parsing
    - Simple scientific notation (C4 D4 E4)
    - Auto-generation from text prosody
    """

    def __init__(self) -> None:
        """Initialize the melody parser with lazy library loading."""
        self._pretty_midi: object | None = None
        logger.debug("MelodyParser created")

    def _ensure_pretty_midi(self) -> None:
        """Load the pretty_midi package on first call.

        Raises:
            RuntimeError: If pretty_midi package is not installed.
        """
        if self._pretty_midi is not None:
            return

        logger.info("Loading pretty_midi for MIDI parsing")

        try:
            import pretty_midi

            self._pretty_midi = pretty_midi
            logger.info("pretty_midi loaded successfully")

        except ImportError as exc:
            raise RuntimeError(
                "pretty_midi package not installed. Run: pip install pretty_midi"
            ) from exc
        except Exception as exc:
            logger.error("Failed to load pretty_midi: %s", exc)
            raise RuntimeError(f"Cannot load pretty_midi: {exc}") from exc

    def parse_midi(
        self, midi_path: Path, tempo_override: Optional[float] = None
    ) -> PitchContour:
        """Parse MIDI file to pitch contour.

        Args:
            midi_path: Path to MIDI file.
            tempo_override: Optional tempo override in BPM.

        Returns:
            PitchContour object with note sequence.

        Raises:
            FileNotFoundError: If MIDI file doesn't exist.
            RuntimeError: If MIDI parsing fails.
        """
        self._ensure_pretty_midi()

        if not midi_path.exists():
            raise FileNotFoundError(f"MIDI file not found: {midi_path}")

        logger.info("Parsing MIDI file: %s", midi_path.name)

        try:
            midi_data = self._pretty_midi.PrettyMIDI(str(midi_path))

            # Extract notes from all instruments
            all_notes: list[Note] = []
            for instrument in midi_data.instruments:
                for note in instrument.notes:
                    all_notes.append(
                        Note(
                            pitch=note.pitch,
                            start_time=note.start,
                            duration=note.end - note.start,
                            velocity=note.velocity,
                        )
                    )

            # Sort notes by start time
            all_notes.sort(key=lambda n: n.start_time)

            # Get tempo (BPM)
            tempo = tempo_override if tempo_override else 120.0
            if not tempo_override and midi_data.get_tempo_changes()[1].size > 0:
                tempo = float(midi_data.get_tempo_changes()[1][0])

            # Calculate total duration
            total_duration = midi_data.get_end_time()

            logger.info(
                "MIDI parsed: %d notes, tempo=%.1f BPM, duration=%.2fs",
                len(all_notes),
                tempo,
                total_duration,
            )

            return PitchContour(
                notes=all_notes, tempo=tempo, total_duration=total_duration
            )

        except Exception as exc:
            logger.error("Failed to parse MIDI file: %s", exc)
            raise RuntimeError(f"MIDI parsing failed: {exc}") from exc

    def parse_abc_notation(
        self, notation: str, tempo: float = 120.0
    ) -> PitchContour:
        """Parse ABC notation to pitch contour.

        Simplified ABC notation support for basic melodies.
        Example: "C4:1.0 D4:0.5 E4:0.5 | F4:1.0 G4:2.0"

        Args:
            notation: ABC notation string.
            tempo: Tempo in BPM.

        Returns:
            PitchContour object with note sequence.

        Raises:
            ValueError: If notation format is invalid.
        """
        logger.info("Parsing ABC notation: %s", notation[:50])

        # Simple notation format: "NOTE:DURATION NOTE:DURATION"
        # Note format: C4, D#4, Bb3, etc.
        # Duration in beats (quarter notes)

        notes: list[Note] = []
        current_time = 0.0
        beat_duration = 60.0 / tempo  # Duration of one beat in seconds

        # Remove bar lines and split into tokens
        tokens = notation.replace("|", " ").split()

        for token in tokens:
            if not token.strip():
                continue

            try:
                # Parse "NOTE:DURATION" format
                if ":" in token:
                    note_str, duration_str = token.split(":", 1)
                    duration_beats = float(duration_str)
                else:
                    # Default to quarter note if no duration specified
                    note_str = token
                    duration_beats = 1.0

                # Parse note name to MIDI number
                midi_note = self._note_name_to_midi(note_str)

                # Create note
                note_duration = duration_beats * beat_duration
                notes.append(
                    Note(
                        pitch=midi_note,
                        start_time=current_time,
                        duration=note_duration,
                        velocity=64,
                    )
                )

                current_time += note_duration

            except (ValueError, IndexError) as exc:
                logger.warning("Skipping invalid token '%s': %s", token, exc)
                continue

        total_duration = current_time

        logger.info(
            "ABC notation parsed: %d notes, tempo=%.1f BPM, duration=%.2fs",
            len(notes),
            tempo,
            total_duration,
        )

        return PitchContour(
            notes=notes, tempo=tempo, total_duration=total_duration
        )

    def parse_simple_notation(
        self, notation: str, tempo: float = 120.0
    ) -> PitchContour:
        """Parse simple scientific notation to pitch contour.

        Format: Space-separated note names with optional durations.
        Example: "C4 D4 E4 F4" or "C4:1.0 D4:0.5 E4:0.5"

        Args:
            notation: Simple notation string.
            tempo: Tempo in BPM.

        Returns:
            PitchContour object with note sequence.

        Raises:
            ValueError: If notation format is invalid.
        """
        # This is essentially the same as ABC notation for our purposes
        return self.parse_abc_notation(notation, tempo)

    @staticmethod
    def _note_name_to_midi(note_name: str) -> int:
        """Convert note name to MIDI note number.

        Supports: C4, C#4, Db4, etc.
        Middle C (C4) = MIDI 60.

        Args:
            note_name: Note name string (e.g. "C4", "D#5", "Bb3").

        Returns:
            MIDI note number (21-108).

        Raises:
            ValueError: If note name format is invalid.
        """
        note_name = note_name.strip().upper()

        # Extract note letter, accidental, and octave
        match = re.match(r"([A-G])([#B]?)(\d)", note_name)
        if not match:
            raise ValueError(f"Invalid note name: {note_name}")

        note_letter, accidental, octave_str = match.groups()
        octave = int(octave_str)

        # Base MIDI numbers for C octave (C0 = 12)
        note_base = {
            "C": 0,
            "D": 2,
            "E": 4,
            "F": 5,
            "G": 7,
            "A": 9,
            "B": 11,
        }

        midi_note = 12 * (octave + 1) + note_base[note_letter]

        # Apply accidental
        if accidental == "#":
            midi_note += 1
        elif accidental == "B":
            midi_note -= 1

        # Clamp to valid MIDI range
        midi_note = max(21, min(108, midi_note))

        return midi_note

    def generate_simple_melody(
        self, text: str, tempo: float = 120.0, base_pitch: int = 60
    ) -> PitchContour:
        """Generate simple melody from text prosody.

        Creates a basic melodic contour based on text structure.
        Uses sentence and word boundaries to create pitch variations.

        Args:
            text: Text to generate melody for.
            tempo: Tempo in BPM.
            base_pitch: Base MIDI pitch (default 60 = middle C).

        Returns:
            PitchContour object with auto-generated melody.
        """
        logger.info("Auto-generating melody for text: %s", text[:50])

        # Split text into words
        words = text.strip().split()
        if not words:
            return PitchContour(notes=[], tempo=tempo, total_duration=0.0)

        notes: list[Note] = []
        current_time = 0.0
        beat_duration = 60.0 / tempo

        # Generate pitch contour based on text structure
        # Use simple melodic pattern: rising on questions, falling on statements
        is_question = text.strip().endswith("?")

        for i, word in enumerate(words):
            # Calculate pitch variation based on position
            position_ratio = i / len(words)

            if is_question:
                # Rising melody for questions
                pitch_offset = int(7 * position_ratio)  # Up to +7 semitones
            else:
                # Falling melody for statements
                pitch_offset = int(5 * (1 - position_ratio))  # Down from +5

            pitch = base_pitch + pitch_offset

            # Duration based on word length
            syllable_estimate = max(1, len(word) // 3)
            duration = syllable_estimate * beat_duration

            notes.append(
                Note(
                    pitch=pitch,
                    start_time=current_time,
                    duration=duration,
                    velocity=64,
                )
            )

            current_time += duration

        total_duration = current_time

        logger.info(
            "Auto-generated melody: %d notes, tempo=%.1f BPM, duration=%.2fs",
            len(notes),
            tempo,
            total_duration,
        )

        return PitchContour(
            notes=notes, tempo=tempo, total_duration=total_duration
        )

    def align_melody_to_text(
        self,
        contour: PitchContour,
        text: str,
        phoneme_count: int,
    ) -> list[tuple[int, float]]:
        """Align melody notes to phoneme sequence.

        Distributes notes across phonemes based on note durations.

        Args:
            contour: Pitch contour with note sequence.
            text: Original text.
            phoneme_count: Number of phonemes in text.

        Returns:
            List of (pitch, duration) tuples for each phoneme.
        """
        if not contour.notes or phoneme_count == 0:
            return []

        logger.info(
            "Aligning %d notes to %d phonemes", len(contour.notes), phoneme_count
        )

        # Simple alignment: distribute phonemes evenly across notes
        phonemes_per_note = phoneme_count / len(contour.notes)
        alignments: list[tuple[int, float]] = []

        phoneme_idx = 0
        for note in contour.notes:
            # Calculate how many phonemes this note should cover
            phonemes_in_note = max(1, int(phonemes_per_note))

            # Distribute note duration across its phonemes
            phoneme_duration = note.duration / phonemes_in_note

            for _ in range(phonemes_in_note):
                if phoneme_idx >= phoneme_count:
                    break
                alignments.append((note.pitch, phoneme_duration))
                phoneme_idx += 1

        # Handle any remaining phonemes
        if phoneme_idx < phoneme_count and contour.notes:
            last_note = contour.notes[-1]
            remaining = phoneme_count - phoneme_idx
            phoneme_duration = last_note.duration / max(1, remaining)

            for _ in range(remaining):
                alignments.append((last_note.pitch, phoneme_duration))

        logger.info("Alignment complete: %d phoneme-note pairs", len(alignments))

        return alignments
