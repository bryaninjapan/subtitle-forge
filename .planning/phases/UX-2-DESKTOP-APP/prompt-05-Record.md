Create src/pages/Record.tsx — a simplified recording page placeholder for a subtitle processing app.

This page uses Web Audio API + MediaRecorder which is complex. For now create a static UI placeholder. The real recording functionality will be added later.

### Setup
- Import { useState } from 'react'

### Layout

Title: "錄製轉換"

Control row:
```
麥克風: [預設麥克風 ▼]  [重新整理]    語言: [自動 ▼]
```

Recording card (centered card with large mic button):
```
┌──────────────────────────────────────┐
│                                      │
│           [ 🎤 ]                     │ ← large circular button
│            00:00                     │ ← timer display
│                                      │
│  錄製轉換：偵測到說話停頓時才辨識...    │ ← description text
│                                      │
└──────────────────────────────────────┘
```

Real-time subtitle area:
```
即時字幕
即時存檔: [○]          [清除]  [儲存字幕]

┌──────────────────────────────────────┐
│  開始錄音後，辨識結果會逐段出現...      │
└──────────────────────────────────────┘
```

### Styling
- Dark theme using CSS variables
- Recording card: background var(--bg-card), border-radius var(--radius), padding 40px, text-align center
- Mic button: 100px x 100px, border-radius 50%, background var(--accent), color white, font-size 48px, border none, cursor pointer
- Timer: font-size 36px, font-weight bold, font-family monospace, color var(--text-primary)
- Description: font-size 13px, color var(--text-muted), margin-top 12px
- Subtitle area: background var(--bg-card), border-radius var(--radius), padding 16px
- Buttons: padding 8px 16px, border-radius var(--radius), border none, cursor pointer
- Toggle switch: same style as Batch.tsx slider toggle
- Empty subtitle area: color var(--text-muted), text-align center, padding 40px

Return the COMPLETE file content only.
