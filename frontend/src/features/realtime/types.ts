/**
 * Real-Time Voice Changer Types
 *
 * Type definitions for real-time voice changing with effects
 */

export interface VoicePreset {
  id: string;
  name: string;
  description: string;
  icon: string;
}

export interface EffectParameters {
  // Pitch & Formant
  pitch_shift: number; // semitones (-12 to +12)
  formant_shift: number; // ratio (0.5 to 2.0)

  // Reverb
  reverb_enabled: boolean;
  reverb_room_size: number; // 0.0 to 1.0
  reverb_damping: number; // 0.0 to 1.0
  reverb_wet: number; // 0.0 to 1.0

  // Delay/Echo
  delay_enabled: boolean;
  delay_time: number; // seconds (0.01 to 2.0)
  delay_feedback: number; // 0.0 to 0.9
  delay_mix: number; // 0.0 to 1.0

  // Chorus
  chorus_enabled: boolean;
  chorus_rate: number; // Hz (0.1 to 10.0)
  chorus_depth: number; // 0.0 to 1.0
  chorus_mix: number; // 0.0 to 1.0

  // Distortion
  distortion_enabled: boolean;
  distortion_gain: number; // 1.0 to 50.0
  distortion_mix: number; // 0.0 to 1.0

  // Noise Gate
  noise_gate_enabled: boolean;
  noise_gate_threshold: number; // dB (-60 to 0)
  noise_gate_ratio: number; // 1.0 to 10.0

  // Equalizer
  eq_enabled: boolean;
  eq_low_gain: number; // dB (-12 to +12)
  eq_mid_gain: number; // dB (-12 to +12)
  eq_high_gain: number; // dB (-12 to +12)
}

export interface AudioDevice {
  index: number;
  name: string;
  max_input_channels: number;
  max_output_channels: number;
  default_samplerate: number;
  is_input: boolean;
  is_output: boolean;
}

export interface SoundEffect {
  id: string;
  name: string;
  description: string;
  icon: string;
  category: string;
}

export interface RealtimeStatus {
  processing: boolean;
  voice_id: string | null;
  input_level: number;
  output_level: number;
  latency_ms: number;
  processing_time_ms: number;
  sample_rate: number;
  block_size: number;
}

export interface WebSocketMessage {
  type: string;
  [key: string]: any;
}
