"""Phoneme conversion for singing synthesis.

Converts text to phoneme sequences for use with DiffSinger and other
singing voice synthesis systems. Supports multiple languages through
different G2P backends.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class PhonemeConverter:
    """Multi-language text-to-phoneme converter.

    Supports:
    - English via g2p_en (primary)
    - Universal G2P via phonemizer (multilingual fallback)
    - Simple phonetic mapping for basic cases
    """

    def __init__(self) -> None:
        """Initialize the phoneme converter with lazy backend loading."""
        self._g2p_en: object | None = None
        self._phonemizer: object | None = None
        logger.debug("PhonemeConverter created")

    def _ensure_g2p_en(self) -> None:
        """Load the g2p_en package on first call.

        Raises:
            RuntimeError: If g2p_en package is not installed.
        """
        if self._g2p_en is not None:
            return

        logger.info("Loading g2p_en for English phoneme conversion")

        try:
            from g2p_en import G2p

            self._g2p_en = G2p()
            logger.info("g2p_en loaded successfully")

        except ImportError as exc:
            raise RuntimeError(
                "g2p-en package not installed. Run: pip install g2p-en"
            ) from exc
        except Exception as exc:
            logger.error("Failed to load g2p_en: %s", exc)
            raise RuntimeError(f"Cannot load g2p_en: {exc}") from exc

    def _ensure_phonemizer(self) -> None:
        """Load the phonemizer package on first call.

        Requires espeak-ng system library to be installed.

        Raises:
            RuntimeError: If phonemizer package or espeak-ng is not available.
        """
        if self._phonemizer is not None:
            return

        logger.info("Loading phonemizer for multilingual phoneme conversion")

        try:
            from phonemizer import phonemize
            from phonemizer.backend import EspeakBackend

            # Test that espeak backend is available
            backend = EspeakBackend("en-us")
            backend.version()

            self._phonemizer = phonemize
            logger.info("Phonemizer loaded successfully")

        except ImportError as exc:
            raise RuntimeError(
                "phonemizer package not installed. Run: pip install phonemizer"
            ) from exc
        except Exception as exc:
            logger.error("Failed to load phonemizer: %s", exc)
            raise RuntimeError(
                f"Cannot load phonemizer (espeak-ng required): {exc}"
            ) from exc

    def _convert_english(self, text: str) -> list[str]:
        """Convert English text to phonemes using g2p_en.

        Args:
            text: English text to convert.

        Returns:
            List of phoneme strings (ARPAbet format).
        """
        self._ensure_g2p_en()

        logger.debug("Converting English text to phonemes: %s", text[:50])

        phonemes = self._g2p_en(text)

        # Filter out punctuation and spaces
        phonemes = [p for p in phonemes if p.strip() and p.isalnum()]

        logger.debug("Generated %d phonemes", len(phonemes))

        return phonemes

    def _convert_universal(self, text: str, language: str) -> list[str]:
        """Convert text to phonemes using phonemizer.

        Args:
            text: Text to convert.
            language: Language code (e.g. 'en-us', 'zh', 'ja').

        Returns:
            List of phoneme strings (IPA format).
        """
        self._ensure_phonemizer()

        logger.debug(
            "Converting text to phonemes (lang=%s): %s", language, text[:50]
        )

        # Map common language codes to espeak language codes
        lang_map = {
            "en": "en-us",
            "zh": "cmn",
            "ja": "ja",
            "ko": "ko",
            "es": "es",
            "fr": "fr",
            "de": "de",
            "it": "it",
            "pt": "pt",
            "ru": "ru",
        }

        espeak_lang = lang_map.get(language.lower(), language)

        phonemes_str = self._phonemizer(
            text,
            language=espeak_lang,
            backend="espeak",
            strip=True,
            preserve_punctuation=False,
        )

        # Split into individual phonemes (IPA characters/sequences)
        phonemes = phonemes_str.split()

        logger.debug("Generated %d phonemes", len(phonemes))

        return phonemes

    def _simple_phonetic_mapping(self, text: str) -> list[str]:
        """Fallback simple phonetic mapping when no G2P backend is available.

        This is a very basic character-level mapping and should only be used
        as a last resort. It splits text into characters for singing synthesis.

        Args:
            text: Text to convert.

        Returns:
            List of characters as pseudo-phonemes.
        """
        logger.warning(
            "Using simple character mapping (no G2P backend available)"
        )

        # Remove punctuation and split into words, then characters
        words = text.strip().split()
        phonemes = []

        for word in words:
            # Add each character as a phoneme
            for char in word.lower():
                if char.isalnum():
                    phonemes.append(char)
            # Add word boundary marker
            if len(words) > 1:
                phonemes.append(" ")

        return phonemes

    def text_to_phonemes(
        self, text: str, language: str = "en"
    ) -> list[str]:
        """Convert text to phoneme sequence.

        Automatically selects the best available backend based on language
        and installed packages.

        Args:
            text: Text to convert to phonemes.
            language: Language code (e.g. 'en', 'zh', 'ja').

        Returns:
            List of phoneme strings suitable for singing synthesis.

        Raises:
            ValueError: If text is empty or invalid.
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        text = text.strip()

        logger.info(
            "Converting text to phonemes: %d chars, language=%s",
            len(text),
            language,
        )

        # Try English G2P first for English text
        if language.lower() in ["en", "english"]:
            try:
                return self._convert_english(text)
            except RuntimeError as exc:
                logger.warning(
                    "g2p_en not available, trying phonemizer: %s", exc
                )

        # Try universal phonemizer for any language
        try:
            return self._convert_universal(text, language)
        except RuntimeError as exc:
            logger.warning(
                "Phonemizer not available, using simple mapping: %s", exc
            )

        # Fallback to simple character mapping
        return self._simple_phonetic_mapping(text)

    def align_phonemes_with_timing(
        self,
        phonemes: list[str],
        durations: list[float],
    ) -> list[tuple[str, float]]:
        """Align phonemes with timing information.

        Args:
            phonemes: List of phoneme strings.
            durations: List of duration values in seconds for each phoneme.

        Returns:
            List of (phoneme, duration) tuples.

        Raises:
            ValueError: If phonemes and durations lists have different lengths.
        """
        if len(phonemes) != len(durations):
            raise ValueError(
                f"Phoneme count ({len(phonemes)}) must match duration count "
                f"({len(durations)})"
            )

        return list(zip(phonemes, durations))

    def get_phoneme_count(self, text: str, language: str = "en") -> int:
        """Get the number of phonemes in text without full conversion.

        Useful for estimating timing requirements.

        Args:
            text: Text to analyze.
            language: Language code.

        Returns:
            Estimated phoneme count.
        """
        phonemes = self.text_to_phonemes(text, language)
        return len(phonemes)
