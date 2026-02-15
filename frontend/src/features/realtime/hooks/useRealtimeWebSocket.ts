/**
 * Real-Time Voice Changer WebSocket Hook
 *
 * Manages WebSocket connection for real-time voice changing
 */

import { useState, useCallback } from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';
import type { AudioStatus, VoiceProfile, RealtimeMessage } from '@/types/realtime.types';
import type { VoicePreset } from '../types';

const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000';
const WS_ENDPOINT = '/ws/realtime-control';

export const useRealtimeWebSocket = () => {
  const [audioStatus, setAudioStatus] = useState<AudioStatus>({
    processing: false,
    input_level: 0,
    output_level: 0,
    latency_ms: 0,
    processing_time_ms: 0,
  });
  const [voices, setVoices] = useState<VoiceProfile[]>([]);
  const [selectedVoice, setSelectedVoice] = useState<VoiceProfile | null>(null);
  const [presets, setPresets] = useState<VoicePreset[]>([]);
  const [selectedPresetId, setSelectedPresetId] = useState<string | null>('none');
  const [error, setError] = useState<string | null>(null);

  const handleMessage = useCallback((message: RealtimeMessage) => {
    setError(null);

    switch (message.type) {
      case 'connected':
        // Connection established - load presets from initial message
        if (message.presets) {
          setPresets(message.presets);
        }
        if (message.voices) {
          setVoices(message.voices);
        }
        break;

      case 'status':
        if (message.status) {
          setAudioStatus(message.status);
        }
        break;

      case 'voices':
        if (message.voices) {
          setVoices(message.voices);
        }
        break;

      case 'voiceSelected':
        if (message.voice) {
          setSelectedVoice(message.voice);
        }
        break;

      case 'presets':
        if (message.presets) {
          setPresets(message.presets);
        }
        break;

      case 'presetLoaded':
        if (message.presetId) {
          setSelectedPresetId(message.presetId);
        }
        break;

      case 'error':
        setError(message.error || 'Unknown error occurred');
        break;

      default:
        console.warn('Unknown message type:', message.type);
    }
  }, []);

  const handleError = useCallback((event: Event) => {
    setError('WebSocket connection error');
    console.error('WebSocket error:', event);
  }, []);

  const handleOpen = useCallback(() => {
    // Request available voices when connected
    send({ action: 'getVoices' });
    send({ action: 'getStatus' });
  }, []);

  const { connected, connecting, connect, disconnect, send } = useWebSocket(
    `${WS_BASE_URL}${WS_ENDPOINT}`,
    {
      onMessage: handleMessage,
      onError: handleError,
      onOpen: handleOpen,
      onClose: () => {
        setAudioStatus({
          processing: false,
          input_level: 0,
          output_level: 0,
          latency_ms: 0,
          processing_time_ms: 0,
        });
        setSelectedVoice(null);
      },
      reconnect: true,
      reconnectInterval: 3000,
      reconnectAttempts: 5,
    }
  );

  const selectVoice = useCallback(
    (voiceId: string) => {
      const success = send({
        action: 'selectVoice',
        voiceId,
      });

      if (!success) {
        setError('Failed to send voice selection. Not connected.');
      }
    },
    [send]
  );

  const startProcessing = useCallback(() => {
    const success = send({
      action: 'start',
    });

    if (!success) {
      setError('Failed to start processing. Not connected.');
    }
  }, [send]);

  const stopProcessing = useCallback(() => {
    const success = send({
      action: 'stop',
    });

    if (!success) {
      setError('Failed to stop processing. Not connected.');
    }
  }, [send]);

  const refreshVoices = useCallback(() => {
    send({ action: 'getVoices' });
  }, [send]);

  const refreshStatus = useCallback(() => {
    send({ action: 'getStatus' });
  }, [send]);

  const loadPreset = useCallback(
    (presetId: string) => {
      const success = send({
        action: 'loadPreset',
        presetId,
      });

      if (!success) {
        setError('Failed to load preset. Not connected.');
      }
    },
    [send]
  );

  const getPresets = useCallback(() => {
    send({ action: 'getPresets' });
  }, [send]);

  return {
    connected,
    connecting,
    connect,
    disconnect,
    audioStatus,
    voices,
    selectedVoice,
    presets,
    selectedPresetId,
    error,
    selectVoice,
    startProcessing,
    stopProcessing,
    refreshVoices,
    refreshStatus,
    loadPreset,
    getPresets,
  };
};
