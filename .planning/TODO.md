# TODO — Subtitle Forge

> Updated: 2026-07-17
> Status: Backend complete, pending React frontend (Part B)

## ✅ Done (backend)

- [x] **G1: ASR model → settings.yaml** ✅
- [x] **G2 (backend): Model status + download API** ✅ `GET /models/status`, `POST /models/download/:name`
- [x] **Pipeline toggle** ✅ translate/notes/chapters 開關
- [x] **VAD threshold → settings.yaml** ✅ `vad_threshold: 0.5`
- [x] **OpenCC 簡繁轉換** ✅ `cc_conversion: off/standard/taiwan`
- [x] **Prompt → hot words** ✅ `POST /pipeline prompt` 參數
- [x] **Waveform / timestamps / audio endpoints** ✅ Phase 1
- [x] **Model management backend** ✅ Phase 3
- [x] **Endpoint service (QR code, auth, port 11435)** ✅ Phase 4
- [x] **Tauri sidecar spawn server.py** ✅ A3
- [x] **System tray** ✅ A4
- [x] **CORS + API contract** ✅ A6

## 🟡 REACT FRONTEND (Part B)

### P1: 音檔轉字幕 (`AudioFile.tsx`)
- [ ] 上傳區（顯示檔名 + 移除）
- [ ] 按鈕列（開始轉換、輸出資料夾、字幕存檔）
- [ ] 簡單設定（語言、說話者分離、時間軸對齊）
- [ ] 辨識提示 textarea（可選）
- [ ] 進度條
- [ ] 辨識結果（波形、字詞區塊、播放控制）
- [ ] 字幕列表（時間戳 + 文字）

### P2: 批次辨識 (`Batch.tsx`)
- [ ] 加入檔案、全部開始
- [ ] 每個檔案進度條 + 狀態標籤
- [ ] 說話者分離 toggle

### P3: 錄製轉換 (`Record.tsx`)
- [ ] 麥克風選取
- [ ] 錄音按鈕 + 計時器
- [ ] 即時字幕顯示
- [ ] 即時存檔 toggle

### P4: 端點服務 (`Endpoint.tsx`)
- [ ] 啟動/停止 toggle
- [ ] QR code 顯示
- [ ] URL + 金鑰顯示
- [ ] Cloudflare tunnel toggle

### P5: 模型與裝置 (`ModelManage.tsx`)
- [ ] 模型列表 + 下載狀態
- [ ] 下載觸發
- [ ] 推理核心選擇

### P6: 設定 (`Settings.tsx`)
- [ ] 介面縮放滑桿
- [ ] 輸出格式選擇
- [ ] VAD 靈敏度滑桿
- [ ] 簡繁轉換選擇
- [ ] 外觀主題
- [ ] FFmpeg 路徑
- [ ] HuggingFace 鏡像

### 通用
- [ ] **G3: 前端測試** (Vitest + MSW)
- [ ] **G4: 首次啟動引導** (歡迎畫面 + model 下載提示)
- [ ] **G5: Error/Loading/Empty 狀態** (每個 component)
- [ ] **G6: 版本更新** (Tauri auto-updater)
- [ ] **G8: Windows ASR Backend** (faster-whisper/OpenVINO)
