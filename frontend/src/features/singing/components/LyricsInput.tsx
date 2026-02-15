/**
 * Lyrics Input Component
 *
 * Multi-line editor with character counter and examples
 */

import React from 'react';
import { Card, Textarea, Button } from '@/components/ui';
import { EXAMPLE_LYRICS, SINGING_HELP_TEXT } from '@/types/singing.types';

interface LyricsInputProps {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}

const MAX_CHARS = 2000;

export const LyricsInput: React.FC<LyricsInputProps> = ({ value, onChange, disabled }) => {
  const charCount = value.length;
  const isOverLimit = charCount > MAX_CHARS;

  const handleExampleClick = (exampleKey: string) => {
    const lyrics = EXAMPLE_LYRICS[exampleKey as keyof typeof EXAMPLE_LYRICS];
    onChange(lyrics);
  };

  return (
    <Card className="lyrics-input">
      <div className="lyrics-input__header">
        <h3>Step 1: Enter Lyrics</h3>
        <span className={`lyrics-input__counter ${isOverLimit ? 'lyrics-input__counter--error' : ''}`}>
          {charCount} / {MAX_CHARS}
        </span>
      </div>

      <p className="lyrics-input__help">{SINGING_HELP_TEXT.lyrics}</p>

      <Textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Enter the lyrics you want to synthesize...&#10;&#10;Example:&#10;Twinkle, twinkle, little star&#10;How I wonder what you are"
        rows={8}
        disabled={disabled}
        className="lyrics-input__textarea"
      />

      <div className="lyrics-input__examples">
        <span className="lyrics-input__examples-label">Examples:</span>
        {Object.keys(EXAMPLE_LYRICS).map((key) => (
          <Button
            key={key}
            variant="secondary"
            size="sm"
            onClick={() => handleExampleClick(key)}
            disabled={disabled}
          >
            {key}
          </Button>
        ))}
      </div>
    </Card>
  );
};
