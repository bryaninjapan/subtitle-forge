# Subtitle Forge — Desktop App Frontend Specification

## Overview

React + TypeScript frontend for a desktop subtitle processing application.
Runs inside a Tauri webview. Communicates with a Python Flask backend (`server.py`) via HTTP on `localhost:5000`.

## UI Layout

```
┌──────────────────────────────────────────────────────────┐
│  🎬 Subtitle Forge                              v1.0   │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐  ┌──────────────────────────────────┐  │
│  │  Drop Zone    │  │  Active Tasks                    │  │
│  │  (upload)     │  │  ┌────────────────────────────┐  │  │
│  │               │  │  │ video1.mp4 ████░░ 60% ASR │  │  │
│  │               │  │  │ video2.mkv ██████ 100% ✅ │  │  │
│  │               │  │  └────────────────────────────┘  │  │
│  └──────────────┘  │                                    │  │
│                     │  ┌────────────────────────────┐  │  │
│  ┌──────────────┐  │  │ History                     │  │  │
│  │  Settings     │  │  │ 14:32 video1  $0.00  ✅   │  │  │
│  │  Simple/Adv.  │  │  │ 14:28 video2  $0.00  ✅   │  │  │
│  └──────────────┘  │  └────────────────────────────┘  │  │
│                    └──────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

### Color Scheme (Dark Theme)

- Background: `#0f172a` (slate-900)
- Card background: `#1e293b` (slate-800)
- Text: `#e2e8f0` (slate-200)
- Muted text: `#64748b` (slate-500)
- Primary accent: `#3b82f6` (blue-500)
- Success: `#22c55e` (green-500)
- Error: `#ef4444` (red-500)
- Border: `#334155` (slate-700)

---

## API Contract

All endpoints are on `http://localhost:5000`.

### Upload File

```http
POST /upload
Content-Type: multipart/form-data

file: <binary audio/video file>
```

Response (JSON):
```json
{
  "task_id": "a1b2c3d4",
  "file": "video.mp4",
  "status": "queued"
}
```

### Get Progress

```http
GET /progress
```

Response (JSON):
```json
{
  "a1b2c3d4": {
    "file": "video.mp4",
    "pct": 60,
    "stage": "processing",
    "message": "Transcribing audio..."
  },
  "e5f6g7h8": {
    "file": "video2.mkv",
    "pct": 100,
    "stage": "done",
    "message": "Complete!"
  }
}
```

**`stage` values**: `queued` | `extracting` | `initializing` | `processing` | `done` | `error`

### Get History

```http
GET /history
```

Response (JSON):
```json
[
  {
    "timestamp": "2026-07-17 14:32:01",
    "category": "ASR",
    "detail": "video.mp4 - transcription complete",
    "cost": 0.0
  }
]
```

### Get Outputs

```http
GET /outputs
```

Response (JSON):
```json
[
  {
    "name": "video1",
    "files": ["video1.srt", "video1.zh.srt", "video1.bilingual.srt", "video1_StudyNotes.md"]
  }
]
```

### Get Settings

```http
GET /settings
```

Response (JSON) — contents of `settings.yaml`:
```json
{
  "domain": "CFA",
  "pipeline": {
    "asr_backend": "local",
    "asr_model": "Qwen/Qwen3-ASR-0.6B",
    "asr_diarize": false,
    "asr_hotwords": true,
    "asr_concurrent": 2,
    "style": "academic"
  }
}
```

### Update Settings

```http
POST /settings
Content-Type: application/json

{"pipeline": {"asr_backend": "api", "asr_hotwords": true}}
```

Response:
```json
{"status": "ok"}
```

### Cancel Task

```http
POST /cancel/a1b2c3d4
```

Response:
```json
{"status": "cancelled"}
```

---

## TypeScript Types

```typescript
// api.ts types

interface TaskProgress {
  file: string;
  pct: number;
  stage: 'queued' | 'extracting' | 'initializing' | 'processing' | 'done' | 'error';
  message: string;
}

interface HistoryEntry {
  timestamp: string;
  category: string;
  detail: string;
  cost: number;
}

interface OutputFolder {
  name: string;
  files: string[];
}

interface AppSettings {
  domain?: string;
  pipeline?: {
    asr_backend?: 'local' | 'api';
    asr_model?: string;
    asr_diarize?: boolean;
    asr_hotwords?: boolean;
    asr_concurrent?: number;
    [key: string]: unknown;
  };
  [key: string]: unknown;
}

interface UploadResponse {
  task_id: string;
  file: string;
  status: string;
}
```

---

## Component Specifications (MVP — 5 Components)

### 1. `api.ts`

API wrapper module. All components import from here, never call fetch directly.

```typescript
// api.ts
const BASE = 'http://localhost:5000';

export const api = {
  upload: async (file: File): Promise<UploadResponse> => {
    const form = new FormData();
    form.append('file', file);
    const res = await fetch(`${BASE}/upload`, { method: 'POST', body: form });
    return res.json();
  },

  getProgress: async (): Promise<Record<string, TaskProgress>> => {
    const res = await fetch(`${BASE}/progress`);
    return res.json();
  },

  getHistory: async (): Promise<HistoryEntry[]> => {
    const res = await fetch(`${BASE}/history`);
    return res.json();
  },

  getOutputs: async (): Promise<OutputFolder[]> => {
    const res = await fetch(`${BASE}/outputs`);
    return res.json();
  },

  getSettings: async (): Promise<AppSettings> => {
    const res = await fetch(`${BASE}/settings`);
    return res.json();
  },

  updateSettings: async (data: Partial<AppSettings>): Promise<{status: string}> => {
    const res = await fetch(`${BASE}/settings`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(data),
    });
    return res.json();
  },

  cancelTask: async (taskId: string): Promise<{status: string}> => {
    const res = await fetch(`${BASE}/cancel/${taskId}`, { method: 'POST' });
    return res.json();
  },
};
```

### 2. `DropZone.tsx`

**Purpose**: Drag-and-drop area for uploading media files.

**Props**: none (uses `api.upload` internally)

**States**:
- Empty: Shows dashed border + "Drop media files here or click to browse"
- Dragging: Border turns blue, background highlights
- Uploading: Shows spinner + filename
- Error: Shows error message (invalid file type, upload failed)
- Success: Clears drop zone (file is being processed)

**Behavior**:
- Accepts: `.mp4`, `.mkv`, `.mov`, `.avi`, `.webm`, `.mp3`, `.wav`, `.m4a`, `.aac`
- Multiple files: create separate tasks for each
- Click to browse: hidden file input
- After upload, the task appears in ProgressDisplay automatically

### 3. `SettingsPanel.tsx`

**Purpose**: Application configuration with Simple/Advanced toggle.

**Props**: none (uses `api.getSettings` / `api.updateSettings`)

**Simple Mode** (default, collapsible):
```
🌐 Language: [auto ▼]
⚙️  ASR:     [● Local  ○ API ]
```

**Advanced Mode** (click "Show Advanced" to expand):
```
ASR Settings:
├── Model: [Qwen3-ASR-0.6B ▼]
├── Hot words: [✅ Enable]
├── Diarization: [✅ Enable]
├── Concurrency: [2]

Pipeline Settings:
├── Style: [academic ▼]
├── Chapters: [✅]
├── Output: [SRT, VTT, Bilingual]
```

**Behavior**:
- Load current settings from API on mount
- Save on change (debounced, 1s after last change)
- "Show Advanced" / "Hide Advanced" toggle
- Settings persist in `settings.yaml` via API

### 4. `ProgressDisplay.tsx`

**Purpose**: Real-time progress for all active/recent tasks.

**Props**: none (polls `api.getProgress` every 2 seconds)

**Task Row Layout**:
```
┌──────────────────────────────────────────────────┐
│  video1.mp4   ████████████░░░░░░  60%  ASR      │
│  video2.mkv   ██████████████████  100% ✅ Done  │
│  video3.mp4   ██████░░░░░░░░░░░░  30%  Extract  │
└──────────────────────────────────────────────────┘
```

**States**:
- Active tasks (pct < 100): Animated progress bar, show stage
- Completed (pct = 100, stage = "done"): Green bar, checkmark
- Error (stage = "error"): Red bar, error message
- Empty: "No active tasks" message

**Colors by stage**:
- queued: gray (#475569)
- extracting/initializing/processing: blue (#3b82f6)
- done: green (#22c55e)
- error: red (#ef4444)

**Auto-cleanup**: Remove tasks that completed >5 minutes ago

### 5. `TaskHistory.tsx`

**Purpose**: Table of completed tasks with costs.

**Props**: none (polls `api.getHistory` every 10 seconds)

**Table columns**:
| Time | Category | Detail | Cost |
|------|----------|--------|------|

**Category badges**:
- ASR: blue background
- Translate: green
- Notes: purple
- Chapter: orange
- Error: red

**Behavior**:
- Sort by time descending
- Show last 30 entries
- Cost column shows `$0.0000` format
- Empty: "No history yet"

---

## Simple/Advanced Settings Design

The settings panel has two modes controlled by a single toggle:

```
[● Simple] [○ Advanced]
```

**Simple** shows only:
- Language dropdown
- ASR source toggle (Local / API)

**Advanced** adds:
- ASR model selector
- Hot words toggle
- Diarization toggle  
- Concurrency slider
- Output format checkboxes
- Style selector
- Max cost input

The selected mode persists in localStorage.

---

## File Structure (desktop/src/)

```
desktop/src/
├── api.ts              # API wrapper
├── types.ts            # TypeScript interfaces
├── App.tsx             # Main layout component
├── main.tsx            # React entry point
│
├── components/
│   ├── DropZone.tsx        # File upload
│   ├── SettingsPanel.tsx   # Simple/Advanced settings
│   ├── ProgressDisplay.tsx # Task progress
│   └── TaskHistory.tsx     # Completed tasks
│
└── styles/
    └── global.css      # Dark theme + layout styles
```

## Development Notes

- Use Vite + React + TypeScript
- No routing library needed (single-page app, no navigation)
- No state management library needed (local state + polling is sufficient)
- Use CSS modules or plain CSS (keep dependencies minimal)
- Dark theme only (match existing web dashboard)
- All API calls go through `api.ts` — never use `fetch()` directly in components
- Handle loading/error states in every component
- Use `hx-trigger="every 2s"` pattern for polling (or `setInterval` + `useEffect`)
