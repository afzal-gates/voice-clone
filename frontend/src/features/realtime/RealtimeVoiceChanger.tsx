/**
 * Real-Time Voice Changer Feature
 *
 * Real-time voice changing with WebSocket communication
 */

import React, { useEffect } from 'react';
import { Card } from '@/components/ui/Card';
import { StatusIndicator } from './components/StatusIndicator';
import { VoiceGrid } from './components/VoiceGrid';
import { AudioMeters } from './components/AudioMeters';
import { ControlPanel } from './components/ControlPanel';
import { PresetSelector } from './components/PresetSelector';
import { useRealtimeWebSocket } from './hooks/useRealtimeWebSocket';
import './RealtimeVoiceChanger.css';

export const RealtimeVoiceChanger: React.FC = () => {
  const {
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
    refreshStatus,
    loadPreset,
  } = useRealtimeWebSocket();

  // Auto-connect on mount
  useEffect(() => {
    connect();
    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  // Poll status when processing
  useEffect(() => {
    if (!audioStatus.processing) return;

    const interval = setInterval(() => {
      refreshStatus();
    }, 200); // Update every 200ms for smooth meters

    return () => clearInterval(interval);
  }, [audioStatus.processing, refreshStatus]);

  return (
    <div className="realtime-voice-changer">
      <Card>
        <div className="realtime-voice-changer__header">
          <h2 className="realtime-voice-changer__title">Real-Time Voice Changer</h2>
          <p className="realtime-voice-changer__description">
            Change your voice in real-time. Select a voice and start processing to begin.
          </p>
        </div>

        <StatusIndicator
          connected={connected}
          connecting={connecting}
          processing={audioStatus.processing}
        />

        {error && (
          <div className="realtime-voice-changer__error">
            <svg
              className="realtime-voice-changer__error-icon"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                clipRule="evenodd"
              />
            </svg>
            <span>{error}</span>
          </div>
        )}
      </Card>

      {connected && (
        <>
          <Card>
            <div className="realtime-voice-changer__section">
              <PresetSelector
                presets={presets}
                selectedPresetId={selectedPresetId}
                onSelectPreset={loadPreset}
                disabled={audioStatus.processing}
              />
            </div>
          </Card>

          <Card>
            <div className="realtime-voice-changer__section">
              <h3 className="realtime-voice-changer__section-title">Select Voice</h3>
              <VoiceGrid
                voices={voices}
                selectedVoiceId={selectedVoice?.id || null}
                onSelectVoice={selectVoice}
                disabled={audioStatus.processing}
              />
            </div>
          </Card>

          <Card>
            <div className="realtime-voice-changer__section">
              <h3 className="realtime-voice-changer__section-title">Audio Levels</h3>
              <AudioMeters audioStatus={audioStatus} />
            </div>
          </Card>

          <Card>
            <div className="realtime-voice-changer__section">
              <h3 className="realtime-voice-changer__section-title">Controls</h3>
              <ControlPanel
                connected={connected}
                processing={audioStatus.processing}
                hasVoiceSelected={selectedVoice !== null}
                onStart={startProcessing}
                onStop={stopProcessing}
                onConnect={connect}
                onDisconnect={disconnect}
              />
            </div>
          </Card>
        </>
      )}

      {!connected && !connecting && (
        <Card>
          <div className="realtime-voice-changer__disconnected">
            <svg
              className="realtime-voice-changer__disconnected-icon"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M13 10V3L4 14h7v7l9-11h-7z"
              />
            </svg>
            <h3 className="realtime-voice-changer__disconnected-title">
              Not Connected
            </h3>
            <p className="realtime-voice-changer__disconnected-message">
              Click connect to start using the real-time voice changer.
            </p>
          </div>
        </Card>
      )}
    </div>
  );
};
