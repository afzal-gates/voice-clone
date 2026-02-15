/**
 * ModelSelector Component
 *
 * TTS model selection dropdown
 */

import { Select, Card } from '@/components/ui';
import type { TTSModel } from '@/types/tts.types';
import type { SelectOption } from '@/components/ui/Select';

interface ModelSelectorProps {
  models: TTSModel[];
  selectedModel: string | null;
  onChange: (modelId: string) => void;
  disabled?: boolean;
}

export const ModelSelector: React.FC<ModelSelectorProps> = ({
  models,
  selectedModel,
  onChange,
  disabled = false,
}) => {
  const options: SelectOption[] = models.map((model) => ({
    value: model.id,
    label: model.name,
  }));

  const selectedModelData = models.find((m) => m.id === selectedModel);

  return (
    <Card className="model-selector">
      <div className="model-selector__header">
        <h3>TTS Model</h3>
      </div>

      <Select
        options={options}
        value={selectedModel || ''}
        onChange={onChange}
        placeholder="Select a model..."
        disabled={disabled}
      />

      {selectedModelData && (
        <div className="model-selector__info">
          {selectedModelData.description && (
            <p className="model-selector__description">
              {selectedModelData.description}
            </p>
          )}
          {selectedModelData.languages && selectedModelData.languages.length > 0 && (
            <div className="model-selector__languages">
              <strong>Supported Languages:</strong>{' '}
              {selectedModelData.languages.join(', ')}
            </div>
          )}
          {selectedModelData.requiresReferenceText && (
            <div className="model-selector__note">
              Note: This model requires reference text for optimal results
            </div>
          )}
        </div>
      )}
    </Card>
  );
};
