/**
 * Settings Modal Component
 *
 * Application settings with offline mode toggle
 */

import { useEffect, useState } from 'react';
import { Modal } from '@/components/ui/Modal';
import { Button } from '@/components/ui/Button';
import { settingsService } from '@/services/settings.service';
import type { Settings as SettingsType } from '@/types/settings.types';
import './Settings.css';

interface SettingsProps {
  isOpen: boolean;
  onClose: () => void;
}

export const Settings: React.FC<SettingsProps> = ({ isOpen, onClose }) => {
  const [settings, setSettings] = useState<SettingsType | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [offlineMode, setOfflineMode] = useState(false);

  useEffect(() => {
    if (isOpen) {
      loadSettings();
    }
  }, [isOpen]);

  const loadSettings = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await settingsService.getSettings();
      setSettings(data);
      setOfflineMode(data.offline_mode);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      setLoading(true);
      setError(null);
      const updated = await settingsService.updateSettings({ offline_mode: offlineMode });
      setSettings(updated);
      onClose();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Settings" size="md">
      <div className="settings">
        {error && (
          <div className="settings__error">
            <svg className="settings__error-icon" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                clipRule="evenodd"
              />
            </svg>
            <span>{error}</span>
          </div>
        )}

        <div className="settings__section">
          <h3 className="settings__section-title">Model Configuration</h3>

          <div className="settings__option">
            <div className="settings__option-header">
              <label htmlFor="offline-mode" className="settings__label">
                Offline Mode
              </label>
              <label htmlFor="offline-mode" className="settings__toggle">
                <input
                  type="checkbox"
                  id="offline-mode"
                  checked={offlineMode}
                  onChange={(e) => setOfflineMode(e.target.checked)}
                  disabled={loading}
                  className="settings__toggle-input"
                />
                <span className="settings__toggle-slider" />
              </label>
            </div>
            <p className="settings__description">
              Use local models instead of downloading from the internet. Requires models to be
              downloaded to the models directory.
            </p>
          </div>

          {settings && (
            <div className="settings__info">
              <div className="settings__info-item">
                <span className="settings__info-label">Models Directory:</span>
                <code className="settings__info-value">{settings.models_dir}</code>
              </div>
              <div className="settings__info-item">
                <span className="settings__info-label">Local Models Available:</span>
                <span className={`settings__info-badge ${settings.has_local_models ? 'settings__info-badge--success' : 'settings__info-badge--warning'}`}>
                  {settings.has_local_models ? 'Yes' : 'No'}
                </span>
              </div>
            </div>
          )}
        </div>

        <div className="settings__actions">
          <Button variant="secondary" onClick={onClose} disabled={loading}>
            Cancel
          </Button>
          <Button variant="primary" onClick={handleSave} disabled={loading} loading={loading}>
            Save Settings
          </Button>
        </div>
      </div>
    </Modal>
  );
};
