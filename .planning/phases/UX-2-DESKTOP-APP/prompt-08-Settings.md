Create src/pages/Settings.tsx — settings page for a subtitle processing app.

### Setup
- Import { useState, useEffect } from 'react'
- Import { api } from '../api'
- Import type { AppSettings } from '../types'

### State
- settings: AppSettings | null
- loading: boolean
- error: string | null
- saving: boolean

### Layout

Title: "設定"

Settings form (single card with horizontal dividers):

```
介面縮放
[══════●══════]  100%

輸出格式
[ SRT 字幕 ● ]  [ 純文字 ]

VAD 靈敏度
[════●══════]  0.35

簡繁轉換
[ 關閉 ]  [ 台灣用語 ● ]  [ 標準 ]

外觀主題
[ 淺色 ● ]  [ 深色 ]  [ 跟隨系統 ]

FFmpeg 路徑
[ (留空=自動偵測)                                    ]
```

Footer:
```
聲音辨識小工具 v0.1  [檢查更新]
```

### Behavior
- On mount: fetch api.getSettings()
- Each setting is a form control bound to state
- Sliders (range input): debounced save (1s after last change)
- Button groups: styled as buttons, selected one has accent bg
- Text input: saves on blur
- "檢查更新" button: just shows "已是最新版本" alert
- Handle loading/error states
- Settings that currently exist in the API:
  - pipeline.asr_backend: 'local' | 'api'
  - pipeline.vad_threshold: number (0-1, step 0.05)
  - pipeline.cc_conversion: 'off' | 'standard' | 'taiwan'
  - pipeline.asr_diarize: boolean
  - pipeline.asr_hotwords: boolean
- UI-only settings (no API endpoint yet):
  - interface scaling (just display, no save)
  - theme (just display, no save)
  - output format (just display, no save)

### Styling
- Dark theme, CSS variables
- Card: bg var(--bg-card), border var(--border), radius var(--radius), padding 24px
- Each setting row: padding 16px 0, border-bottom 1px solid var(--border)
- Last row: no border
- Label: font-size 14px, font-weight 500, color var(--text-primary)
- Description: font-size 12px, color var(--text-muted), margin-top 4px
- Range input: custom styled (accent track, white thumb)
- Button group: inline-flex, no gap, first/last border-radius
- Selected button: bg var(--accent), color white
- Unselected button: bg var(--bg-hover), color var(--text-secondary)
- Input text: bg var(--bg-primary), border var(--border), color var(--text-primary)
- Footer: text-align center, color var(--text-muted), font-size 12px
- Loading state: centered spinner text
- Saving indicator: small "儲存中..." text next to changed setting

Return the COMPLETE file content only.
