/**
 * VoiceLibraryGrid Component
 *
 * Grid display of voice library with filtering and upload
 */

import { useState } from 'react';
import { Input, Button, Card, Modal } from '@/components/ui';
import { VoiceTile } from './VoiceTile';
import { useVoiceStore } from '@/store/voiceStore';
import type { VoiceProfile, VoiceCategory } from '@/types/tts.types';

interface VoiceLibraryGridProps {
  voices: VoiceProfile[];
  selectedVoiceId: string | null;
  playingVoiceId: string | null;
  onSelectVoice: (voiceId: string) => void;
  onPreviewVoice: (voiceId: string) => void;
  isLoading?: boolean;
}

const categories: { value: VoiceCategory; label: string }[] = [
  { value: 'all', label: 'All Voices' },
  { value: 'realistic', label: 'Realistic' },
  { value: 'character', label: 'Character' },
  { value: 'custom', label: 'Custom' },
];

export const VoiceLibraryGrid: React.FC<VoiceLibraryGridProps> = ({
  voices,
  selectedVoiceId,
  playingVoiceId,
  onSelectVoice,
  onPreviewVoice,
  isLoading = false,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<VoiceCategory>('all');
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [uploadName, setUploadName] = useState('');
  const [uploadDescription, setUploadDescription] = useState('');
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const { uploadVoice, loadVoices } = useVoiceStore();

  // Filter voices
  const filteredVoices = voices.filter((voice) => {
    const matchesSearch = voice.name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = selectedCategory === 'all' || voice.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      // Validate audio file
      if (!file.type.startsWith('audio/')) {
        setUploadError('Please select an audio file');
        return;
      }
      setUploadFile(file);
      setUploadError(null);
    }
  };

  const handleUploadVoice = async () => {
    if (!uploadFile || !uploadName.trim()) {
      setUploadError('Please provide a name and select an audio file');
      return;
    }

    try {
      setIsUploading(true);
      setUploadError(null);
      await uploadVoice(uploadFile, uploadName.trim(), uploadDescription.trim());

      // Reset form and close modal
      setUploadName('');
      setUploadDescription('');
      setUploadFile(null);
      setIsUploadModalOpen(false);

      // Refresh voice list
      await loadVoices();
    } catch (error) {
      setUploadError((error as Error).message);
    } finally {
      setIsUploading(false);
    }
  };

  const handleCloseUploadModal = () => {
    if (!isUploading) {
      setIsUploadModalOpen(false);
      setUploadName('');
      setUploadDescription('');
      setUploadFile(null);
      setUploadError(null);
    }
  };

  return (
    <>
      <Card className="voice-library-grid">
        <div className="voice-library-grid__header">
          <div>
            <h3>Voice Library</h3>
            <div className="voice-library-grid__count">
              {filteredVoices.length} {filteredVoices.length === 1 ? 'voice' : 'voices'}
            </div>
          </div>
          <Button
            variant="primary"
            size="sm"
            onClick={() => setIsUploadModalOpen(true)}
            className="voice-library-grid__upload-btn"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
              <path
                d="M12 5v14M5 12h14"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            Add Voice
          </Button>
        </div>

      <div className="voice-library-grid__filters">
        <Input
          type="search"
          placeholder="Search voices..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="voice-library-grid__search"
        />

        <div className="voice-library-grid__categories">
          {categories.map((category) => (
            <Button
              key={category.value}
              variant={selectedCategory === category.value ? 'primary' : 'outline'}
              size="sm"
              onClick={() => setSelectedCategory(category.value)}
            >
              {category.label}
            </Button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <div className="voice-library-grid__loading">
          <div className="spinner" />
          <p>Loading voices...</p>
        </div>
      ) : filteredVoices.length === 0 ? (
        <div className="voice-library-grid__empty">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none">
            <path
              d="M12 14a2 2 0 100-4 2 2 0 000 4z"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <path
              d="M17.5 12a5.5 5.5 0 11-11 0 5.5 5.5 0 0111 0z"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          <p>
            {searchQuery || selectedCategory !== 'all'
              ? 'No voices match your filters'
              : 'No voices available'}
          </p>
        </div>
      ) : (
        <div className="voice-library-grid__grid">
          {filteredVoices.map((voice) => (
            <VoiceTile
              key={voice.id}
              voice={voice}
              isSelected={selectedVoiceId === voice.id}
              isPlaying={playingVoiceId === voice.id}
              onSelect={() => onSelectVoice(voice.id)}
              onPreview={() => onPreviewVoice(voice.id)}
            />
          ))}
        </div>
      )}
    </Card>

    {/* Upload Voice Modal */}
    <Modal
      isOpen={isUploadModalOpen}
      onClose={handleCloseUploadModal}
      title="Add Voice to Library"
      size="md"
    >
      <div className="voice-upload-modal">
        {uploadError && (
          <div className="voice-upload-modal__error">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                clipRule="evenodd"
              />
            </svg>
            <span>{uploadError}</span>
          </div>
        )}

        <div className="voice-upload-modal__field">
          <label htmlFor="voice-name" className="voice-upload-modal__label">
            Voice Name <span className="voice-upload-modal__required">*</span>
          </label>
          <Input
            id="voice-name"
            type="text"
            placeholder="e.g., Professional Speaker, Character Voice"
            value={uploadName}
            onChange={(e) => setUploadName(e.target.value)}
            disabled={isUploading}
          />
        </div>

        <div className="voice-upload-modal__field">
          <label htmlFor="voice-description" className="voice-upload-modal__label">
            Description (Optional)
          </label>
          <textarea
            id="voice-description"
            placeholder="Add a description for this voice..."
            value={uploadDescription}
            onChange={(e) => setUploadDescription(e.target.value)}
            disabled={isUploading}
            className="voice-upload-modal__textarea"
            rows={3}
          />
        </div>

        <div className="voice-upload-modal__field">
          <label htmlFor="voice-audio" className="voice-upload-modal__label">
            Reference Audio <span className="voice-upload-modal__required">*</span>
          </label>
          <div className="voice-upload-modal__file-input">
            <input
              id="voice-audio"
              type="file"
              accept="audio/*"
              onChange={handleFileSelect}
              disabled={isUploading}
              className="voice-upload-modal__file-input-hidden"
            />
            <label htmlFor="voice-audio" className="voice-upload-modal__file-label">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                <path
                  d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
              {uploadFile ? uploadFile.name : 'Choose audio file'}
            </label>
          </div>
          <p className="voice-upload-modal__hint">
            Upload a clear audio sample (WAV, MP3, or other audio format)
          </p>
        </div>

        <div className="voice-upload-modal__actions">
          <Button variant="secondary" onClick={handleCloseUploadModal} disabled={isUploading}>
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={handleUploadVoice}
            disabled={isUploading || !uploadFile || !uploadName.trim()}
            loading={isUploading}
          >
            {isUploading ? 'Uploading...' : 'Add Voice'}
          </Button>
        </div>
      </div>
    </Modal>
    </>
  );
};
