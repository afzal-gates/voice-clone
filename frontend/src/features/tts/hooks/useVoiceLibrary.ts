/**
 * useVoiceLibrary Hook
 *
 * Custom hook for voice library operations
 */

import { useState, useEffect, useCallback } from 'react';
import { getVoices, getVoicePreviewUrl } from '@/services/tts.service';
import type { VoiceProfile, VoiceCategory } from '@/types/tts.types';

interface UseVoiceLibraryReturn {
  voices: VoiceProfile[];
  filteredVoices: VoiceProfile[];
  isLoading: boolean;
  error: string | null;
  searchQuery: string;
  selectedCategory: VoiceCategory;
  playingVoiceId: string | null;
  setSearchQuery: (query: string) => void;
  setSelectedCategory: (category: VoiceCategory) => void;
  playPreview: (voiceId: string) => void;
  stopPreview: () => void;
  reload: () => Promise<void>;
}

export const useVoiceLibrary = (): UseVoiceLibraryReturn => {
  const [voices, setVoices] = useState<VoiceProfile[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<VoiceCategory>('all');
  const [playingVoiceId, setPlayingVoiceId] = useState<string | null>(null);
  const [audioElement, setAudioElement] = useState<HTMLAudioElement | null>(null);

  // Load voices
  const loadVoices = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const data = await getVoices();
      setVoices(data);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load voices';
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Initial load
  useEffect(() => {
    loadVoices();
  }, [loadVoices]);

  // Filter voices based on search and category
  const filteredVoices = voices.filter((voice) => {
    const matchesSearch = voice.name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = selectedCategory === 'all' || voice.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  // Play voice preview
  const playPreview = useCallback((voiceId: string) => {
    // Stop current preview if playing
    if (audioElement) {
      audioElement.pause();
      audioElement.currentTime = 0;
    }

    // If same voice, just stop
    if (playingVoiceId === voiceId) {
      setPlayingVoiceId(null);
      setAudioElement(null);
      return;
    }

    // Create new audio element
    const audio = new Audio(getVoicePreviewUrl(voiceId));

    audio.addEventListener('ended', () => {
      setPlayingVoiceId(null);
      setAudioElement(null);
    });

    audio.addEventListener('error', () => {
      setPlayingVoiceId(null);
      setAudioElement(null);
      setError('Failed to play preview');
    });

    audio.play();
    setAudioElement(audio);
    setPlayingVoiceId(voiceId);
  }, [audioElement, playingVoiceId]);

  // Stop preview
  const stopPreview = useCallback(() => {
    if (audioElement) {
      audioElement.pause();
      audioElement.currentTime = 0;
    }
    setPlayingVoiceId(null);
    setAudioElement(null);
  }, [audioElement]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (audioElement) {
        audioElement.pause();
      }
    };
  }, [audioElement]);

  return {
    voices,
    filteredVoices,
    isLoading,
    error,
    searchQuery,
    selectedCategory,
    playingVoiceId,
    setSearchQuery,
    setSelectedCategory,
    playPreview,
    stopPreview,
    reload: loadVoices,
  };
};
