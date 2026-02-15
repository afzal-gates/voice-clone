"""MIDI export engine for melody generation.

Provides MIDI file generation from pitch contours with tempo, key signature,
and instrument configuration support.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import pretty_midi

from app.pipeline.melody_parser import PitchContour

logger = logging.getLogger(__name__)


class MIDIExporter:
    """MIDI file export engine.

    Converts PitchContour objects to standard MIDI files with configurable
    tempo, key signature, and instrument settings.

    Typical usage::

        exporter = MIDIExporter()
        exporter.export_midi(
            pitch_contour=melody,
            output_path=Path("melody.mid"),
            tempo=120,
            key_signature="C",
            instrument_program=0  # Acoustic Grand Piano
        )
    """

    # MIDI instrument programs (General MIDI standard)
    INSTRUMENTS = {
        "piano": 0,
        "guitar": 24,
        "violin": 40,
        "flute": 73,
        "synth": 80,
        "voice": 52,  # Choir Aahs
        "strings": 48,  # String Ensemble
        "organ": 19,
        "trumpet": 56,
        "saxophone": 65,
    }

    def __init__(self) -> None:
        """Initialize the MIDI exporter."""
        logger.debug("MIDIExporter created")

    def export_midi(
        self,
        pitch_contour: PitchContour,
        output_path: Path,
        tempo: int = 120,
        key_signature: str = "C",
        instrument_program: int = 0,
        instrument_name: Optional[str] = None,
    ) -> Path:
        """Export pitch contour to MIDI file.

        Converts a PitchContour object containing musical notes to a standard
        MIDI file format with specified tempo and key signature.

        Args:
            pitch_contour: PitchContour object with note sequence.
            output_path: Path where MIDI file will be saved.
            tempo: Tempo in BPM (beats per minute). Default: 120.
            key_signature: Key signature (C, D, E, F, G, A, B with optional
                          # or b modifier). Default: C.
            instrument_program: MIDI instrument program number (0-127).
                               Default: 0 (Acoustic Grand Piano).
            instrument_name: Optional instrument name for metadata.

        Returns:
            Path to the saved MIDI file.

        Raises:
            ValueError: If pitch_contour is empty or invalid.
            RuntimeError: If MIDI file generation fails.

        Example:
            >>> contour = melody_parser.parse_simple_notation("C D E F G", 120)
            >>> exporter.export_midi(contour, Path("melody.mid"), tempo=120)
            Path('melody.mid')
        """
        if not pitch_contour or len(pitch_contour.notes) == 0:
            raise ValueError("Cannot export empty pitch contour")

        logger.info(
            "Exporting MIDI: %d notes, tempo=%d BPM, key=%s",
            len(pitch_contour.notes),
            tempo,
            key_signature,
        )

        try:
            # Create MIDI object with specified tempo
            midi_data = pretty_midi.PrettyMIDI(initial_tempo=tempo)

            # Create instrument track
            instrument = pretty_midi.Instrument(
                program=instrument_program,
                name=instrument_name or self._get_instrument_name(instrument_program),
            )

            # Convert pitch contour notes to MIDI notes
            for note in pitch_contour.notes:
                midi_note = pretty_midi.Note(
                    velocity=100,  # Medium-loud velocity
                    pitch=int(note.pitch),  # MIDI pitch (0-127)
                    start=note.start_time,
                    end=note.start_time + note.duration,
                )
                instrument.notes.append(midi_note)

            # Add key signature metadata
            self._add_key_signature(midi_data, key_signature)

            # Add instrument track to MIDI
            midi_data.instruments.append(instrument)

            # Save MIDI file
            output_path.parent.mkdir(parents=True, exist_ok=True)
            midi_data.write(str(output_path))

            file_size = output_path.stat().st_size
            logger.info(
                "MIDI exported: %s (%d bytes, %.2fs)",
                output_path.name,
                file_size,
                pitch_contour.total_duration,
            )

            return output_path

        except Exception as exc:
            logger.error("MIDI export failed: %s", exc)
            raise RuntimeError(f"Cannot export MIDI file: {exc}") from exc

    def export_multi_track(
        self,
        pitch_contours: list[PitchContour],
        output_path: Path,
        tempo: int = 120,
        key_signature: str = "C",
        instrument_programs: Optional[list[int]] = None,
        track_names: Optional[list[str]] = None,
    ) -> Path:
        """Export multiple pitch contours as multi-track MIDI.

        Creates a MIDI file with multiple instrument tracks, useful for
        exporting harmonies, accompaniment, or multi-part arrangements.

        Args:
            pitch_contours: List of PitchContour objects (one per track).
            output_path: Path where MIDI file will be saved.
            tempo: Tempo in BPM. Default: 120.
            key_signature: Key signature. Default: C.
            instrument_programs: Optional list of MIDI program numbers (one per track).
                                If None, defaults to piano for all tracks.
            track_names: Optional list of track names for metadata.

        Returns:
            Path to the saved MIDI file.

        Raises:
            ValueError: If pitch_contours is empty or length mismatch.
        """
        if not pitch_contours or len(pitch_contours) == 0:
            raise ValueError("Cannot export empty track list")

        num_tracks = len(pitch_contours)
        logger.info("Exporting multi-track MIDI: %d tracks", num_tracks)

        # Prepare instrument programs (default to piano)
        if instrument_programs is None:
            instrument_programs = [0] * num_tracks
        elif len(instrument_programs) != num_tracks:
            raise ValueError(
                f"Instrument programs length ({len(instrument_programs)}) "
                f"must match tracks ({num_tracks})"
            )

        # Prepare track names
        if track_names is None:
            track_names = [f"Track {i+1}" for i in range(num_tracks)]
        elif len(track_names) != num_tracks:
            raise ValueError(
                f"Track names length ({len(track_names)}) "
                f"must match tracks ({num_tracks})"
            )

        # Create MIDI with first track, then add remaining tracks
        midi_data = pretty_midi.PrettyMIDI(initial_tempo=tempo)

        for i, contour in enumerate(pitch_contours):
            if len(contour.notes) == 0:
                logger.warning("Skipping empty track %d", i)
                continue

            instrument = pretty_midi.Instrument(
                program=instrument_programs[i],
                name=track_names[i],
            )

            for note in contour.notes:
                midi_note = pretty_midi.Note(
                    velocity=100,
                    pitch=int(note.pitch),
                    start=note.start_time,
                    end=note.start_time + note.duration,
                )
                instrument.notes.append(midi_note)

            midi_data.instruments.append(instrument)

        # Add key signature
        self._add_key_signature(midi_data, key_signature)

        # Save MIDI file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        midi_data.write(str(output_path))

        logger.info("Multi-track MIDI exported: %s", output_path.name)
        return output_path

    def _add_key_signature(self, midi_data: pretty_midi.PrettyMIDI, key_signature: str) -> None:
        """Add key signature metadata to MIDI.

        Args:
            midi_data: PrettyMIDI object to modify.
            key_signature: Key signature string (e.g., "C", "G", "Bb", "F#").
        """
        # Parse key signature
        key_map = {
            "C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4,
            "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9,
            "A#": 10, "Bb": 10, "B": 11,
        }

        key_number = key_map.get(key_signature, 0)

        # Add key signature event (at time 0)
        key_event = pretty_midi.KeySignature(key_number=key_number, time=0)
        midi_data.key_signature_changes.append(key_event)

    def _get_instrument_name(self, program: int) -> str:
        """Get instrument name from MIDI program number.

        Args:
            program: MIDI program number (0-127).

        Returns:
            Instrument name string.
        """
        # Reverse lookup in instruments dict
        for name, prog in self.INSTRUMENTS.items():
            if prog == program:
                return name.capitalize()

        # General MIDI instrument names for common programs
        gm_names = {
            0: "Acoustic Grand Piano",
            24: "Acoustic Guitar",
            40: "Violin",
            52: "Choir Aahs",
            73: "Flute",
            80: "Lead Synth",
        }

        return gm_names.get(program, f"Instrument {program}")
