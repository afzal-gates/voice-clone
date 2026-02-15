/**
 * TextInputCard Component
 *
 * Text input area for TTS generation
 */

import { Textarea, Button, Card } from '@/components/ui';

interface TextInputCardProps {
  value: string;
  onChange: (value: string) => void;
  maxLength?: number;
}

export const TextInputCard: React.FC<TextInputCardProps> = ({
  value,
  onChange,
  maxLength = 5000,
}) => {
  const handleClear = () => {
    onChange('');
  };

  const characterCount = value.length;
  const isNearLimit = characterCount > maxLength * 0.8;

  return (
    <Card className="text-input-card">
      <div className="text-input-card__header">
        <h3>Text to Speech</h3>
        <div className="text-input-card__actions">
          <span
            className={`text-input-card__counter ${
              isNearLimit ? 'text-input-card__counter--warning' : ''
            }`}
          >
            {characterCount} / {maxLength}
          </span>
          {value && (
            <Button variant="ghost" size="sm" onClick={handleClear}>
              Clear
            </Button>
          )}
        </div>
      </div>

      <Textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Enter text to convert to speech..."
        rows={8}
        maxLength={maxLength}
        className="text-input-card__textarea"
      />
    </Card>
  );
};
