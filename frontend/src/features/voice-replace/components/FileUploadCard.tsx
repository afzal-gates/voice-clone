import React, { useCallback, useState } from 'react';
import { Card } from '@/components';
import { Button } from '@/components';
import { useFileUpload } from '../hooks/useFileUpload';
import { ProgressBar } from '@/components';

interface FileUploadCardProps {
  onUploadSuccess: (jobId: string) => void;
}

export const FileUploadCard: React.FC<FileUploadCardProps> = ({ onUploadSuccess }) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const { uploading, progress, error, uploadFile, validateFile } = useFileUpload({
    onSuccess: onUploadSuccess,
    maxSizeMB: 500
  });

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(false);

      const files = Array.from(e.dataTransfer.files);
      if (files.length > 0) {
        const file = files[0];
        const validationError = validateFile(file);
        if (!validationError) {
          setSelectedFile(file);
        }
      }
    },
    [validateFile]
  );

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files;
      if (files && files.length > 0) {
        const file = files[0];
        const validationError = validateFile(file);
        if (!validationError) {
          setSelectedFile(file);
        }
      }
    },
    [validateFile]
  );

  const handleUpload = useCallback(() => {
    if (selectedFile) {
      uploadFile(selectedFile);
    }
  }, [selectedFile, uploadFile]);

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  return (
    <Card>
      <div className="file-upload-card">
        <h2 className="file-upload-card__title">Upload Media File</h2>
        <p className="file-upload-card__description">
          Upload a video or audio file to replace voices
        </p>

        <div
          className={`file-upload-card__dropzone ${isDragging ? 'file-upload-card__dropzone--dragging' : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          <div className="file-upload-card__dropzone-content">
            <svg
              className="file-upload-card__icon"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
              />
            </svg>

            {selectedFile ? (
              <div className="file-upload-card__file-info">
                <p className="file-upload-card__filename">{selectedFile.name}</p>
                <p className="file-upload-card__filesize">{formatFileSize(selectedFile.size)}</p>
              </div>
            ) : (
              <>
                <p className="file-upload-card__prompt">
                  <strong>Click to upload</strong> or drag and drop
                </p>
                <p className="file-upload-card__hint">MP4, AVI, MKV, MP3, WAV (max 500MB)</p>
              </>
            )}

            <input
              type="file"
              className="file-upload-card__input"
              accept="video/*,audio/*"
              onChange={handleFileSelect}
              disabled={uploading}
            />
          </div>
        </div>

        {uploading && progress && (
          <div className="file-upload-card__progress">
            <ProgressBar progress={progress.percentage} />
            <p className="file-upload-card__progress-text">
              Uploading: {progress.percentage}% ({formatFileSize(progress.loaded)} / {formatFileSize(progress.total)})
            </p>
          </div>
        )}

        {error && (
          <div className="file-upload-card__error">
            <svg
              className="file-upload-card__error-icon"
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

        <div className="file-upload-card__actions">
          <Button
            variant="primary"
            onClick={handleUpload}
            disabled={!selectedFile || uploading}
            fullWidth
          >
            {uploading ? 'Uploading...' : 'Start Processing'}
          </Button>
        </div>
      </div>
    </Card>
  );
};
