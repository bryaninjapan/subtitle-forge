# Subtitle Forge — React Frontend Specification

## 架構

6 個頁面 + 側邊導航，所有頁面透過 HTTP call `localhost:5000`。

```
desktop/src/
├── api.ts                  # API 封裝層
├── types.ts                # TypeScript 型別
├── App.tsx                 # 側邊導航 + 頁面路由
├── main.tsx                # React 入口
│
├── pages/
│   ├── AudioFile.tsx       # 頁面 1: 音檔轉字幕
│   ├── Batch.tsx           # 頁面 2: 批次辨識
│   ├── Record.tsx          # 頁面 3: 錄製轉換
│   ├── Endpoint.tsx        # 頁面 4: 端點服務
│   ├── ModelManage.tsx     # 頁面 5: 模型與裝置
│   └── Settings.tsx        # 頁面 6: 設定
│
├── hooks/
│   ├── useProgress.ts      # 輪詢 /progress
│   ├── useSettings.ts      # 讀寫 settings.yaml
│   └── useEndpoint.ts      # 端點服務控制
│
└── styles/
    └── global.css          # 暗色主題
```

## Component Tree

```
<App>
  ├── <Sidebar>                     # 左側導航列
  │   ├── 圖示 + 標題
  │   ├── NavItem (音檔)            # 當前頁面高亮
  │   ├── NavItem (批次)
  │   ├── NavItem (錄製)
  │   ├── NavItem (端點)
  │   ├── NavItem (模型)
  │   ├── NavItem (設定)
  │   └── 狀態列 (模型已就緒)
  │
  └── <MainContent>                 # 右側內容區
      │
      ├── [route=/audio]  <AudioFile>
      │   ├── 上傳區 (檔案名稱 + 移除按鈕)
      │   ├── 按鈕列 (開始轉換 / 輸出資料夾 / 字幕存檔)
      │   ├── 設定列 (語言 / 說話者分離 / 時間軸對齊)
      │   ├── 辨識提示 textarea
      │   ├── 進度條
      │   ├── 辨識結果
      │   │   ├── 波形顯示
      │   │   ├── 字詞區塊
      │   │   └── 播放控制
      │   └── 字幕列表
      │
      ├── [route=/batch]  <Batch>
      │   ├── 控制列 (加入檔案 / 全部開始 / toggle)
      │   └── 任務列表
      │       └── TaskRow (檔名 / 進度條 / 狀態 / 選單)
      │
      ├── [route=/record]  <Record>
      │   ├── 麥克風選取
      │   ├── 錄音按鈕 (大圓形)
      │   ├── 計時器
      │   └── 即時字幕
      │
      ├── [route=/endpoint]  <Endpoint>
      │   ├── 服務 toggle
      │   ├── QR Code
      │   ├── URL + 金鑰
      │   └── Cloudflare toggle
      │
      ├── [route=/models]  <ModelManage>
      │   ├── 系統自檢
      │   └── 模型卡片列表
      │       └── ModelCard (名稱 / 狀態 / 大小)
      │
      └── [route=/settings]  <Settings>
          └── 設定表單 (縮放 / 格式 / VAD / 主題 / ...)
```

## Page Routing

```
Path          Page            Sidebar icon
─────────────────────────────────────────────
/             AudioFile        音檔 (default)
/batch        Batch            批次
/record       Record           錄製
/endpoint     Endpoint         端點
/models       ModelManage      模型
/settings     Settings         設定
```

實作方式：不用 react-router，用簡單的 state-based routing：

```tsx
// App.tsx
const [page, setPage] = useState<Page>('audio');
// 點側邊欄 → setPage('batch') → 渲染對應元件
```

## Data Flow

```
┌──────────┐  fetch()  ┌───────────┐  state  ┌─────────────┐
│ server.py │ ←──────→ │ api.ts    │ ──────→ │ React Page  │
│ :5000     │          │ (HTTP)    │         │ Component   │
└──────────┘          └───────────┘         └─────────────┘
                            │                      │
                            │ 回傳 JSON             │ 渲染 UI
                            ▼                      ▼
                    打字稿型別 (types.ts)     DOM + CSS
```

具體流程：
1. 每個 page component 在 `useEffect` 中 call `api.getXXX()`
2. `api.ts` 用 `fetch()` call `localhost:5000`
3. 回傳 JSON → setState → 重新渲染
4. 需要輪詢的 page (AudioFile, Batch) 用 `setInterval` 每 2s 更新

## State Management

不需要全域 state library (Redux/Zustand)。每個 page 自己管自己的 state：

```tsx
// AudioFile.tsx — 範例
function AudioFile() {
  const [file, setFile] = useState<File | null>(null);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [progress, setProgress] = useState<TaskProgress | null>(null);
  const [timestamps, setTimestamps] = useState<WordTimestamp[]>([]);
  const [peaks, setPeaks] = useState<number[]>([]);
  const [settings, setSettings] = useState({
    language: 'auto',
    diarize: false,
    numSpeakers: 'auto',
    timelineAlign: true,
  });

  // 上傳
  async function handleUpload(file: File) { ... }
  
  // 輪詢進度
  useEffect(() => {
    if (!taskId) return;
    const interval = setInterval(async () => {
      const p = await api.getProgress();
      if (p[taskId]) setProgress(p[taskId]);
    }, 2000);
    return () => clearInterval(interval);
  }, [taskId]);
  
  // 載入波形 + 時間戳
  useEffect(() => {
    if (!taskId || progress?.stage !== 'done') return;
    api.getWaveform(taskId).then(d => setPeaks(d.peaks));
    api.getTimestamps(taskId).then(d => setTimestamps(d.words));
  }, [taskId, progress]);
  
  // ... render
}
```

## Hook 定義

### useProgress(taskId)

```tsx
function useProgress(taskId: string | null) {
  const [progress, setProgress] = useState<TaskProgress | null>(null);

  useEffect(() => {
    if (!taskId) return;
    const interval = setInterval(async () => {
      const data = await api.getProgress();
      if (data[taskId]) setProgress(data[taskId]);
    }, 2000);
    return () => clearInterval(interval);
  }, [taskId]);

  return progress;
}
```

### useSettings()

```tsx
function useSettings() {
  const [settings, setSettings] = useState<AppSettings | null>(null);

  useEffect(() => {
    api.getSettings().then(setSettings);
  }, []);

  const update = async (patch: Partial<AppSettings>) => {
    await api.updateSettings(patch);
    setSettings(prev => prev ? { ...prev, ...patch } : null);
  };

  return { settings, update };
}
```

### useEndpoint()

```tsx
function useEndpoint() {
  const [status, setStatus] = useState<EndpointStatus | null>(null);

  const start = async () => {
    const data = await api.startEndpoint();
    setStatus(data);
    return data;
  };

  const stop = async () => {
    await api.stopEndpoint();
    setStatus(null);
  };

  const refresh = async () => {
    const data = await api.getEndpointStatus();
    setStatus(data);
  };

  return { status, start, stop, refresh };
}
```

## TypeScript Types (`types.ts`)

```typescript
// ── Task / Progress ──
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

// ── Pipeline ──
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

// ── History ──
export interface HistoryEntry {
  timestamp: string;
  category: string;
  detail: string;
  cost: number;
}

// ── Outputs ──
export interface OutputFolder {
  name: string;
  files: string[];
}

// ── Waveform & Timestamps ──
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

// ── Settings ──
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

// ── Models ──
export interface ModelInfo {
  id: string;
  repo: string;
  status: 'downloaded' | 'not_downloaded' | 'downloading';
  size_mb: number;
}

export interface ModelsResponse {
  models: ModelInfo[];
}

// ── Endpoint ──
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

// ── Components Props ──
export type Page = 'audio' | 'batch' | 'record' | 'endpoint' | 'models' | 'settings';

export interface NavItemProps {
  icon: string;
  label: string;
  page: Page;
  active: boolean;
  onClick: (page: Page) => void;
}

export interface TaskRowProps {
  file: string;
  progress: TaskProgress | null;
  onCancel: (taskId: string) => void;
}

export interface ModelCardProps {
  model: ModelInfo;
  onDownload: (modelId: string) => void;
}
```


## Complete `api.ts`

```typescript
// api.ts — Single API layer. All pages import from here.
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
  // ── Upload ──
  upload: (file: File) => {
    const form = new FormData();
    form.append('file', file);
    return request<UploadResponse>(`${BASE}/upload`, { method: 'POST', body: form });
  },

  // ── Pipeline ──
  runPipeline: (file: File, params?: PipelineParams) => {
    const form = new FormData();
    form.append('file', file);
    if (params?.translate) form.append('translate', 'true');
    if (params?.notes) form.append('notes', 'true');
    if (params?.chapters) form.append('chapters', 'true');
    if (params?.prompt) form.append('prompt', params.prompt);
    return request<PipelineResponse>(`${BASE}/pipeline`, { method: 'POST', body: form });
  },

  // ── Progress ──
  getProgress: () =>
    request<Record<string, TaskProgress>>(`${BASE}/progress`),

  // ── History ──
  getHistory: () =>
    request<HistoryEntry[]>(`${BASE}/history`),

  // ── Outputs ──
  getOutputs: () =>
    request<OutputFolder[]>(`${BASE}/outputs`),

  // ── Waveform ──
  getWaveform: (taskId: string) =>
    request<WaveformData>(`${BASE}/waveform/${taskId}`),

  // ── Timestamps ──
  getTimestamps: (taskId: string) =>
    request<TimestampsData>(`${BASE}/timestamps/${taskId}`),

  // ── Settings ──
  getSettings: () =>
    request<AppSettings>(`${BASE}/settings`),

  updateSettings: (data: Partial<AppSettings>) =>
    request<{status: string}>(`${BASE}/settings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),

  // ── Cancel ──
  cancelTask: (taskId: string) =>
    request<{status: string}>(`${BASE}/cancel/${taskId}`, { method: 'POST' }),

  // ── Models ──
  getModels: () =>
    request<ModelsResponse>(`${BASE}/models/status`),

  downloadModel: (modelId: string) =>
    request<{status: string}>(`${BASE}/models/download/${modelId}`),

  // ── Endpoint ──
  startEndpoint: () =>
    request<EndpointStartResponse>(`${BASE}/endpoint/start`, { method: 'POST' }),

  stopEndpoint: () =>
    request<{status: string}>(`${BASE}/endpoint/stop`, { method: 'POST' }),

  getEndpointStatus: () =>
    request<EndpointStatus>(`${BASE}/endpoint/status`),
};
```


## Error & Loading Patterns

每個 page component 遵循這三種狀態：

```tsx
function AudioFile() {
  // 1. Loading: 初始資料載入中
  if (isLoading) return <LoadingSpinner />;

  // 2. Error: API 失敗
  if (error) return <ErrorBanner message={error} onRetry={retry} />;

  // 3. Empty: 無資料
  if (!file && !taskId) return <EmptyState message="選擇音檔開始轉換" />;

  // 4. Normal: 正常顯示
  return <div>...</div>;
}
```


## CSS Variables (`styles/global.css`)

```css
:root {
  --bg-primary: #0f172a;       /* slate-900 */
  --bg-card: #1e293b;          /* slate-800 */
  --bg-hover: #334155;         /* slate-700 */
  --bg-active: #1e3a5f;        /* blue-900 */
  --text-primary: #e2e8f0;     /* slate-200 */
  --text-secondary: #94a3b8;   /* slate-400 */
  --text-muted: #64748b;       /* slate-500 */
  --accent: #3b82f6;           /* blue-500 */
  --accent-hover: #2563eb;     /* blue-600 */
  --success: #22c55e;          /* green-500 */
  --warning: #f59e0b;          /* amber-500 */
  --error: #ef4444;            /* red-500 */
  --border: #334155;           /* slate-700 */
  --sidebar-width: 200px;
  --header-height: 48px;
  --radius: 8px;
  --radius-sm: 4px;
}

* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background: var(--bg-primary);
  color: var(--text-primary);
}
```


## 頁面規格

### P1: 音檔轉字幕 (AudioFile.tsx)

單一音檔上傳、轉錄、檢視結果：

```
┌─ 上傳區 ──────────────────────────────────────┐
│  夏天這一站.mp3  (3.1 MB)           [×]       │ ← 選檔後顯示檔名
│  [選擇檔案]                                      │ ← 未選檔時顯示
└────────────────────────────────────────────────┘

[▶ 開始轉換]  [📂 輸出資料夾]  [💾 字幕存檔]     ← 按鈕列

語言: [自動 ▼]   說話者分離: [○]   人數: [自動 ▼]
時間軸對齊: [●]

辨識提示（可選）
┌──────────────────────────────────────────────┐
│  貼入歌詞、關鍵字或背景說明...                  │
│                               [讀入TXT...]    │
└──────────────────────────────────────────────┘

████████████████████░░░░  完成  100%            ← 進度條

┌── 辨識結果 ──────────────────────────────────┐
│  [=====波形=====]        01:10                │
│  週末 窗外 花 黃 有 別 我 每                  │ ← 字詞區塊
│  [▶] [■] [🎤]  點波形/字幕可跳播              │ ← 播放控制
└──────────────────────────────────────────────┘

00:01 → 00:03   週末的早晨                         ← 字幕列表
00:03 → 00:05   睡到自然醒
```

**States**:
- 未上傳: 顯示「選擇檔案」按鈕
- 已上傳: 顯示檔名 + 檔案大小 + [×] 移除
- 轉換中: 按鈕列置灰，進度條動畫
- 完成: 顯示波形 + 字詞區塊 + 字幕列表

**API calls**:
- `POST /upload` (上傳檔案)
- `GET /progress` (輪詢進度)
- `GET /outputs/:name/:file` (下載字幕)

---

### P2: 批次辨識 (Batch.tsx)

多檔批次處理：

```
批次辨識

[＋ 加入檔案]  [▶ 全部開始]  說話者分離: [○]  人數: [自動 ▼]   0 / 3 完成

夏天這一站.mp3      ████████████░░░░  60%  轉換中  [⋮]
月宮・換裝夢遊.mp3   ░░░░░░░░░░░░░░   0%  待處理  [⋮]
華裳夢遊.mp3        ░░░░░░░░░░░░░░   0%  待處理  [⋮]
```

**States**:
- 無檔案: 空列表 + 「加入檔案」按鈕
- 佇列中: 顯示進度條 + 狀態標籤 (待處理/轉換中/完成/失敗)
- 全部完成: 按鈕變成「全部清除」

**API calls**:
- `POST /upload` (每個檔案)
- `GET /progress` (輪詢所有 task)
- `POST /cancel/:id` (取消單一任務)

---

### P3: 錄製轉換 (Record.tsx)

即時麥克風錄音轉文字：

```
錄製轉換

麥克風: [預設麥克風 ▼]  [重新整理]  語言: [自動 ▼]

┌──────────────────────────────────────┐
│                                      │
│           [ 🎤 ]                     │ ← 大圓形按鈕
│            00:00                     │
│                                      │
│  錄製轉換：偵測到說話停頓時才辨識...    │
└──────────────────────────────────────┘

即時字幕
即時存檔: [○]          [清除]  [儲存字幕]

┌──────────────────────────────────────┐
│  開始錄音後，辨識結果會逐段出現...      │
└──────────────────────────────────────┘
```

**States**:
- 未開始: 顯示大麥克風按鈕 + 說明文字
- 錄音中: 按鈕變紅色脈動，計時器跑
- 暫停: 保留已辨識文字

**API**: 即時錄音不走 HTTP，需用 MediaRecorder + WebSocket 或 file upload。

---

### P4: 端點服務 (Endpoint.tsx)

讓手機或其他裝置上傳音檔：

```
OpenAI 相容轉錄服務

[●] 啟動服務

上傳網頁                    存取金鑰
┌──────────────────┐        ┌────────┐
│ [QR Code]        │        │ ●●●●●● │
│ http://192.168.. │        │[顯示]   │
│ [複製]           │        │[重設]   │
└──────────────────┘        └────────┘

對外臨時網址 (Cloudflare)
[○] 對外   ⚠️ 網址含金鑰，用完請關閉
```

**States**:
- 未啟動: 灰色 toggle，無 QR code
- 啟動: 顯示 QR code + URL + key
- 對外啟用: Cloudflare tunnel

**API calls**:
- `POST /endpoint/start` (啟動服務)
- `POST /endpoint/stop` (停止)
- `GET /endpoint/status` (取得 URL + QR code data)

---

### P5: 模型與裝置 (ModelManage.tsx)

顯示各 ASR backend 的模型下載狀態：

```
系統自檢  核心就緒 · 1 項將於啟用時自動下載  [重新檢查]

Qwen · OpenVINO (CPU)
  ASR 模型 (0.6B)     ● 已下載
  語音分段 VAD         ● 已內建
  時間軸對齊 FA        ● 已下載
  說話者分離           ● 已下載

CRISPASR (Vulkan)
  CrispASR 核心        ● 使用中
  Whisper 模型 (Q4)    ○ 未下載 (啟用時下載)
  Qwen3-ASR-1.7B      ● 已下載

推理核心
  ● Qwen (5 種模型可選)
  ○ Whisper/Breeze (3 種模型可選)

模型: [Qwen3-ASR-0.6B ▼]  GPU: [Auto ▼]
```

**States**:
- 每個模型有狀態：已下載 / 未下載 / 下載中 / 失敗
- 下載中顯示進度條

**API calls**:
- `GET /models/status` (查詢所有模型狀態)
- `POST /models/download/:name` (下載模型)
- `POST /models/recheck` (重新檢查)

---

### P6: 設定 (Settings.tsx)

應用程式偏好設定，類似參考工具的設定頁：

```
設定

介面縮放        [══════●══════]  100%

輸出格式        [SRT 字幕 ●] [純文字]

語音偵測靈敏度  [════●══════]  0.35

每段最長秒數    [════●══════]  30s

簡繁詞彙轉換    [關閉] [台灣用語 ●] [標準]

HuggingFace 鏡像  [hf-mirror.com]

FFmpeg 路徑       [(留空=自動偵測)]

外觀主題        [淺色 ●] [深色] [跟隨系統]

介面語言        [繁體中文 ▼]
```

**States**: 所有設定即時存檔（onChange → POST /settings）

**API calls**:
- `GET /settings` (讀取)
- `POST /settings` (寫入)

---

## API Contract

All endpoints are on `http://localhost:5000`.

### Upload & Pipeline

```http
POST /upload
Content-Type: multipart/form-data
file: <binary>

→ {"task_id", "file", "status"}
```

```http
POST /pipeline
Content-Type: multipart/form-data
file: <binary>
translate: "true"|"false"
notes: "true"|"false"
chapters: "true"|"false"
prompt: "optional hint text"

→ {"task_id", "file", "status", "translate", "notes", "chapters"}
```

### Progress & History

```http
GET /progress
→ {[task_id]: {file, pct, stage, message}}

GET /history
→ [{timestamp, category, detail, cost}]
```

### Media & Waveform

```http
GET /audio/<path>
→ audio/video file (Range header for seeking)

GET /waveform/<task_id>
→ {"peaks": [...], "num_peaks": N}

GET /timestamps/<task_id>
→ {"words": [{text, start, end}], "language": "..."}
```

### Outputs

```http
GET /outputs
→ [{name, files: [...]}]

GET /outputs/<path>
→ file download
```

### Settings

```http
GET /settings
→ settings.yaml as JSON

POST /settings
Content-Type: application/json
{"pipeline": {"asr_backend": "api"}}

→ {"status": "ok"}
```

### Cancel

```http
POST /cancel/<task_id>
→ {"status": "cancelled"}
```

### Models

```http
GET /models/status
→ {"models": [{id, repo, status, size_mb}]}

GET /models/download/<model_id>
→ {"status": "downloading|already_downloaded"}
```

### Endpoint Service

```http
POST /endpoint/start
→ {"status": "started", "port": 11435, "url": "...", "key": "..."}

POST /endpoint/stop
→ {"status": "stopped"}

GET /endpoint/status
→ {"running": bool, "port": ..., "url": ..., "key": ...}

GET /endpoint/qrcode
→ image/png (QR code for server URL)
```

## Theme

暗色主題（直接沿用 spec.md 的配色方案）：
- Background: `#0f172a`
- Card: `#1e293b`
- Text: `#e2e8f0`
- Accent: `#3b82f6`
- Success: `#22c55e`

## AI Studio Prompt 範例

```prompt
Generate a React TypeScript page component called AudioFile that:
1. Has an upload area showing file name or "選擇檔案" button
2. A button row: Start Conversion, Open Output Folder, Save Subtitles
3. Simple inline settings: language dropdown, speaker diarization toggle, timeline alignment toggle
4. An optional recognition prompt textarea
5. A progress bar
6. Recognition results area with waveform placeholder, word blocks, and subtitle list
7. All API calls go through api.ts (import { api } from '../api')
Use the dark theme colors from the spec. Single page, no routing needed.
```

就是 6 個清晰明確的頁面，每個對應一個 API 互動模式，沒有多餘的抽象層。
