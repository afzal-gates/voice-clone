/**
 * VoiceSelector Component
 *
 * Voice selection interface with library grid
 */

import { useEffect } from 'react';
import { useVoiceStore } from '@/store/voiceStore';
import { VoiceLibraryGrid } from './VoiceLibraryGrid';

interface VoiceSelectorProps {
  selectedVoiceId: string | null;
  onSelectVoice: (voiceId: string) => void;
}

export const VoiceSelector: React.FC<VoiceSelectorProps> = ({
  selectedVoiceId,
  onSelectVoice,
}) => {
  const {
    voices,
    isLoading,
    playingVoiceId,
    loadVoices,
    playPreview,
    stopPreview,
  } = useVoiceStore();

  // Load voices on mount
  useEffect(() => {
    loadVoices();
  }, [loadVoices]);

  const handleSelectVoice = (voiceId: string) => {
    onSelectVoice(voiceId);
  };

  const handlePreviewVoice = (voiceId: string) => {
    if (playingVoiceId === voiceId) {
      stopPreview();
    } else {
      playPreview(voiceId);
    }
  };

  return (
    <VoiceLibraryGrid
      voices={voices}
      selectedVoiceId={selectedVoiceId}
      playingVoiceId={playingVoiceId}
      onSelectVoice={handleSelectVoice}
      onPreviewVoice={handlePreviewVoice}
      isLoading={isLoading}
    />
  );
};
