/**
 * Voice Grid Component
 *
 * Grid of available voices
 */

import React, { useState, useMemo } from 'react';
import { SearchFilter } from './SearchFilter';
import { VoiceTile } from './VoiceTile';
import type { VoiceProfile, VoiceCategory } from '@/types/realtime.types';

interface VoiceGridProps {
  voices: VoiceProfile[];
  selectedVoiceId: string | null;
  onSelectVoice: (voiceId: string) => void;
  disabled?: boolean;
}

export const VoiceGrid: React.FC<VoiceGridProps> = ({
  voices,
  selectedVoiceId,
  onSelectVoice,
  disabled = false,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<VoiceCategory>('all');

  const filteredVoices = useMemo(() => {
    return voices.filter((voice) => {
      const matchesSearch =
        searchTerm === '' ||
        voice.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        voice.description?.toLowerCase().includes(searchTerm.toLowerCase());

      const matchesCategory =
        selectedCategory === 'all' || voice.category === selectedCategory;

      return matchesSearch && matchesCategory;
    });
  }, [voices, searchTerm, selectedCategory]);

  return (
    <div className="voice-grid-container">
      <SearchFilter
        searchTerm={searchTerm}
        onSearchChange={setSearchTerm}
        selectedCategory={selectedCategory}
        onCategoryChange={setSelectedCategory}
      />

      {filteredVoices.length === 0 ? (
        <div className="voice-grid__empty">
          <p>No voices found matching your criteria</p>
        </div>
      ) : (
        <div className="voice-grid">
          {filteredVoices.map((voice) => (
            <VoiceTile
              key={voice.id}
              voice={voice}
              selected={voice.id === selectedVoiceId}
              onSelect={onSelectVoice}
              disabled={disabled}
            />
          ))}
        </div>
      )}
    </div>
  );
};
