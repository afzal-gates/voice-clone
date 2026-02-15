export interface RealtimeMessage {
  type: 'connected' | 'voiceSelected' | 'status' | 'error' | 'voices' | 'presets' | 'presetLoaded';
  status?: AudioStatus;
  voices?: VoiceProfile[];
  voice?: VoiceProfile;
  error?: string;
  presets?: any[]; // Array of preset objects
  presetId?: string;
}

export interface AudioStatus {
  processing: boolean;
  input_level: number; // 0-1
  output_level: number; // 0-1
  latency_ms: number;
  processing_time_ms: number;
}

export interface VoiceProfile {
  id: string;
  name: string;
  category: 'realistic' | 'character' | 'custom';
  description?: string;
}

export interface VoiceChangeEvent {
  action: 'selectVoice' | 'start' | 'stop' | 'getStatus' | 'getVoices';
  voiceId?: string;
}

export type VoiceCategory = 'all' | 'realistic' | 'character' | 'custom';
