import type { Settings, SettingsUpdate, SettingsResponse } from '../types/settings.types';

class SettingsService {
  private baseURL = '/api';

  async getSettings(): Promise<Settings> {
    const response = await fetch(`${this.baseURL}/settings`);

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to fetch settings' }));
      throw new Error(error.detail || 'Failed to fetch settings');
    }

    const data: SettingsResponse = await response.json();
    return {
      offline_mode: data.offline_mode,
      models_dir: data.models_dir,
      has_local_models: data.has_local_models
    };
  }

  async updateSettings(update: SettingsUpdate): Promise<Settings> {
    const formData = new FormData();
    formData.append('offline_mode', String(update.offline_mode));

    const response = await fetch(`${this.baseURL}/settings`, {
      method: 'POST',
      body: formData
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to update settings' }));
      throw new Error(error.detail || 'Failed to update settings');
    }

    const data: SettingsResponse = await response.json();
    return {
      offline_mode: data.offline_mode,
      models_dir: data.models_dir,
      has_local_models: data.has_local_models
    };
  }
}

export const settingsService = new SettingsService();
