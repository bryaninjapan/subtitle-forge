export interface TaskProgress {
  file: string;
  pct: number;
  stage: 'queued' | 'extracting' | 'initializing' | 'processing' | 'done' | 'error' | 'cancelled' | 'downloading';
  message: string;
}

export interface UploadResponse {
  task_id: string;
  file: string;
  status: string;
}

export interface PipelineParams {
  translate?: boolean;
  notes?: boolean;
  chapters?: boolean;
  prompt?: string;
}

export interface PipelineResponse extends UploadResponse {
  translate: boolean;
  notes: boolean;
  chapters: boolean;
}

export interface HistoryEntry {
  timestamp: string;
  category: string;
  detail: string;
  cost: number;
}

export interface OutputFolder {
  name: string;
  files: string[];
}

export interface WaveformData {
  peaks: number[];
  num_peaks: number;
}

export interface WordTimestamp {
  text: string;
  start: number;
  end: number;
}

export interface TimestampsData {
  words: WordTimestamp[];
  language: string;
}

export interface PipelineSettings {
  asr_backend?: 'local' | 'api';
  asr_model?: string;
  asr_diarize?: boolean;
  asr_hotwords?: boolean;
  asr_concurrent?: number;
  vad_threshold?: number;
  cc_conversion?: 'off' | 'standard' | 'taiwan';
  translate?: boolean;
  study_notes?: boolean;
  chapters?: boolean;
  [key: string]: unknown;
}

export interface AppSettings {
  domain?: string;
  pipeline?: PipelineSettings;
  [key: string]: unknown;
}

export interface ModelInfo {
  id: string;
  repo: string;
  status: 'downloaded' | 'not_downloaded' | 'downloading';
  size_mb: number;
}

export interface ModelsResponse {
  models: ModelInfo[];
}

export interface EndpointStatus {
  running: boolean;
  port: number | null;
  url: string | null;
  key: string | null;
}

export interface EndpointStartResponse {
  status: string;
  port: number;
  url: string;
  key: string;
}

export type Page = 'audio' | 'batch' | 'record' | 'endpoint' | 'models' | 'settings';
