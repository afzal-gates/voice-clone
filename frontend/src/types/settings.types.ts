export interface Settings {
  offline_mode: boolean;
  models_dir: string;
  has_local_models: boolean;
}

export interface SettingsUpdate {
  offline_mode: boolean;
}

export interface SettingsResponse {
  offline_mode: boolean;
  models_dir: string;
  has_local_models: boolean;
}
