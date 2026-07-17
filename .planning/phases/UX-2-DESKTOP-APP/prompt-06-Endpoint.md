Create src/pages/Endpoint.tsx — endpoint service page for a subtitle processing app.

### Setup
- Import { useState, useEffect } from 'react'
- Import { api } from '../api'
- Import type { EndpointStatus } from '../types'

### State
- status: EndpointStatus | null
- showKey: boolean (false)
- error: string | null

### Layout

Title: "端點服務"

```
# Card 1: OpenAI-Compatible Service
┌────────────────────────────────────────────────────┐
│ OpenAI 相容轉錄服務                                  │
│ 讓手機或其他程式透過區網上傳音檔辨識                   │
│ ● 執行中                               [● 啟動服務] │
└────────────────────────────────────────────────────┘

# Card 2: Connection Info (two-column)
┌───────────────────────┐  ┌───────────────────────┐
│ 上傳網頁                │  │ 存取金鑰               │
│ [ QR Code placeholder ]│  │ ●●●●●●●●●  [顯示]    │
│                        │  │           [重設]      │
│ http://192.168.x.x     │  │                       │
│ :11435                 │  │                       │
│ [複製]                  │  │                       │
│ 同網段裝置可掃QR...      │  │                       │
└───────────────────────┘  └───────────────────────┘

# Card 3: External URL
┌────────────────────────────────────────────────────┐
│ ⚠️ 對外臨時網址 (Cloudflare)                        │
│ ○ 對外    網址含金鑰，用完請立即關閉                   │
└────────────────────────────────────────────────────┘
```

### Behavior
- On mount: call api.getEndpointStatus() to check if service is running
- "啟動服務" toggle → call api.startEndpoint() / api.stopEndpoint()
- When started: show status as "running" with green dot
- 顯示/重設  key: showKey toggles between masked and visible, "重設" calls api.startEndpoint() again
- "複製" button copies URL to clipboard (navigator.clipboard.writeText)
- QR Code: show a black square with a small QR icon or "QR" text (placeholder, real QR will be added later)
- Cloudflare toggle is UI only (functionality not implemented yet) — clicking it shows a note "Coming soon"

### Styling
- Dark theme with CSS variables
- Cards: background var(--bg-card), border 1px solid var(--border), border-radius var(--radius), padding 20px
- Two-column layout for the connection info cards using grid or flex
- Status dot: 10px circle, green when running, gray when stopped
- Key field: monospace font, password dots when masked
- Warning box (cloudflare): background rgba(245, 158, 11, 0.1), border 1px solid var(--warning)
- Buttons: accent for primary, bg-hover for secondary
- QR placeholder: 120x120 black square, centered, with small white "QR" text in center
- Copy button: small, inline

Return the COMPLETE file content only.
