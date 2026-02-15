/**
 * Song Generator Component
 *
 * Complete AI song generation interface with lyrics, genre, mood, BPM controls
 */

import React from 'react';
import { useSongGeneratorStore } from '@/store/songGeneratorStore';
import type { MusicGenre, MusicMood } from '@/types/song.types';
import { downloadSongOutput } from '@/services/song.service';

export const SongGenerator: React.FC = () => {
  const {
    // Form state
    lyrics,
    genre,
    mood,
    bpm,
    instruments,
    vocalType,
    language,
    songTitle,
    artistName,
    generateVideo,
    duration,
    showAdvanced,

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
    setVocalType,
    setLanguage,
    setSongTitle,
    setArtistName,
    setGenerateVideo,
    setDuration,
    toggleAdvanced,
    generate,
    reset,
  } = useSongGeneratorStore();

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
    await generate();
  };

  const handleDownload = (outputType: string) => {
    if (jobId) {
      const url = downloadSongOutput(jobId, outputType);
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
        return '';
    }
  };

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '20px' }}>
      <div style={{ marginBottom: '30px' }}>
        <h1 style={{ fontSize: '32px', fontWeight: 'bold', marginBottom: '8px' }}>
          AI Song Generator
        </h1>
        <p style={{ color: '#6b7280' }}>
          Create complete songs with instrumentals, vocals, and mixing
        </p>
      </div>

      {/* Error Display */}
      {error && (
        <div
          style={{
            marginBottom: '20px',
            padding: '16px',
            background: '#fef2f2',
            border: '1px solid #fecaca',
            borderRadius: '8px',
          }}
        >
          <p style={{ color: '#991b1b', fontWeight: '500' }}>Error: {error}</p>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '30px' }}>
        {/* Left Column: Input Form */}
        <div>
          {/* Lyrics */}
          <div style={{ marginBottom: '20px' }}>
            <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '8px' }}>
              Lyrics <span style={{ color: '#ef4444' }}>*</span>
            </label>
            <textarea
              value={lyrics}
              onChange={(e) => setLyrics(e.target.value)}
              placeholder="Enter your song lyrics here..."
              rows={8}
              maxLength={5000}
              disabled={isGenerating}
              style={{
                width: '100%',
                padding: '12px',
                border: '1px solid #d1d5db',
                borderRadius: '8px',
                fontSize: '14px',
                resize: 'vertical',
              }}
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '4px' }}>
              <span style={{ fontSize: '12px', color: '#6b7280' }}>10-5000 characters</span>
              <span style={{ fontSize: '12px', color: '#6b7280' }}>{lyrics.length} / 5000</span>
            </div>
          </div>

          {/* Song Info */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '20px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '8px' }}>
                Song Title
              </label>
              <input
                type="text"
                value={songTitle}
                onChange={(e) => setSongTitle(e.target.value)}
                disabled={isGenerating}
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  border: '1px solid #d1d5db',
                  borderRadius: '8px',
                  fontSize: '14px',
                }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '8px' }}>
                Artist Name
              </label>
              <input
                type="text"
                value={artistName}
                onChange={(e) => setArtistName(e.target.value)}
                disabled={isGenerating}
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  border: '1px solid #d1d5db',
                  borderRadius: '8px',
                  fontSize: '14px',
                }}
              />
            </div>
          </div>

          {/* Genre and Mood */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '20px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '8px' }}>
                Genre <span style={{ color: '#ef4444' }}>*</span>
              </label>
              <select
                value={genre}
                onChange={(e) => setGenre(e.target.value as MusicGenre)}
                disabled={isGenerating}
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  border: '1px solid #d1d5db',
                  borderRadius: '8px',
                  fontSize: '14px',
                }}
              >
                <option value="pop">Pop</option>
                <option value="rock">Rock</option>
                <option value="edm">EDM</option>
                <option value="classical">Classical</option>
                <option value="cinematic">Cinematic</option>
                <option value="hiphop">Hip-Hop</option>
                <option value="jazz">Jazz</option>
                <option value="country">Country</option>
                <option value="folk">Folk</option>
                <option value="ambient">Ambient</option>
              </select>
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '8px' }}>
                Mood <span style={{ color: '#ef4444' }}>*</span>
              </label>
              <select
                value={mood}
                onChange={(e) => setMood(e.target.value as MusicMood)}
                disabled={isGenerating}
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  border: '1px solid #d1d5db',
                  borderRadius: '8px',
                  fontSize: '14px',
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

          {/* BPM */}
          <div style={{ marginBottom: '20px' }}>
            <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '8px' }}>
              Tempo (BPM): {bpm}
            </label>
            <input
              type="range"
              min="60"
              max="200"
              value={bpm}
              onChange={(e) => setBpm(Number(e.target.value))}
              disabled={isGenerating}
              style={{ width: '100%' }}
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: '#6b7280' }}>
              <span>60 (Slow)</span>
              <span>120 (Medium)</span>
              <span>200 (Fast)</span>
            </div>
          </div>

          {/* Vocal Type */}
          <div style={{ marginBottom: '20px' }}>
            <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '8px' }}>
              Vocal Type
            </label>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px' }}>
              {(['ai', 'male', 'female', 'choir'] as const).map((type) => (
                <button
                  key={type}
                  onClick={() => setVocalType(type)}
                  disabled={isGenerating}
                  style={{
                    padding: '8px 16px',
                    borderRadius: '8px',
                    border: '1px solid',
                    borderColor: vocalType === type ? '#3b82f6' : '#d1d5db',
                    background: vocalType === type ? '#3b82f6' : '#ffffff',
                    color: vocalType === type ? '#ffffff' : '#374151',
                    cursor: isGenerating ? 'not-allowed' : 'pointer',
                    fontSize: '14px',
                  }}
                >
                  {type.charAt(0).toUpperCase() + type.slice(1)}
                </button>
              ))}
            </div>
          </div>

          {/* Advanced Settings */}
          <div style={{ marginBottom: '20px' }}>
            <button
              onClick={toggleAdvanced}
              disabled={isGenerating}
              style={{
                display: 'flex',
                alignItems: 'center',
                fontSize: '14px',
                fontWeight: '500',
                color: '#3b82f6',
                background: 'none',
                border: 'none',
                cursor: isGenerating ? 'not-allowed' : 'pointer',
                padding: 0,
              }}
            >
              <span>{showAdvanced ? '▼' : '▶'}</span>
              <span style={{ marginLeft: '8px' }}>Advanced Settings</span>
            </button>

            {showAdvanced && (
              <div style={{ marginTop: '16px', padding: '16px', background: '#f9fafb', borderRadius: '8px' }}>
                {/* Duration */}
                <div style={{ marginBottom: '16px' }}>
                  <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '8px' }}>
                    Duration: {duration}s
                  </label>
                  <input
                    type="range"
                    min="5"
                    max="60"
                    value={duration}
                    onChange={(e) => setDuration(Number(e.target.value))}
                    disabled={isGenerating}
                    style={{ width: '100%' }}
                  />
                </div>

                {/* Instruments */}
                <div style={{ marginBottom: '16px' }}>
                  <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '8px' }}>
                    Instruments (optional)
                  </label>
                  <select
                    multiple
                    value={instruments}
                    onChange={(e) => {
                      const selected = Array.from(e.target.selectedOptions, option => option.value);
                      setInstruments(selected);
                    }}
                    disabled={isGenerating}
                    style={{
                      width: '100%',
                      padding: '8px 12px',
                      border: '1px solid #d1d5db',
                      borderRadius: '8px',
                      fontSize: '14px',
                      minHeight: '120px',
                      cursor: isGenerating ? 'not-allowed' : 'pointer',
                    }}
                  >
                    {availableInstruments.map((instrument) => (
                      <option key={instrument} value={instrument.toLowerCase()}>
                        {instrument}
                      </option>
                    ))}
                  </select>
                  <span style={{ fontSize: '12px', color: '#6b7280', display: 'block', marginTop: '4px' }}>
                    Hold Ctrl (Windows) or Cmd (Mac) to select multiple
                  </span>
                  {instruments.length > 0 && (
                    <div style={{ marginTop: '8px', display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                      {instruments.map((instrument) => (
                        <span
                          key={instrument}
                          style={{
                            padding: '4px 12px',
                            background: '#3b82f6',
                            color: '#ffffff',
                            borderRadius: '16px',
                            fontSize: '12px',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px',
                          }}
                        >
                          {instrument}
                          <button
                            onClick={() => setInstruments(instruments.filter(i => i !== instrument))}
                            disabled={isGenerating}
                            style={{
                              background: 'none',
                              border: 'none',
                              color: '#ffffff',
                              cursor: isGenerating ? 'not-allowed' : 'pointer',
                              padding: '0',
                              fontSize: '14px',
                              fontWeight: 'bold',
                            }}
                          >
                            ×
                          </button>
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                {/* Language */}
                <div style={{ marginBottom: '16px' }}>
                  <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '8px' }}>
                    Language
                  </label>
                  <select
                    value={language}
                    onChange={(e) => setLanguage(e.target.value)}
                    disabled={isGenerating}
                    style={{
                      width: '100%',
                      padding: '8px 12px',
                      border: '1px solid #d1d5db',
                      borderRadius: '8px',
                      fontSize: '14px',
                    }}
                  >
                    <option value="en">English</option>
                    <option value="es">Spanish</option>
                    <option value="fr">French</option>
                    <option value="de">German</option>
                    <option value="it">Italian</option>
                    <option value="pt">Portuguese</option>
                    <option value="ja">Japanese</option>
                    <option value="ko">Korean</option>
                    <option value="zh">Chinese</option>
                  </select>
                </div>

                {/* Generate Video */}
                <div>
                  <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
                    <input
                      type="checkbox"
                      checked={generateVideo}
                      onChange={(e) => setGenerateVideo(e.target.checked)}
                      disabled={isGenerating}
                      style={{ marginRight: '8px' }}
                    />
                    <span style={{ fontSize: '14px' }}>Generate music video</span>
                  </label>
                </div>
              </div>
            )}
          </div>

          {/* Generate Button */}
          <div style={{ display: 'flex', gap: '12px' }}>
            <button
              onClick={handleGenerate}
              disabled={isGenerating || !lyrics || lyrics.length < 10}
              style={{
                flex: 1,
                padding: '12px 24px',
                background: isGenerating || !lyrics || lyrics.length < 10 ? '#9ca3af' : '#3b82f6',
                color: '#ffffff',
                border: 'none',
                borderRadius: '8px',
                fontSize: '16px',
                fontWeight: '500',
                cursor: isGenerating || !lyrics || lyrics.length < 10 ? 'not-allowed' : 'pointer',
              }}
            >
              {isGenerating ? 'Generating...' : 'Generate Song'}
            </button>
            <button
              onClick={reset}
              disabled={isGenerating}
              style={{
                padding: '12px 24px',
                background: '#ffffff',
                color: '#374151',
                border: '1px solid #d1d5db',
                borderRadius: '8px',
                fontSize: '16px',
                cursor: isGenerating ? 'not-allowed' : 'pointer',
              }}
            >
              Reset
            </button>
          </div>
        </div>

        {/* Right Column: Status and Results */}
        <div>
          {/* Status */}
          {(status || isGenerating) && (
            <div
              style={{
                padding: '20px',
                background: '#f9fafb',
                borderRadius: '8px',
                border: '1px solid #e5e7eb',
                marginBottom: '20px',
              }}
            >
              <h3 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '16px' }}>
                Generation Status
              </h3>
              <div style={{ marginBottom: '12px' }}>
                <span style={{ color: getStatusColor(), fontWeight: '500' }}>
                  {getStatusText()}
                </span>
              </div>
              {status === 'processing' && (
                <div style={{ background: '#e5e7eb', borderRadius: '4px', height: '8px', overflow: 'hidden' }}>
                  <div
                    style={{
                      background: '#3b82f6',
                      height: '100%',
                      width: `${progress * 100}%`,
                      transition: 'width 0.3s ease',
                    }}
                  />
                </div>
              )}
            </div>
          )}

          {/* Results */}
          {status === 'completed' && outputs && (
            <div
              style={{
                padding: '20px',
                background: '#f0fdf4',
                borderRadius: '8px',
                border: '1px solid #86efac',
                marginBottom: '20px',
              }}
            >
              <h3 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '16px', color: '#166534' }}>
                Your Song is Ready!
              </h3>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                {/* Mixed Song */}
                {outputs.mixed_song_mp3 && (
                  <div>
                    <h4 style={{ fontSize: '14px', fontWeight: '500', marginBottom: '8px' }}>Mixed Song</h4>
                    <button
                      onClick={() => handleDownload('mixed_song_wav')}
                      style={{
                        width: '100%',
                        padding: '8px 16px',
                        background: '#3b82f6',
                        color: '#ffffff',
                        border: 'none',
                        borderRadius: '4px',
                        fontSize: '14px',
                        cursor: 'pointer',
                        marginBottom: '4px',
                      }}
                    >
                      WAV
                    </button>
                    <button
                      onClick={() => handleDownload('mixed_song_mp3')}
                      style={{
                        width: '100%',
                        padding: '8px 16px',
                        background: '#10b981',
                        color: '#ffffff',
                        border: 'none',
                        borderRadius: '4px',
                        fontSize: '14px',
                        cursor: 'pointer',
                      }}
                    >
                      MP3
                    </button>
                  </div>
                )}

                {/* Instrumental */}
                {outputs.instrumental_mp3 && (
                  <div>
                    <h4 style={{ fontSize: '14px', fontWeight: '500', marginBottom: '8px' }}>Instrumental</h4>
                    <button
                      onClick={() => handleDownload('instrumental_wav')}
                      style={{
                        width: '100%',
                        padding: '8px 16px',
                        background: '#3b82f6',
                        color: '#ffffff',
                        border: 'none',
                        borderRadius: '4px',
                        fontSize: '14px',
                        cursor: 'pointer',
                        marginBottom: '4px',
                      }}
                    >
                      WAV
                    </button>
                    <button
                      onClick={() => handleDownload('instrumental_mp3')}
                      style={{
                        width: '100%',
                        padding: '8px 16px',
                        background: '#10b981',
                        color: '#ffffff',
                        border: 'none',
                        borderRadius: '4px',
                        fontSize: '14px',
                        cursor: 'pointer',
                      }}
                    >
                      MP3
                    </button>
                  </div>
                )}

                {/* Vocals */}
                {outputs.vocals_mp3 && (
                  <div>
                    <h4 style={{ fontSize: '14px', fontWeight: '500', marginBottom: '8px' }}>Vocals</h4>
                    <button
                      onClick={() => handleDownload('vocals_wav')}
                      style={{
                        width: '100%',
                        padding: '8px 16px',
                        background: '#3b82f6',
                        color: '#ffffff',
                        border: 'none',
                        borderRadius: '4px',
                        fontSize: '14px',
                        cursor: 'pointer',
                        marginBottom: '4px',
                      }}
                    >
                      WAV
                    </button>
                    <button
                      onClick={() => handleDownload('vocals_mp3')}
                      style={{
                        width: '100%',
                        padding: '8px 16px',
                        background: '#10b981',
                        color: '#ffffff',
                        border: 'none',
                        borderRadius: '4px',
                        fontSize: '14px',
                        cursor: 'pointer',
                      }}
                    >
                      MP3
                    </button>
                  </div>
                )}

                {/* MIDI */}
                {outputs.midi && (
                  <div>
                    <h4 style={{ fontSize: '14px', fontWeight: '500', marginBottom: '8px' }}>MIDI</h4>
                    <button
                      onClick={() => handleDownload('midi')}
                      style={{
                        width: '100%',
                        padding: '8px 16px',
                        background: '#8b5cf6',
                        color: '#ffffff',
                        border: 'none',
                        borderRadius: '4px',
                        fontSize: '14px',
                        cursor: 'pointer',
                      }}
                    >
                      Download MIDI
                    </button>
                  </div>
                )}

                {/* Video */}
                {outputs.video && (
                  <div style={{ gridColumn: '1 / -1' }}>
                    <h4 style={{ fontSize: '14px', fontWeight: '500', marginBottom: '8px' }}>Music Video</h4>
                    <button
                      onClick={() => handleDownload('video')}
                      style={{
                        width: '100%',
                        padding: '8px 16px',
                        background: '#ef4444',
                        color: '#ffffff',
                        border: 'none',
                        borderRadius: '4px',
                        fontSize: '14px',
                        cursor: 'pointer',
                      }}
                    >
                      Download Video (MP4)
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Info Card */}
          <div
            style={{
              padding: '20px',
              background: '#eff6ff',
              borderRadius: '8px',
              border: '1px solid #bfdbfe',
            }}
          >
            <h3 style={{ fontSize: '16px', fontWeight: '500', marginBottom: '12px', color: '#1e40af' }}>
              How it works
            </h3>
            <ul style={{ fontSize: '14px', color: '#1e40af', lineHeight: '1.6' }}>
              <li>• Generates complete songs with AI instrumentals and vocals</li>
              <li>• Produces separate tracks for remixing</li>
              <li>• Exports MIDI for further editing</li>
              <li>• Optional music video with waveform visualization</li>
              <li>• Generation takes 3-10 minutes depending on options</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};
