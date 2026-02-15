/**
 * Only Music (Instrumental) Generator Component
 *
 * Generate instrumental music from lyrics without vocal synthesis
 */

import React from 'react';
import { useInstrumentalStore } from '@/store/instrumentalStore';
import type { MusicGenre, MusicMood } from '@/types/instrumental.types';
import { downloadInstrumentalOutput } from '@/services/instrumental.service';

export const OnlyMusic: React.FC = () => {
  const {
    // Form state
    lyrics,
    genre,
    mood,
    bpm,
    instruments,
    title,
    duration,

    // Job state
    jobId,
    status,
    outputs,
    progress,
    error,
    isGenerating,

    // Actions
    setLyrics,
    setGenre,
    setMood,
    setBpm,
    setInstruments,
    setTitle,
    setDuration,
    generateMusic,
    reset,
  } = useInstrumentalStore();

  // Available instruments for multiselect
  const availableInstruments = [
    'Piano',
    'Guitar',
    'Bass',
    'Drums',
    'Strings',
    'Synthesizer',
    'Saxophone',
    'Trumpet',
    'Violin',
    'Flute',
    'Organ',
    'Electric Guitar',
  ];

  const handleGenerate = async () => {
    await generateMusic();
  };

  const handleDownload = (outputType: string) => {
    if (jobId) {
      const url = downloadInstrumentalOutput(jobId, outputType);
      window.open(url, '_blank');
    }
  };

  const getStatusColor = () => {
    switch (status) {
      case 'completed':
        return '#10b981';
      case 'failed':
        return '#ef4444';
      case 'pending':
      case 'processing':
        return '#3b82f6';
      default:
        return '#6b7280';
    }
  };

  const getStatusText = () => {
    switch (status) {
      case 'pending':
        return 'Queued...';
      case 'processing':
        return `Generating... ${Math.round(progress * 100)}%`;
      case 'completed':
        return 'Complete!';
      case 'failed':
        return 'Failed';
      default:
        return 'Ready';
    }
  };

  return (
    <div style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: '32px' }}>
        <h1 style={{ fontSize: '28px', fontWeight: 'bold', marginBottom: '8px', color: '#1f2937' }}>
          Only Music Generator
        </h1>
        <p style={{ color: '#6b7280', fontSize: '14px' }}>
          Generate high-quality instrumental music inspired by lyrics, without vocals.
        </p>
      </div>

      {/* Form */}
      <div style={{
        background: '#ffffff',
        border: '1px solid #e5e7eb',
        borderRadius: '8px',
        padding: '24px',
        marginBottom: '24px',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
      }}>
        {/* Lyrics */}
        <div style={{ marginBottom: '20px' }}>
          <label style={{
            display: 'block',
            fontSize: '14px',
            fontWeight: '500',
            color: '#374151',
            marginBottom: '8px',
          }}>
            Lyrics <span style={{ color: '#ef4444' }}>*</span>
          </label>
          <textarea
            value={lyrics}
            onChange={(e) => setLyrics(e.target.value)}
            placeholder="Enter lyrics to inspire the music (10-5000 characters)..."
            rows={8}
            disabled={isGenerating}
            style={{
              width: '100%',
              padding: '12px',
              fontSize: '14px',
              border: '1px solid #d1d5db',
              borderRadius: '6px',
              resize: 'vertical',
              fontFamily: 'monospace',
            }}
          />
          <p style={{ fontSize: '12px', color: '#6b7280', marginTop: '4px' }}>
            {lyrics.length} / 5000 characters
          </p>
        </div>

        {/* Title */}
        <div style={{ marginBottom: '20px' }}>
          <label style={{
            display: 'block',
            fontSize: '14px',
            fontWeight: '500',
            color: '#374151',
            marginBottom: '8px',
          }}>
            Title
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Untitled Instrumental"
            disabled={isGenerating}
            style={{
              width: '100%',
              padding: '10px 12px',
              fontSize: '14px',
              border: '1px solid #d1d5db',
              borderRadius: '6px',
            }}
          />
        </div>

        {/* Genre & Mood */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '20px' }}>
          <div>
            <label style={{
              display: 'block',
              fontSize: '14px',
              fontWeight: '500',
              color: '#374151',
              marginBottom: '8px',
            }}>
              Genre <span style={{ color: '#ef4444' }}>*</span>
            </label>
            <select
              value={genre}
              onChange={(e) => setGenre(e.target.value as MusicGenre)}
              disabled={isGenerating}
              style={{
                width: '100%',
                padding: '10px 12px',
                fontSize: '14px',
                border: '1px solid #d1d5db',
                borderRadius: '6px',
                background: '#ffffff',
              }}
            >
              <option value="pop">Pop</option>
              <option value="rock">Rock</option>
              <option value="edm">EDM</option>
              <option value="classical">Classical</option>
              <option value="cinematic">Cinematic</option>
              <option value="hiphop">Hip Hop</option>
              <option value="jazz">Jazz</option>
              <option value="country">Country</option>
              <option value="folk">Folk</option>
              <option value="ambient">Ambient</option>
            </select>
          </div>

          <div>
            <label style={{
              display: 'block',
              fontSize: '14px',
              fontWeight: '500',
              color: '#374151',
              marginBottom: '8px',
            }}>
              Mood <span style={{ color: '#ef4444' }}>*</span>
            </label>
            <select
              value={mood}
              onChange={(e) => setMood(e.target.value as MusicMood)}
              disabled={isGenerating}
              style={{
                width: '100%',
                padding: '10px 12px',
                fontSize: '14px',
                border: '1px solid #d1d5db',
                borderRadius: '6px',
                background: '#ffffff',
              }}
            >
              <option value="happy">Happy</option>
              <option value="sad">Sad</option>
              <option value="dark">Dark</option>
              <option value="romantic">Romantic</option>
              <option value="epic">Epic</option>
              <option value="calm">Calm</option>
              <option value="energetic">Energetic</option>
            </select>
          </div>
        </div>

        {/* BPM & Duration */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '20px' }}>
          <div>
            <label style={{
              display: 'block',
              fontSize: '14px',
              fontWeight: '500',
              color: '#374151',
              marginBottom: '8px',
            }}>
              BPM (Tempo)
            </label>
            <input
              type="number"
              value={bpm}
              onChange={(e) => setBpm(Number(e.target.value))}
              min={60}
              max={200}
              disabled={isGenerating}
              style={{
                width: '100%',
                padding: '10px 12px',
                fontSize: '14px',
                border: '1px solid #d1d5db',
                borderRadius: '6px',
              }}
            />
            <p style={{ fontSize: '12px', color: '#6b7280', marginTop: '4px' }}>
              60-200 BPM
            </p>
          </div>

          <div>
            <label style={{
              display: 'block',
              fontSize: '14px',
              fontWeight: '500',
              color: '#374151',
              marginBottom: '8px',
            }}>
              Duration (seconds)
            </label>
            <input
              type="number"
              value={duration}
              onChange={(e) => setDuration(Number(e.target.value))}
              min={5}
              max={60}
              disabled={isGenerating}
              style={{
                width: '100%',
                padding: '10px 12px',
                fontSize: '14px',
                border: '1px solid #d1d5db',
                borderRadius: '6px',
              }}
            />
            <p style={{ fontSize: '12px', color: '#6b7280', marginTop: '4px' }}>
              5-60 seconds
            </p>
          </div>
        </div>

        {/* Instruments */}
        <div style={{ marginBottom: '20px' }}>
          <label style={{
            display: 'block',
            fontSize: '14px',
            fontWeight: '500',
            color: '#374151',
            marginBottom: '8px',
          }}>
            Instruments (optional)
          </label>
          <select
            multiple
            value={instruments}
            onChange={(e) => {
              const selected = Array.from(e.target.selectedOptions, (option) => option.value);
              setInstruments(selected);
            }}
            disabled={isGenerating}
            style={{
              width: '100%',
              padding: '10px 12px',
              fontSize: '14px',
              border: '1px solid #d1d5db',
              borderRadius: '6px',
              minHeight: '120px',
            }}
          >
            {availableInstruments.map((instrument) => (
              <option key={instrument} value={instrument.toLowerCase()}>
                {instrument}
              </option>
            ))}
          </select>
          <p style={{ fontSize: '12px', color: '#6b7280', marginTop: '4px' }}>
            Hold Ctrl/Cmd to select multiple instruments
          </p>

          {/* Selected instruments badges */}
          {instruments.length > 0 && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: '12px' }}>
              {instruments.map((instrument) => (
                <span
                  key={instrument}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '6px',
                    padding: '4px 12px',
                    background: '#3b82f6',
                    color: '#ffffff',
                    borderRadius: '16px',
                    fontSize: '13px',
                  }}
                >
                  {instrument}
                  <button
                    onClick={() => setInstruments(instruments.filter((i) => i !== instrument))}
                    disabled={isGenerating}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      color: '#ffffff',
                      cursor: 'pointer',
                      fontSize: '16px',
                      padding: '0 2px',
                      lineHeight: '1',
                    }}
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Error Display */}
        {error && (
          <div style={{
            padding: '12px 16px',
            background: '#fef2f2',
            border: '1px solid #fecaca',
            borderRadius: '6px',
            marginBottom: '20px',
          }}>
            <p style={{ color: '#991b1b', fontSize: '14px', fontWeight: '500' }}>
              {error}
            </p>
          </div>
        )}

        {/* Action Buttons */}
        <div style={{ display: 'flex', gap: '12px' }}>
          <button
            onClick={handleGenerate}
            disabled={isGenerating || !lyrics.trim()}
            style={{
              flex: 1,
              padding: '12px 24px',
              fontSize: '16px',
              fontWeight: '600',
              color: '#ffffff',
              background: isGenerating || !lyrics.trim() ? '#9ca3af' : '#3b82f6',
              border: 'none',
              borderRadius: '6px',
              cursor: isGenerating || !lyrics.trim() ? 'not-allowed' : 'pointer',
            }}
          >
            {isGenerating ? 'Generating...' : 'Generate Music'}
          </button>

          <button
            onClick={reset}
            disabled={isGenerating}
            style={{
              padding: '12px 24px',
              fontSize: '16px',
              fontWeight: '600',
              color: '#374151',
              background: '#ffffff',
              border: '1px solid #d1d5db',
              borderRadius: '6px',
              cursor: isGenerating ? 'not-allowed' : 'pointer',
            }}
          >
            Reset
          </button>
        </div>
      </div>

      {/* Status & Progress */}
      {jobId && (
        <div style={{
          background: '#ffffff',
          border: '1px solid #e5e7eb',
          borderRadius: '8px',
          padding: '24px',
          marginBottom: '24px',
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
        }}>
          <div style={{ marginBottom: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <span style={{ fontSize: '14px', fontWeight: '500', color: '#374151' }}>
                Generation Status
              </span>
              <span style={{ fontSize: '14px', fontWeight: '600', color: getStatusColor() }}>
                {getStatusText()}
              </span>
            </div>

            {/* Progress Bar */}
            <div style={{
              width: '100%',
              height: '8px',
              background: '#e5e7eb',
              borderRadius: '4px',
              overflow: 'hidden',
            }}>
              <div style={{
                width: `${progress * 100}%`,
                height: '100%',
                background: getStatusColor(),
                transition: 'width 0.3s ease',
              }} />
            </div>
          </div>

          <p style={{ fontSize: '12px', color: '#6b7280' }}>
            Job ID: <span style={{ fontFamily: 'monospace' }}>{jobId}</span>
          </p>
        </div>
      )}

      {/* Audio Preview */}
      {outputs && status === 'completed' && outputs.instrumental_wav && (
        <div style={{
          background: '#ffffff',
          border: '1px solid #e5e7eb',
          borderRadius: '8px',
          padding: '24px',
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
          marginBottom: '16px',
        }}>
          <h2 style={{ fontSize: '20px', fontWeight: '600', marginBottom: '16px', color: '#1f2937' }}>
            🎧 Audio Preview
          </h2>
          <audio
            controls
            src={`/api/music/generate-instrumental/${jobId}/download/instrumental_wav`}
            style={{
              width: '100%',
              height: '40px',
              outline: 'none',
            }}
          >
            Your browser does not support the audio element.
          </audio>
        </div>
      )}

      {/* Outputs */}
      {outputs && status === 'completed' && (
        <div style={{
          background: '#ffffff',
          border: '1px solid #e5e7eb',
          borderRadius: '8px',
          padding: '24px',
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
        }}>
          <h2 style={{ fontSize: '20px', fontWeight: '600', marginBottom: '16px', color: '#1f2937' }}>
            Downloads
          </h2>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '12px' }}>
            {outputs.instrumental_wav && (
              <button
                onClick={() => handleDownload('instrumental_wav')}
                style={{
                  padding: '12px 16px',
                  fontSize: '14px',
                  fontWeight: '500',
                  color: '#ffffff',
                  background: '#3b82f6',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  textAlign: 'left',
                }}
              >
                🎵 Instrumental (WAV)
              </button>
            )}

            {outputs.instrumental_mp3 && (
              <button
                onClick={() => handleDownload('instrumental_mp3')}
                style={{
                  padding: '12px 16px',
                  fontSize: '14px',
                  fontWeight: '500',
                  color: '#ffffff',
                  background: '#3b82f6',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  textAlign: 'left',
                }}
              >
                🎵 Instrumental (MP3)
              </button>
            )}

            {outputs.midi && (
              <button
                onClick={() => handleDownload('midi')}
                style={{
                  padding: '12px 16px',
                  fontSize: '14px',
                  fontWeight: '500',
                  color: '#ffffff',
                  background: '#8b5cf6',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  textAlign: 'left',
                }}
              >
                🎹 MIDI File
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
