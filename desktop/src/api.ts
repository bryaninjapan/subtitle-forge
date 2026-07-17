import type { UploadResponse, PipelineResponse, PipelineParams, TaskProgress, HistoryEntry, OutputFolder, WaveformData, TimestampsData, AppSettings, ModelsResponse, EndpointStatus, EndpointStartResponse } from './types';

const BASE = 'http://localhost:5000';

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, options);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(err.error || `HTTP ${res.status}`);
  }
  return res.json();
}

export const api = {
  upload: (file: File) => {
    const form = new FormData();
    form.append('file', file);
    return request<UploadResponse>(`${BASE}/upload`, { method: 'POST', body: form });
  },
  runPipeline: (file: File, params?: PipelineParams) => {
    const form = new FormData();
    form.append('file', file);
    if (params?.translate) form.append('translate', 'true');
    if (params?.notes) form.append('notes', 'true');
    if (params?.chapters) form.append('chapters', 'true');
    if (params?.prompt) form.append('prompt', params.prompt);
    return request<PipelineResponse>(`${BASE}/pipeline`, { method: 'POST', body: form });
  },
  getProgress: () => request<Record<string, TaskProgress>>(`${BASE}/progress`),
  getHistory: () => request<HistoryEntry[]>(`${BASE}/history`),
  getOutputs: () => request<OutputFolder[]>(`${BASE}/outputs`),
  getWaveform: (taskId: string) => request<WaveformData>(`${BASE}/waveform/${taskId}`),
  getTimestamps: (taskId: string) => request<TimestampsData>(`${BASE}/timestamps/${taskId}`),
  getSettings: () => request<AppSettings>(`${BASE}/settings`),
  updateSettings: (data: Partial<AppSettings>) => request<{status: string}>(`${BASE}/settings`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }),
  cancelTask: (taskId: string) => request<{status: string}>(`${BASE}/cancel/${taskId}`, { method: 'POST' }),
  getModels: () => request<ModelsResponse>(`${BASE}/models/status`),
  downloadModel: (modelId: string) => request<{status: string}>(`${BASE}/models/download/${modelId}`),
  startEndpoint: () => request<EndpointStartResponse>(`${BASE}/endpoint/start`, { method: 'POST' }),
  stopEndpoint: () => request<{status: string}>(`${BASE}/endpoint/stop`, { method: 'POST' }),
  getEndpointStatus: () => request<EndpointStatus>(`${BASE}/endpoint/status`),
};
