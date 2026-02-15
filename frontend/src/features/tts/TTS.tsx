/**
 * TTS Feature Component
 *
 * Main Text-to-Speech interface
 */

import { useEffect } from 'react';
import { useTTSStore } from '@/store/ttsStore';
import { Button, ProgressBar } from '@/components/ui';
import {
  TextInputCard,
  ModelSelector,
  VoiceSelector,
  ParametersCard,
  TTSResultCard,
} from './components';
import { useToast } from '@/hooks/useToast';
import './tts.styles.css';

export const TTS: React.FC = () => {
  const {
    text,
    selectedModel,
    selectedVoiceId,
    models,
    parameters,
    isGenerating,
    progress,
    error,
    result,
    setText,
    setModel,
    setVoice,
    setSpeed,
    setPitch,
    setRefText,
    setReferenceAudio,
    loadModels,
    generate,
    reset,
  } = useTTSStore();

  const { showToast } = useToast();

  // Load models on mount
  useEffect(() => {
    loadModels();
  }, [loadModels]);

  // Show error toast
  useEffect(() => {
    if (error) {
      showToast({ type: 'error', message: error });
    }
  }, [error, showToast]);

  const handleGenerate = async () => {
    if (!text.trim()) {
      showToast({ type: 'error', message: 'Please enter text to generate speech' });
      return;
    }

    await generate();
  };

  const selectedModelData = models.find((m) => m.id === selectedModel);
  const showReferenceText = selectedModelData?.requiresReferenceText || false;

  const canGenerate = text.trim().length > 0 && !isGenerating;

  return (
    <div className="tts-feature">
      <div className="tts-feature__container">
        {/* Text Input Section */}
        <section className="tts-feature__section">
          <TextInputCard value={text} onChange={setText} />
        </section>

        {/* Model Selection */}
        <section className="tts-feature__section">
          <ModelSelector
            models={models}
            selectedModel={selectedModel}
            onChange={setModel}
            disabled={isGenerating}
          />
        </section>

        {/* Voice Selection */}
        <section className="tts-feature__section">
          <VoiceSelector selectedVoiceId={selectedVoiceId} onSelectVoice={setVoice} />
        </section>

        {/* Parameters */}
        <section className="tts-feature__section">
          <ParametersCard
            parameters={parameters}
            onSpeedChange={setSpeed}
            onPitchChange={setPitch}
            onRefTextChange={setRefText}
            onReferenceAudioChange={setReferenceAudio}
            showReferenceText={showReferenceText}
          />
        </section>

        {/* Generation Progress */}
        {isGenerating && (
          <section className="tts-feature__section">
            <div className="tts-feature__progress">
              <h4>Generating Speech...</h4>
              <ProgressBar progress={progress} />
              <p className="tts-feature__progress-text">
                {progress < 25
                  ? 'Initializing...'
                  : progress < 50
                  ? 'Processing text...'
                  : progress < 100
                  ? 'Generating audio...'
                  : 'Complete!'}
              </p>
            </div>
          </section>
        )}

        {/* Generate Button */}
        {!result && (
          <section className="tts-feature__section tts-feature__actions">
            <Button
              variant="primary"
              size="lg"
              onClick={handleGenerate}
              disabled={!canGenerate}
              className="tts-feature__generate-btn"
            >
              {isGenerating ? (
                <>
                  <div className="spinner spinner--sm" />
                  Generating...
                </>
              ) : (
                <>
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                    <path
                      d="M12 2a3 3 0 00-3 3v7a3 3 0 006 0V5a3 3 0 00-3-3z"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                    <path
                      d="M19 10v2a7 7 0 01-14 0v-2M12 19v3"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                  Generate Speech
                </>
              )}
            </Button>
          </section>
        )}

        {/* Result */}
        {result && (
          <section className="tts-feature__section">
            <TTSResultCard result={result} onReset={reset} />
          </section>
        )}
      </div>
    </div>
  );
};
