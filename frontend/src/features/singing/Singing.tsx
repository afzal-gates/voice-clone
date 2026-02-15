/**
 * Singing Feature Component
 *
 * Main DiffSinger singing synthesis interface
 */

import { useEffect } from 'react';
import { useSingingStore } from '@/store/singingStore';
import { Button, ProgressBar } from '@/components/ui';
import {
  LyricsInput,
  MelodyInput,
  VoiceSelector,
  SingingControls,
  SingingResult,
} from './components';
import { useToast } from '@/hooks/useToast';
import './singing.styles.css';

export const Singing: React.FC = () => {
  const {
    lyrics,
    melodyMode,
    melodyInput,
    melodyFile,
    selectedVoice,
    tempo,
    keyShift,
    availableVoices,
    isGenerating,
    progress,
    error,
    result,
    setLyrics,
    setMelodyMode,
    setMelodyInput,
    setMelodyFile,
    setVoice,
    setTempo,
    setKeyShift,
    loadVoices,
    generate,
    reset,
  } = useSingingStore();

  const { showToast } = useToast();

  // Load voices on mount
  useEffect(() => {
    loadVoices();
  }, [loadVoices]);

  // Show error toast
  useEffect(() => {
    if (error) {
      showToast({ type: 'error', message: error });
    }
  }, [error, showToast]);

  const handleGenerate = async () => {
    if (!lyrics.trim()) {
      showToast({ type: 'error', message: 'Please enter lyrics to synthesize' });
      return;
    }

    if (!selectedVoice) {
      showToast({ type: 'error', message: 'Please select a voice model' });
      return;
    }

    if (melodyMode === 'notation' && !melodyInput.trim()) {
      showToast({ type: 'error', message: 'Please provide melody notation' });
      return;
    }

    if (melodyMode === 'midi' && !melodyFile) {
      showToast({ type: 'error', message: 'Please upload a MIDI file' });
      return;
    }

    await generate();
  };

  const canGenerate =
    lyrics.trim().length > 0 &&
    selectedVoice &&
    !isGenerating &&
    (melodyMode === 'auto' ||
      (melodyMode === 'notation' && melodyInput.trim().length > 0) ||
      (melodyMode === 'midi' && melodyFile !== null));

  return (
    <div className="singing-feature">
      <div className="singing-feature__container">
        {/* Lyrics Input Section */}
        <section className="singing-feature__section">
          <LyricsInput value={lyrics} onChange={setLyrics} disabled={isGenerating} />
        </section>

        {/* Melody Input Section */}
        <section className="singing-feature__section">
          <MelodyInput
            mode={melodyMode}
            notationInput={melodyInput}
            midiFile={melodyFile}
            onModeChange={setMelodyMode}
            onNotationChange={setMelodyInput}
            onMidiFileChange={setMelodyFile}
            disabled={isGenerating}
          />
        </section>

        {/* Voice Selection Section */}
        <section className="singing-feature__section">
          <VoiceSelector
            voices={availableVoices}
            selectedVoice={selectedVoice}
            onChange={setVoice}
            disabled={isGenerating}
          />
        </section>

        {/* Controls Section */}
        <section className="singing-feature__section">
          <SingingControls
            tempo={tempo}
            keyShift={keyShift}
            onTempoChange={setTempo}
            onKeyShiftChange={setKeyShift}
            disabled={isGenerating}
          />
        </section>

        {/* Generation Progress */}
        {isGenerating && (
          <section className="singing-feature__section">
            <div className="singing-feature__progress">
              <h4>Generating Singing...</h4>
              <ProgressBar progress={progress} />
              <p className="singing-feature__progress-text">
                {progress < 25
                  ? 'Initializing...'
                  : progress < 60
                  ? 'Processing lyrics and melody...'
                  : progress < 100
                  ? 'Synthesizing vocals...'
                  : 'Complete!'}
              </p>
            </div>
          </section>
        )}

        {/* Generate Button */}
        {!result && (
          <section className="singing-feature__section singing-feature__actions">
            <Button
              variant="primary"
              size="lg"
              onClick={handleGenerate}
              disabled={!canGenerate}
              className="singing-feature__generate-btn"
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
                      d="M9 18V5l12-2v13M9 13l12-2"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                    <circle
                      cx="6"
                      cy="18"
                      r="3"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                    <circle
                      cx="18"
                      cy="16"
                      r="3"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                  Generate Singing
                </>
              )}
            </Button>
          </section>
        )}

        {/* Result */}
        {result && (
          <section className="singing-feature__section">
            <SingingResult result={result} onReset={reset} />
          </section>
        )}
      </div>
    </div>
  );
};
