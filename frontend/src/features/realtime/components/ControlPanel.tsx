/**
 * Control Panel Component
 *
 * Start/stop controls for real-time processing
 */

import React from 'react';
import { Button } from '@/components/ui/Button';

interface ControlPanelProps {
  connected: boolean;
  processing: boolean;
  hasVoiceSelected: boolean;
  onStart: () => void;
  onStop: () => void;
  onConnect: () => void;
  onDisconnect: () => void;
}

export const ControlPanel: React.FC<ControlPanelProps> = ({
  connected,
  processing,
  hasVoiceSelected,
  onStart,
  onStop,
  onConnect,
  onDisconnect,
}) => {
  return (
    <div className="control-panel">
      <div className="control-panel__connection">
        {connected ? (
          <Button variant="secondary" onClick={onDisconnect}>
            Disconnect
          </Button>
        ) : (
          <Button variant="primary" onClick={onConnect}>
            Connect
          </Button>
        )}
      </div>

      <div className="control-panel__processing">
        {processing ? (
          <Button variant="danger" onClick={onStop} disabled={!connected} fullWidth>
            Stop Processing
          </Button>
        ) : (
          <Button
            variant="primary"
            onClick={onStart}
            disabled={!connected || !hasVoiceSelected}
            fullWidth
          >
            Start Processing
          </Button>
        )}
        {!hasVoiceSelected && connected && (
          <p className="control-panel__hint">Select a voice to begin</p>
        )}
      </div>
    </div>
  );
};
