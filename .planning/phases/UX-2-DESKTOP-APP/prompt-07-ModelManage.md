Create src/pages/ModelManage.tsx — model management page for a subtitle processing app.

### Setup
- Import { useState, useEffect } from 'react'
- Import { api } from '../api'
- Import type { ModelInfo } from '../types'

### State
- models: ModelInfo[]
- loading: boolean
- error: string | null
- downloadProgress: Record<string, TaskProgress> (progress of ongoing downloads)

### Layout

Title: "模型與裝置"

System check badge:
```
核心就緒 · 1 項將於啟用時自動下載  [重新檢查]
```

Model cards (one per model):

Qwen3-ASR-0.6B
```
┌──────────────────────────────────────────────┐
│  Qwen3-ASR-0.6B                              │
│  ● 已下載  (1,200 MB)                        │
│  components: ASR 模型(0.6B), VAD, FA, 分離    │
└──────────────────────────────────────────────┘
```

Qwen3-ForcedAligner-0.6B (not downloaded):
```
┌──────────────────────────────────────────────┐
│  Qwen3-ForcedAligner-0.6B                    │
│  ○ 未下載  (1.8 GB)            [ 下載 ]      │
│  components: 時間軸對齊 FA, 說話者分離         │
└──────────────────────────────────────────────┘
```

Shared components card:
```
共用元件
FFmpeg (影片抽音軌用)    ● 已偵測
說話者分離模型            ● 已下載
```

Inference core radio buttons:
```
推理核心
(●) Qwen  — 5 種模型可選
(○) Whisper (Breeze) — 3 種模型可選
```

Model dropdown:
```
模型: [Qwen3-ASR-0.6B ▼]  GPU: [Auto ▼]

[前往語音轉文字]
```

### Behavior
- On mount: fetch api.getModels()
- Each model card shows status icon:
  - ● downloaded (green dot, var(--success))
  - ○ not_downloaded (gray dot, var(--text-muted)) + [下載] button
  - ◐ downloading (yellow dot) + progress text
- Click "下載" → api.downloadModel(id)
- Download progress: poll api.getProgress() for task_id = "download_{id}"
- Click "重新檢查" → refetch models
- "前往語音轉文字" button navigates to audio page (just a link/hint)
- Handle loading/error states
- Empty state: "暫無模型資訊" if models list is empty

### Styling
- Dark theme, CSS variables
- Card: bg var(--bg-card), border var(--border), radius var(--radius), padding 16px
- Status dot: 8px circle
- Green: var(--success), Gray: var(--text-muted), Yellow: var(--warning)
- Download button: accent bg when enabled, muted when downloading
- Grid layout for model cards (2 columns on wider screens)
- Radio buttons: custom styled (accent ring for selected)
- Shared components section: slightly different bg (bg-primary)
- Footer: center-aligned, margin-top auto

Return the COMPLETE file content only.
