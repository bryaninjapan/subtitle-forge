# AI Studio Prompts — Subtitle Forge React Frontend

餵給 AI Studio 的順序：一次一個 prompt，完成後再餵下一個。

---

## Prompt 1: 基礎檔案 (api.ts + types.ts)

```prompt
You are a senior React/TypeScript developer. Create two files for a subtitle processing desktop app.

### File 1: src/types.ts

```typescript
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
```

### File 2: src/api.ts

```typescript
import type {
  UploadResponse, PipelineResponse, PipelineParams,
  TaskProgress, HistoryEntry, OutputFolder,
  WaveformData, TimestampsData,
  AppSettings, ModelsResponse, ModelInfo,
  EndpointStatus, EndpointStartResponse,
} from './types';

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
  updateSettings: (data: Partial<AppSettings>) =>
    request<{status: string}>(`${BASE}/settings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),

  cancelTask: (taskId: string) =>
    request<{status: string}>(`${BASE}/cancel/${taskId}`, { method: 'POST' }),

  getModels: () => request<ModelsResponse>(`${BASE}/models/status`),
  downloadModel: (modelId: string) =>
    request<{status: string}>(`${BASE}/models/download/${modelId}`),

  startEndpoint: () => request<EndpointStartResponse>(`${BASE}/endpoint/start`, { method: 'POST' }),
  stopEndpoint: () => request<{status: string}>(`${BASE}/endpoint/stop`, { method: 'POST' }),
  getEndpointStatus: () => request<EndpointStatus>(`${BASE}/endpoint/status`),
};
```

Return ONLY the complete content of both files, nothing else.
```

---

## Prompt 2: CSS + App.tsx + Sidebar

```prompt
Create src/styles/global.css and src/App.tsx for a React dark-theme desktop app.

### global.css

Use these CSS variables:
--bg-primary: #0f172a (slate-900)
--bg-card: #1e293b (slate-800)
--bg-hover: #334155 (slate-700)
--bg-active: #1e3a5f
--text-primary: #e2e8f0 (slate-200)
--text-secondary: #94a3b8 (slate-400)
--text-muted: #64748b (slate-500)
--accent: #3b82f6 (blue-500)
--accent-hover: #2563eb
--success: #22c55e
--warning: #f59e0b
--error: #ef4444
--border: #334155
--sidebar-width: 200px
--radius: 8px

Reset margins/padding/box-sizing. Font: -apple-system, BlinkMacSystemFont.

### App.tsx

- No react-router. Use useState<Page>('audio') for routing.
- Sidebar on the left (200px wide) with 6 nav items:
  音檔 (audio), 批次 (batch), 錄製 (record), 端點 (endpoint), 模型 (models), 設定 (settings)
- Active nav item has accent background
- Main content area on the right
- Import and render 6 page components (AudioFile, Batch, Record, Endpoint, ModelManage, Settings)
- Page components can be placeholder divs for now: <div>音檔</div>
- Dark background: var(--bg-primary)

Return both files fully.
```

---

## Prompt 3: 音檔轉字幕 (AudioFile.tsx)

```prompt
Create src/pages/AudioFile.tsx — the main audio transcription page.

### Layout
```
上傳區 (顯示檔名 + 移除按鈕 / 未選檔時顯示選擇檔案按鈕)
[▶ 開始轉換]  [📂 輸出資料夾]  [💾 字幕存檔]   ← 按鈕列
語言: [自動 ▼]   說話者分離: [○]   人數: [自動 ▼]   時間軸對齊: [●]
辨識提示 (可選) textarea + [讀入TXT...] 按鈕
████████████████████░░░░  完成  100%     ← 進度條
辨識結果: 波形顯示 + 字詞區塊 + 播放控制 [▶][■][🎤]
00:01 → 00:03   週末的早晨     ← 字幕列表
00:03 → 00:05   睡到自然醒
```

### Behavior
- Upload file → api.upload or api.runPipeline → get taskId
- Poll api.getProgress(taskId) every 2s → update progress bar
- When stage === 'done': fetch api.getWaveform(taskId) + api.getTimestamps(taskId)
- Waveform: render peaks as a bar chart (simple colored bars, each bar height = peak value * 100px)
- Timestamps: render word blocks (each word in a rounded box, click to jump)
- Subtitle list: render SRT entries (timestamp range + text)
- Use CSS variables for styling (var(--bg-card), var(--accent), etc.)
- Handle loading state, error state, empty state (no file selected)
- Import { api } from '../api'
```

---

## Prompt 4: 批次辨識 (Batch.tsx)

```prompt
Create src/pages/Batch.tsx — batch processing page.

### Layout
```
[＋ 加入檔案]  [▶ 全部開始]  說話者分離: [○]  人數: [自動 ▼]   0 / 3 完成

夏天這一站.mp3  ████████░░░░  60%  轉換中  [⋮]
月宮・換裝夢遊  ░░░░░░░░░░░░   0%  待處理  [⋮]
```

### Behavior
- Add files button → multiple file selection
- Start all → call api.runPipeline for each file with batch flag
- Poll api.getProgress for all tasks every 2s
- Each task row: filename, progress bar (stage-colored), status label, three-dot menu
- Status: 待處理 / 轉換中 / 完成 / 失敗 (colored badges)
- Count completed / total at top
- Handle empty state (no files added)
```

---

## Prompt 5: 錄製轉換 (Record.tsx) — 簡化版

```prompt
Create src/pages/Record.tsx — a simplified recording page placeholder.

### Layout
```
錄製轉換
麥克風: [預設麥克風 ▼]  [重新整理]  語言: [自動 ▼]
┌──────────────────────┐
│       [ 🎤 ]         │  ← large mic button
│        00:00         │  ← timer
│  錄製轉換：說明文字    │
└──────────────────────┘
即時字幕
┌──────────────────────┐
│  開始錄音後會出現...   │
└──────────────────────┘
```

### Note
This page requires Web Audio API + MediaRecorder which is complex.
For now create a static UI placeholder. The recording functionality will be added later.
```

---

## Prompt 6: 端點服務 (Endpoint.tsx)

```prompt
Create src/pages/Endpoint.tsx — endpoint service page.

### Layout
```
端點服務

[●] 啟動服務

上傳網頁               存取金鑰
┌──────────┐         ┌────────────┐
│ QR Code  │         │ ●●●●●●●●●  │
│ (黑色方塊)│         │ [顯示] [重設]│
│          │         │            │
│ URL: ... │         │            │
│ [複製]    │         │            │
└──────────┘         └────────────┘

對外臨時網址 (Cloudflare)
[○] 對外   ⚠️ 網址含金鑰，用完請關閉
```

### Behavior
- "啟動服務" toggle → call api.startEndpoint() / api.stopEndpoint()
- When started: show QR code placeholder (black square), URL, access key
- "複製" button copies URL to clipboard
- "顯示" toggle shows/hides the access key
- "重設" generates a new key (call stop then start)
- Cloudflare toggle is UI only (functionality TBD)
- Poll api.getEndpointStatus() on mount to check if running
```

---

## Prompt 7: 模型管理 (ModelManage.tsx)

```prompt
Create src/pages/ModelManage.tsx — model management page.

### Layout
```
模型與裝置
系統自檢  核心就緒 · 1 項將於啟用時自動下載  [重新檢查]

Qwen3-ASR-0.6B
  ● 已下載 (1,200 MB)

Qwen3-ForcedAligner-0.6B
  ○ 未下載  [下載]
```

### Behavior
- Fetch api.getModels() on mount
- Each model as a card: name, status icon (● downloaded / ○ not / ◐ downloading), size
- "下載" button → call api.downloadModel(id)
- Download progress from api.getProgress (task_id = 'download_{id}')
- "重新檢查" → refetch models
- Handle loading/error states
```

---

## Prompt 8: 設定 (Settings.tsx)

```prompt
Create src/pages/Settings.tsx — settings page.

### Layout
```
設定

介面縮放   [══════●══════]  100%
輸出格式   [SRT ●] [純文字]
VAD 靈敏度 [════●══════]  0.35
簡繁轉換   [關閉] [台灣用語 ●] [標準]
外觀主題   [淺色 ●] [深色] [跟隨系統]
FFmpeg 路徑 [(留空=自動偵測)]
```

### Behavior
- Fetch api.getSettings() on mount
- Each setting is a form control bound to state
- On change, call api.updateSettings() (debounced 1s for sliders)
- Sliders: use range input
- Toggle groups: styled button groups (selected one has accent bg)
- Handle loading/error states
```
