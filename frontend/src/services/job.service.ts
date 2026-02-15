import type {
  JobResponse,
  JobDetailResponse,
  VoiceAssignment,
  DownloadOptions,
  UploadProgress,
  Voice
} from '@/types/job.types';
import { InputType } from '@/types/job.types';

class JobService {
  private baseURL = '/api';

  async uploadFile(
    file: File,
    inputType?: InputType,
    onProgress?: (progress: UploadProgress) => void
  ): Promise<JobResponse> {
    const formData = new FormData();
    formData.append('file', file);

    if (inputType) {
      formData.append('input_type', inputType);
    }

    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();

      xhr.upload.addEventListener('progress', (event) => {
        if (event.lengthComputable && onProgress) {
          onProgress({
            loaded: event.loaded,
            total: event.total,
            percentage: Math.round((event.loaded / event.total) * 100)
          });
        }
      });

      xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            const response = JSON.parse(xhr.responseText);
            resolve(response);
          } catch (error) {
            reject(new Error('Invalid response format'));
          }
        } else {
          try {
            const error = JSON.parse(xhr.responseText);
            reject(new Error(error.detail || 'Upload failed'));
          } catch {
            reject(new Error(`Upload failed: ${xhr.statusText}`));
          }
        }
      });

      xhr.addEventListener('error', () => {
        reject(new Error('Network error during upload'));
      });

      xhr.addEventListener('abort', () => {
        reject(new Error('Upload cancelled'));
      });

      xhr.open('POST', `${this.baseURL}/upload`);
      xhr.send(formData);
    });
  }

  async getJob(jobId: string): Promise<JobDetailResponse> {
    const response = await fetch(`${this.baseURL}/jobs/${jobId}`);

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to fetch job' }));
      throw new Error(error.detail || 'Failed to fetch job');
    }

    return response.json();
  }

  async getAllJobs(): Promise<JobDetailResponse[]> {
    const response = await fetch(`${this.baseURL}/jobs`);

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to fetch jobs' }));
      throw new Error(error.detail || 'Failed to fetch jobs');
    }

    return response.json();
  }

  async assignVoices(jobId: string, assignments: VoiceAssignment[]): Promise<void> {
    const response = await fetch(`${this.baseURL}/jobs/${jobId}/assign-voices`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ assignments })
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to assign voices' }));
      throw new Error(error.detail || 'Failed to assign voices');
    }
  }

  async downloadResult(jobId: string, options: DownloadOptions): Promise<Blob> {
    const response = await fetch(
      `${this.baseURL}/jobs/${jobId}/download?format=${options.format}`
    );

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to download result' }));
      throw new Error(error.detail || 'Failed to download result');
    }

    return response.blob();
  }

  async deleteJob(jobId: string): Promise<void> {
    const response = await fetch(`${this.baseURL}/jobs/${jobId}`, {
      method: 'DELETE'
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to delete job' }));
      throw new Error(error.detail || 'Failed to delete job');
    }
  }

  async getVoices(): Promise<Voice[]> {
    const response = await fetch(`${this.baseURL}/voices`);

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to fetch voices' }));
      throw new Error(error.detail || 'Failed to fetch voices');
    }

    return response.json();
  }

  downloadBlob(blob: Blob, filename: string): void {
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }
}

export const jobService = new JobService();
