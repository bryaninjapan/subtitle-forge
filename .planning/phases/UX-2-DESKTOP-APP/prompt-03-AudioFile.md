Create src/pages/AudioFile.tsx — the main audio transcription page for a subtitle processing app.

### Setup
- Import { useState, useEffect } from 'react'
- Import { api } from '../api'
- Import type { TaskProgress, WordTimestamp } from '../types'

### State
- file: File | null (selected file)
- taskId: string | null (from upload response)
- progress: TaskProgress | null (polled progress)
- peaks: number[] (waveform data)
- words: WordTimestamp[] (word timestamps)
- lang: string ('auto')
- diarize: boolean (false)
- timelineAlign: boolean (true)
- prompt: string (optional recognition hint)

### Layout (render exactly as shown)

File upload area (when no file is selected):
```
[選擇檔案] button — styled as dashed border box with "選擇音檔" text
```

File upload area (when file is selected):
```
夏天這一站.mp3  (3.1 MB)                    [×]
— rounded card, light background (var(--bg-card)), shows filename + size + X button
```

Button row:
```
[▶ 開始轉換]  [📂 輸出資料夾]  [💾 字幕存檔]
— Start has accent background, others have card background
— Disable Start when no file or task is running
— Disable all buttons during processing
```

Settings row:
```
語言: [自動 ▼]    說話者分離: [○]    人數: [自動 ▼]    時間軸對齊: [●]
— Select dropdowns for language and numSpeakers
— Toggle switches for diarize and timelineAlign
```

Recognition prompt (optional):
```
辨識提示（可選）
┌──────────────────────────────────────────────┐
│                                                │
│  貼入歌詞、關鍵字或背景說明...                   │
│                                                │
│                               [讀入TXT...]      │
└──────────────────────────────────────────────┘
— Textarea with placeholder
— Read TXT button opens file picker for .txt files
```

Progress bar (only shown when taskId exists):
```
████████████████████░░░░  完成  60%
— Thick bar: completed part accent color, remaining part bg-hover
— Label on left, percentage on right
— Stage changes color: queued=gray, processing=blue, done=green, error=red
```

Recognition results (only when progress?.stage === 'done'):
```
┌── 辨識結果 ──────────────────────────────────┐
│  [=====波形=====]        01:10                │
│  週末 窗外 花 黃 有 別 我 每                  │
│  [▶] [■] [🎤]  點波形/字幕可跳播              │
└──────────────────────────────────────────────┘
— Waveform area: render peaks as vertical bars
  - Container height: 80px
  - Each bar: 2px wide, height = peak * 80px, color var(--accent)
  - Played portion (left half): var(--accent), remaining: var(--bg-hover)
— Word blocks: each word in a rounded box (background var(--bg-card), margin 4px, padding 4px 8px)
— Playback controls: play button (accent), stop button, mic button
— Timestamp: current playback position
```

Subtitle list (only when progress?.stage === 'done'):
```
00:01 → 00:03   週末的早晨
00:03 → 00:05   睡到自然醒
— Each row: timestamp range (var(--text-muted)) + text (var(--text-primary))
— Alternating row backgrounds
```

### Behavior
- Select file → setFile
- Click Start → api.runPipeline(file, { translate: false, notes: false }) → get taskId
- When taskId exists: poll api.getProgress() every 2 seconds
- When progress.stage === 'done': fetch api.getWaveform(taskId) and api.getTimestamps(taskId)
- X button clears file and taskId
- Open Output Folder: calls a function (can just alert or open in finder)
- Save Subtitles: download the .srt file from server
- Handle all states: empty (no file), loading (uploading/processing), error, done
- Error state: show red error card with message

### Styling
- Use CSS variables: var(--bg-card), var(--bg-primary), var(--accent), var(--text-primary), var(--text-secondary), var(--text-muted), var(--border), var(--radius), var(--bg-hover), var(--success), var(--error)
- Dark theme throughout
- Cards have background var(--bg-card), border-radius var(--radius), padding 16px
- Inputs/selects: dark background (var(--bg-hover)), light text
- Buttons: padding 8px 16px, border-radius var(--radius), border none, cursor pointer
- Toggle switches: slider-style, accent color when on

Return the COMPLETE file content only.
